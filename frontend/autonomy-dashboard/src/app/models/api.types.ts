export interface MissionResponse {
  mission_id: string;
  status: string;
  created_at: string;
}

export interface MissionPlan {
  goal_type: string;
  target_label: string | null;
  constraints: string[];
  plan_steps: string[];
  confidence: number | null;
  planner_mode: string;
}

export interface ExecutionStep {
  waypoint_index: number;
  target_x: number;
  target_y: number;
  reached: boolean;
}

export interface SceneObstacle {
  x: number;
  y: number;
}

export interface MissionExecutionSummary {
  mission_id: string;
  status: string;
  plan_steps: string[];
  planner_mode?: string | null;
  goal_type?: string | null;
  target_label?: string | null;
  constraints?: string[];
  detected_target?: Record<string, unknown> | null;
  world_bounds?: [number, number, number, number] | null;
  obstacles?: SceneObstacle[];
  path_found: boolean;
  waypoint_count: number;
  path_length_raw?: number | null;
  path_length_simplified?: number | null;
  grid_inflation_cells?: number | null;
  telemetry_count: number;
  message?: string | null;
  execution_steps: ExecutionStep[];
  final_robot_position?: Record<string, number> | null;
  execution_status?: string | null;
}

export interface TelemetryEvent {
  event_id: string;
  mission_id: string;
  sequence: number;
  timestamp: string;
  event_type: string;
  source_component: string;
  payload: Record<string, unknown>;
}

export interface TelemetryQueryResponse {
  mission_id: string;
  events: TelemetryEvent[];
  count: number;
}
