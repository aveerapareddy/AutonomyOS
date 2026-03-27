export interface Vec2 {
  x: number;
  y: number;
}

export interface WorldBounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

export interface RobotPose {
  x: number;
  y: number;
  theta: number;
}

export interface SimulatorScene {
  mode: 'idle' | 'live';
  bounds: WorldBounds;
  obstacles: Vec2[];
  obstacleHalfExtent: number;
  target: Vec2 | null;
  robot: RobotPose | null;
  plannedPath: Vec2[];
  executedPath: Vec2[];
}
