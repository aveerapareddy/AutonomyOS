import type { Vec2, WorldBounds } from './simulator-scene.model';

export const REFERENCE_WORLD_BOUNDS: WorldBounds = {
  minX: -10,
  maxX: 10,
  minY: -10,
  maxY: 10,
};

export const REFERENCE_OBSTACLES: Vec2[] = [
  { x: -3, y: 0 },
  { x: 3, y: 0 },
  { x: 1, y: 1 },
];

export const REFERENCE_TARGET: Vec2 = { x: 5, y: 3 };
