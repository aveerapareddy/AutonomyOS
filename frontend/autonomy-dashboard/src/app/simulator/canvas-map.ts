import type { RobotPose, SimulatorScene, Vec2, WorldBounds } from './simulator-scene.model';

export interface ScreenMapping {
  scale: number;
  ox: number;
  oy: number;
}

export interface MapCanvasLayout {
  cssWidth: number;
  cssHeight: number;
  pixelWidth: number;
  pixelHeight: number;
  map: ScreenMapping;
}

function worldToScreen(m: ScreenMapping, x: number, y: number): Vec2 {
  return { x: m.ox + x * m.scale, y: m.oy - y * m.scale };
}

function niceStep(span: number, divisions: number): number {
  const raw = span / divisions;
  if (raw <= 0) {
    return 1;
  }
  const exp = Math.floor(Math.log10(raw));
  const base = Math.pow(10, exp);
  const fr = raw / base;
  const nf = fr <= 1 ? 1 : fr <= 2 ? 2 : fr <= 5 ? 5 : 10;
  return nf * base;
}

export function layoutForBounds(
  cssWidth: number,
  cssHeight: number,
  dpr: number,
  bounds: WorldBounds,
  padFraction: number,
): MapCanvasLayout {
  const pixelWidth = Math.max(1, Math.floor(cssWidth * dpr));
  const pixelHeight = Math.max(1, Math.floor(cssHeight * dpr));
  const bw = bounds.maxX - bounds.minX;
  const bh = bounds.maxY - bounds.minY;
  const padX = bw * padFraction;
  const padY = bh * padFraction;
  const worldW = bw + 2 * padX;
  const worldH = bh + 2 * padY;
  const scale = Math.min(pixelWidth / worldW, pixelHeight / worldH);
  const ox = (pixelWidth - scale * worldW) / 2 - scale * (bounds.minX - padX);
  const oy = (pixelHeight - scale * worldH) / 2 + scale * (bounds.maxY + padY);
  return {
    cssWidth,
    cssHeight,
    pixelWidth,
    pixelHeight,
    map: { scale, ox, oy },
  };
}

function drawGrid(
  ctx: CanvasRenderingContext2D,
  bounds: WorldBounds,
  map: ScreenMapping,
  idleOpacity: number,
): void {
  const step = niceStep(Math.max(bounds.maxX - bounds.minX, bounds.maxY - bounds.minY), 10);
  ctx.lineWidth = 1;
  ctx.strokeStyle = `rgba(200,205,212,${0.035 + idleOpacity * 0.02})`;
  for (let x = Math.ceil(bounds.minX / step) * step; x <= bounds.maxX + 1e-6; x += step) {
    const a = worldToScreen(map, x, bounds.minY);
    const b = worldToScreen(map, x, bounds.maxY);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
  for (let y = Math.ceil(bounds.minY / step) * step; y <= bounds.maxY + 1e-6; y += step) {
    const a = worldToScreen(map, bounds.minX, y);
    const b = worldToScreen(map, bounds.maxX, y);
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.stroke();
  }
}

function drawBounds(ctx: CanvasRenderingContext2D, bounds: WorldBounds, map: ScreenMapping): void {
  const c1 = worldToScreen(map, bounds.minX, bounds.minY);
  const c2 = worldToScreen(map, bounds.maxX, bounds.maxY);
  const x = Math.min(c1.x, c2.x);
  const y = Math.min(c1.y, c2.y);
  const w = Math.abs(c2.x - c1.x);
  const h = Math.abs(c2.y - c1.y);
  ctx.strokeStyle = '#3D4450';
  ctx.lineWidth = 1;
  ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
}

function drawPolyline(
  ctx: CanvasRenderingContext2D,
  map: ScreenMapping,
  path: Vec2[],
  style: { stroke: string; dash?: number[]; width: number },
): void {
  if (path.length < 2) {
    return;
  }
  ctx.beginPath();
  const p0 = worldToScreen(map, path[0].x, path[0].y);
  ctx.moveTo(p0.x, p0.y);
  for (let i = 1; i < path.length; i++) {
    const p = worldToScreen(map, path[i].x, path[i].y);
    ctx.lineTo(p.x, p.y);
  }
  ctx.strokeStyle = style.stroke;
  ctx.lineWidth = style.width;
  ctx.setLineDash(style.dash ?? []);
  ctx.lineJoin = 'round';
  ctx.stroke();
  ctx.setLineDash([]);
}

function drawObstacles(
  ctx: CanvasRenderingContext2D,
  scene: SimulatorScene,
  map: ScreenMapping,
  idleMul: number,
): void {
  const half = scene.obstacleHalfExtent * map.scale;
  for (const o of scene.obstacles) {
    const c = worldToScreen(map, o.x, o.y);
    ctx.fillStyle = idleMul > 0 ? 'rgba(35,39,46,0.55)' : 'rgba(35,39,46,0.92)';
    ctx.strokeStyle = idleMul > 0 ? 'rgba(61,68,80,0.5)' : '#333942';
    ctx.lineWidth = 1;
    ctx.fillRect(c.x - half, c.y - half, half * 2, half * 2);
    ctx.strokeRect(c.x - half + 0.5, c.y - half + 0.5, half * 2 - 1, half * 2 - 1);
  }
}

function drawTarget(ctx: CanvasRenderingContext2D, map: ScreenMapping, p: Vec2, dim: boolean): void {
  const c = worldToScreen(map, p.x, p.y);
  const r = Math.max(4, map.scale * 0.22);
  ctx.strokeStyle = dim ? 'rgba(173,181,189,0.45)' : '#ADB5BD';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(c.x - r, c.y);
  ctx.lineTo(c.x + r, c.y);
  ctx.moveTo(c.x, c.y - r);
  ctx.lineTo(c.x, c.y + r);
  ctx.stroke();
  ctx.strokeRect(c.x - r * 0.65, c.y - r * 0.65, r * 1.3, r * 1.3);
}

function drawRobot(ctx: CanvasRenderingContext2D, map: ScreenMapping, pose: RobotPose): void {
  const c = worldToScreen(map, pose.x, pose.y);
  const body = Math.max(5, map.scale * 0.32);
  ctx.save();
  ctx.translate(c.x, c.y);
  ctx.rotate(-pose.theta);
  ctx.fillStyle = '#B8BEC8';
  ctx.strokeStyle = '#1A1D22';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(body * 0.9, 0);
  ctx.lineTo(-body * 0.55, body * 0.42);
  ctx.lineTo(-body * 0.35, 0);
  ctx.lineTo(-body * 0.55, -body * 0.42);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

export function paintSimulatorMap(
  ctx: CanvasRenderingContext2D,
  layout: MapCanvasLayout,
  scene: SimulatorScene,
): void {
  const { pixelWidth, pixelHeight, map } = layout;
  const idle = scene.mode === 'idle' ? 1 : 0;
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.clearRect(0, 0, pixelWidth, pixelHeight);
  ctx.fillStyle = '#121418';
  ctx.fillRect(0, 0, pixelWidth, pixelHeight);

  drawGrid(ctx, scene.bounds, map, idle);
  drawBounds(ctx, scene.bounds, map);

  drawObstacles(ctx, scene, map, idle);

  drawPolyline(ctx, map, scene.plannedPath, {
    stroke: idle ? 'rgba(156,163,175,0.35)' : '#9CA3AF',
    width: idle ? 1 : 1.5,
  });
  drawPolyline(ctx, map, scene.executedPath, {
    stroke: idle ? 'rgba(107,114,128,0.2)' : '#6B7280',
    dash: [6, 4],
    width: 1.25,
  });

  if (scene.target) {
    drawTarget(ctx, map, scene.target, idle > 0);
  }
  if (scene.robot) {
    drawRobot(ctx, map, scene.robot);
  }
}
