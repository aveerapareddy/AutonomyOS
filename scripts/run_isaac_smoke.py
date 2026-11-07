"""Run in an isolated, licensed Isaac Sim environment on an RTX GPU.

Opens AutonomyOS geometry and simulates a falling probe on the exported floor.
This checks interchange and basic physics, not robot control or safety.
Does not accept any license automatically.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    start = time.perf_counter()
    from isaacsim import SimulationApp
    app = SimulationApp({"headless": True})
    try:
        import omni.usd
        from pxr import Gf, UsdGeom, UsdPhysics
        from isaacsim.core.api import World
        if not omni.usd.get_context().open_stage(str(args.stage.resolve())):
            raise RuntimeError("Isaac Sim could not open the stage")
        app.update()
        stage = omni.usd.get_context().get_stage()
        if not stage.GetPrimAtPath("/World/robot") or not stage.GetPrimAtPath("/World/target"):
            raise RuntimeError("AutonomyOS robot/target geometry is missing")
        floor = stage.GetPrimAtPath("/World/floor")
        UsdPhysics.CollisionAPI.Apply(floor)
        probe = UsdGeom.Cube.Define(stage, "/World/PhysicsProbe")
        probe.CreateSizeAttr(.2)
        probe.AddTranslateOp().Set(Gf.Vec3d(0, 0, 1.5))
        UsdPhysics.CollisionAPI.Apply(probe.GetPrim())
        UsdPhysics.RigidBodyAPI.Apply(probe.GetPrim())
        UsdPhysics.MassAPI.Apply(probe.GetPrim()).CreateMassAttr(1.0)
        world = World(physics_dt=1/60, rendering_dt=1/60, stage_units_in_meters=1)
        world.reset()
        initial_z = 1.5
        for _ in range(120):
            world.step(render=False)
        from pxr import Usd
        transform = UsdGeom.Xformable(probe).ComputeLocalToWorldTransform(Usd.TimeCode.Default())
        final_z = float(transform.ExtractTranslation()[2])
        passed = .05 < final_z < .2
        report = {"passed": passed, "stage_sha256": hashlib.sha256(args.stage.read_bytes()).hexdigest(),
                  "steps": 120, "physics_dt": 1/60, "probe_initial_z": initial_z,
                  "probe_final_z": final_z, "elapsed_seconds": time.perf_counter()-start,
                  "limitations": ["Geometry import plus falling-body smoke test only.",
                                  "No Isaac robot navigation or physical safety validation."]}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report))
        return 0 if passed else 1
    finally:
        app.close()


if __name__ == "__main__":
    raise SystemExit(main())
