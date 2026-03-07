"""Shared constants for mission and event lifecycle."""

MISSION_STATUS_RECEIVED = "received"
MISSION_STATUS_PLANNED = "planned"
MISSION_STATUS_EXECUTING = "executing"
MISSION_STATUS_COMPLETED = "completed"
MISSION_STATUS_FAILED = "failed"

EVENT_TYPE_MISSION_START = "mission_start"
EVENT_TYPE_MISSION_END = "mission_end"
EVENT_TYPE_NAVIGATION = "navigation"
EVENT_TYPE_PERCEPTION = "perception"
EVENT_TYPE_TELEMETRY = "telemetry"

BENCHMARK_STATUS_PENDING = "pending"
BENCHMARK_STATUS_RUNNING = "running"
BENCHMARK_STATUS_COMPLETED = "completed"
BENCHMARK_STATUS_FAILED = "failed"

# Perception confidence defaults (Phase-1 rule-based uses these; evolve for YOLO).
TARGET_CONFIDENCE_DEFAULT = 1.0
OBSTACLE_CONFIDENCE_DEFAULT = 1.0
