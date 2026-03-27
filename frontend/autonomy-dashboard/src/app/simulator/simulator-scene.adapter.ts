import type { MissionExecutionSummary, TelemetryEvent } from '../models/api.types';
import { REFERENCE_OBSTACLES, REFERENCE_TARGET, REFERENCE_WORLD_BOUNDS } from './default-reference-layout';
import type { RobotPose, SimulatorScene, Vec2, WorldBounds } from './simulator-scene.model';

const OBSTACLE_HALF = 0.5;
const EPS = 1e-4;

function num(v: unknown): number | null {
  if (typeof v === 'number' && Number.isFinite(v)) {
    return v;
  }
  return null;
}

function vecFromTargetRecord(t: Record<string, unknown> | null | undefined): Vec2 | null {
  if (!t) {
    return null;
  }
  const x = num(t['x']);
  const y = num(t['y']);
  if (x === null || y === null) {
    return null;
  }
  return { x, y };
}

function vecFromRobotRecord(r: Record<string, unknown> | null | undefined): RobotPose | null {
  if (!r) {
    return null;
  }
  const x = num(r['x']);
  const y = num(r['y']);
  if (x === null || y === null) {
    return null;
  }
  const th = num(r['theta']);
  return { x, y, theta: th ?? 0 };
}

function dedupeConsecutive(path: Vec2[]): Vec2[] {
  const out: Vec2[] = [];
  for (const p of path) {
    const last = out[out.length - 1];
    if (!last || Math.hypot(p.x - last.x, p.y - last.y) > EPS) {
      out.push(p);
    }
  }
  return out;
}

function collectPoints(scene: Omit<SimulatorScene, 'mode'>): Vec2[] {
  const pts: Vec2[] = [
    { x: scene.bounds.minX, y: scene.bounds.minY },
    { x: scene.bounds.maxX, y: scene.bounds.maxY },
  ];
  for (const o of scene.obstacles) {
    pts.push(o);
  }
  if (scene.target) {
    pts.push(scene.target);
  }
  if (scene.robot) {
    pts.push({ x: scene.robot.x, y: scene.robot.y });
  }
  for (const p of scene.plannedPath) {
    pts.push(p);
  }
  for (const p of scene.executedPath) {
    pts.push(p);
  }
  return pts;
}

export function expandBoundsToInclude(bounds: WorldBounds, points: Vec2[], margin: number): WorldBounds {
  let minX = bounds.minX;
  let maxX = bounds.maxX;
  let minY = bounds.minY;
  let maxY = bounds.maxY;
  for (const p of points) {
    minX = Math.min(minX, p.x - margin);
    maxX = Math.max(maxX, p.x + margin);
    minY = Math.min(minY, p.y - margin);
    maxY = Math.max(maxY, p.y + margin);
  }
  const pad = Math.max(maxX - minX, maxY - minY) * 0.04 + 0.2;
  return {
    minX: minX - pad,
    maxX: maxX + pad,
    minY: minY - pad,
    maxY: maxY + pad,
  };
}

function executionStartFromTelemetry(events: TelemetryEvent[]): Vec2 | null {
  const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
  for (const e of ordered) {
    if (e.event_type !== 'execution_started') {
      continue;
    }
    const x = num(e.payload['robot_x']);
    const y = num(e.payload['robot_y']);
    if (x !== null && y !== null) {
      return { x, y };
    }
  }
  return null;
}

function executedPathFromTelemetry(events: TelemetryEvent[]): Vec2[] {
  const ordered = [...events].sort((a, b) => a.sequence - b.sequence);
  const raw: Vec2[] = [];
  for (const e of ordered) {
    if (e.event_type === 'execution_started') {
      const x = num(e.payload['robot_x']);
      const y = num(e.payload['robot_y']);
      if (x !== null && y !== null) {
        raw.push({ x, y });
      }
    } else if (e.event_type === 'waypoint_reached') {
      const x = num(e.payload['robot_x']);
      const y = num(e.payload['robot_y']);
      if (x !== null && y !== null) {
        raw.push({ x, y });
      }
    }
  }
  return dedupeConsecutive(raw);
}

function plannedFromExecution(summary: MissionExecutionSummary, start: Vec2 | null): Vec2[] {
  const steps = [...summary.execution_steps].sort((a, b) => a.waypoint_index - b.waypoint_index);
  const pts: Vec2[] = [];
  if (start) {
    pts.push(start);
  }
  for (const s of steps) {
    pts.push({ x: s.target_x, y: s.target_y });
  }
  return dedupeConsecutive(pts);
}

function boundsFromApi(summary: MissionExecutionSummary): WorldBounds | null {
  const wb = summary.world_bounds;
  if (!wb || wb.length !== 4) {
    return null;
  }
  return { minX: wb[0], maxX: wb[1], minY: wb[2], maxY: wb[3] };
}

export function buildIdleSimulatorScene(): SimulatorScene {
  return {
    mode: 'idle',
    bounds: { ...REFERENCE_WORLD_BOUNDS },
    obstacles: REFERENCE_OBSTACLES.map((o) => ({ ...o })),
    obstacleHalfExtent: OBSTACLE_HALF,
    target: { ...REFERENCE_TARGET },
    robot: null,
    plannedPath: [],
    executedPath: [],
  };
}

export function buildSimulatorScene(
  execution: MissionExecutionSummary | null,
  telemetry: TelemetryEvent[],
): SimulatorScene {
  if (!execution) {
    return buildIdleSimulatorScene();
  }

  const obstacles =
    execution.obstacles?.map((o) => ({ x: o.x, y: o.y })) ?? [];
  const apiBounds = boundsFromApi(execution);
  const target = vecFromTargetRecord(execution.detected_target ?? undefined);
  const robot = vecFromRobotRecord(execution.final_robot_position ?? undefined);
  const execStart = executionStartFromTelemetry(telemetry);
  const plannedPath = plannedFromExecution(execution, execStart);
  let executedPath = executedPathFromTelemetry(telemetry);

  if (
    executedPath.length === 0 &&
    robot &&
    (execution.execution_steps?.length ?? 0) > 0 &&
    execStart
  ) {
    executedPath = dedupeConsecutive([execStart, robot]);
  }

  let bounds: WorldBounds =
    apiBounds ??
    (target && robot
      ? expandBoundsToInclude(REFERENCE_WORLD_BOUNDS, [target, robot], OBSTACLE_HALF)
      : { ...REFERENCE_WORLD_BOUNDS });

  const baseScene: Omit<SimulatorScene, 'mode'> = {
    bounds,
    obstacles,
    obstacleHalfExtent: OBSTACLE_HALF,
    target,
    robot,
    plannedPath,
    executedPath,
  };

  bounds = expandBoundsToInclude(bounds, collectPoints(baseScene), OBSTACLE_HALF);

  return {
    mode: 'live',
    ...baseScene,
    bounds,
  };
}
