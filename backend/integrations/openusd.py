"""Scenario-to-OpenUSD geometry interchange, not an Isaac Sim runtime adapter."""
import math
from pathlib import Path
from backend.scenarios.scenario_config import ScenarioConfig


def export_scenario(scenario: ScenarioConfig, path: Path):
    from pxr import Gf, Sdf, Usd, UsdGeom
    stage = Usd.Stage.CreateNew(str(path.resolve()))
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)
    root = UsdGeom.Xform.Define(stage, "/World")
    stage.SetDefaultPrim(root.GetPrim())
    root.GetPrim().CreateAttribute("autonomyos:scenarioId", Sdf.ValueTypeNames.String).Set(scenario.scenario_id)
    root.GetPrim().CreateAttribute("autonomyos:bounds", Sdf.ValueTypeNames.Double4).Set(scenario.world_bounds)

    def box(name, position, dimensions, color, kind):
        cube = UsdGeom.Cube.Define(stage, "/World/" + name)
        cube.CreateSizeAttr(1.0)
        cube.AddTranslateOp().Set(Gf.Vec3d(*position))
        cube.AddScaleOp().Set(Gf.Vec3f(*dimensions))
        cube.CreateDisplayColorAttr([Gf.Vec3f(*color)])
        cube.GetPrim().CreateAttribute("autonomyos:kind", Sdf.ValueTypeNames.String).Set(kind)
        return cube

    # Scenario-built PyBullet obstacles are all 1m cubes, including those labeled wall.
    for i, (x, y) in enumerate(scenario.obstacle_positions):
        kind = scenario.obstacle_types[i] if i < len(scenario.obstacle_types) else "obstacle"
        box(f"obstacle_{i}", (x, y, .5), (1, 1, 1), (.5, .5, .5), kind)
    x, y = scenario.target_position
    box("target", (x, y, .15), (.3, .3, .3), (.9, .2, .2), "target")
    x, y, theta = scenario.robot_start_position
    robot = box("robot", (x, y, .1), (.4, .3, .2), (.2, .4, .9), "robot")
    # Rotation precedes scale in the authored stack so non-square robot geometry rotates correctly.
    rotate = robot.AddRotateZOp()
    rotate.Set(math.degrees(theta))
    ops = robot.GetOrderedXformOps()
    robot.SetXformOpOrder([ops[0], ops[2], ops[1]])
    # Plane visualization only; not a physics collider.
    min_x, max_x, min_y, max_y = scenario.world_bounds
    box("floor", ((min_x+max_x)/2, (min_y+max_y)/2, -.05),
        (max_x-min_x, max_y-min_y, .1), (.15, .15, .15), "floor")
    stage.GetRootLayer().Save()
    return path
