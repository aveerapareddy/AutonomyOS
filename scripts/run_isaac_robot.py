"""Licensed optional Isaac Jetbot closed-loop lane and RTX-camera validation.

This is one bounded straight-lane case, not a general navigation or safety claim.
The caller must already have accepted the relevant Omniverse license.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
from pathlib import Path
import time


def run(stage_path,output):
    from isaacsim import SimulationApp
    app=SimulationApp({'headless':True,'renderer':'RayTracedLighting','width':640,'height':480})
    started=time.perf_counter();output.mkdir(parents=True,exist_ok=False)
    report={'passed':False,'stage_sha256':hashlib.sha256(stage_path.read_bytes()).hexdigest(),
            'isaacsim':importlib.metadata.version('isaacsim'),'limitations':['One straight-lane goal-following case, not a general navigation benchmark.',
             'Default World physics configuration; GPU dynamics not explicitly enabled.','RTX RGB frames are checked for valid, nonblank output; no learned sensor accuracy claim.']}
    try:
        import numpy as np
        import omni.usd
        from pxr import UsdPhysics,UsdLux
        from PIL import Image
        from isaacsim.core.api import World
        from isaacsim.core.utils.extensions import enable_extension
        enable_extension("isaacsim.robot.wheeled_robots")
        enable_extension("isaacsim.sensors.camera")
        from isaacsim.storage.native import get_assets_root_path
        from isaacsim.robot.wheeled_robots.robots import WheeledRobot
        from isaacsim.robot.wheeled_robots.controllers.differential_controller import DifferentialController
        from isaacsim.sensors.camera import Camera
        if not omni.usd.get_context().open_stage(str(stage_path.resolve())):raise RuntimeError('Stage import failed')
        app.update();stage=omni.usd.get_context().get_stage()
        stage.RemovePrim('/World/robot')
        UsdLux.DomeLight.Define(stage,'/World/ValidationLight').CreateIntensityAttr(1000.)
        for prim in stage.Traverse():
            if str(prim.GetPath()).startswith('/World/obstacle_') or str(prim.GetPath())=='/World/floor':UsdPhysics.CollisionAPI.Apply(prim)
        asset_root=get_assets_root_path()
        if not asset_root:raise RuntimeError('Official Isaac robot assets unavailable')
        asset=asset_root+'/Isaac/Robots/NVIDIA/Jetbot/jetbot.usd'
        world=World(physics_dt=1/60,rendering_dt=1/60,stage_units_in_meters=1)
        robot=world.scene.add(WheeledRobot(prim_path='/World/Jetbot',name='autonomy_jetbot',
             wheel_dof_names=['left_wheel_joint','right_wheel_joint'],create_robot=True,usd_path=asset,
             position=np.array([0.,-6.,.1]),orientation=np.array([math.sqrt(.5),0.,0.,math.sqrt(.5)])))
        camera=Camera(prim_path='/World/OverviewCamera',name='overview',position=np.array([0.,0.,20.]),
                      orientation=np.array([math.sqrt(.5),0.,math.sqrt(.5),0.]),frequency=20,resolution=(320,240))
        world.reset();camera.initialize();camera.set_focal_length(1.6);camera.add_rgb_to_frame()
        drive=DifferentialController(name='bounded_lane_controller',wheel_radius=.03,wheel_base=.1125)
        frames={}
        def capture(name):
            for _ in range(120):
                world.step(render=True)
                rgba=np.asarray(camera.get_rgba())
                if rgba.shape==(240,320,4) and np.isfinite(rgba).all() and float(rgba[:,:,:3].std())>1:break
            if rgba.shape!=(240,320,4) or not np.isfinite(rgba).all() or float(rgba[:,:,:3].std())<=1:raise RuntimeError('Camera frame missing or blank')
            path=output/(name+'.png');Image.fromarray(rgba.astype(np.uint8),'RGBA').save(path)
            frames[name]={'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'shape':list(rgba.shape),'rgb_std':float(rgba[:,:,:3].std())}
        robot.apply_wheel_actions(drive.forward(command=[0.,0.]))
        capture('initial-rgb');initial=robot.get_world_pose()[0].tolist();trajectory=[];goal=np.array([0.,6.])
        reached=False
        for step in range(4200):
            position,orientation=robot.get_world_pose()
            w,x,y,z=[float(v) for v in orientation]
            yaw=math.atan2(2*(w*z+x*y),1-2*(y*y+z*z));delta=goal-position[:2]
            distance=float(np.linalg.norm(delta))
            if step%30==0:trajectory.append({'step':step,'x':float(position[0]),'y':float(position[1]),'z':float(position[2]),'yaw':yaw,'goal_distance':distance})
            if distance<.4:reached=True;break
            desired=math.atan2(float(delta[1]),float(delta[0]));error=math.atan2(math.sin(desired-yaw),math.cos(desired-yaw))
            linear=min(.25,.6*distance) if abs(error)<.25 else 0.
            angular=max(-1.5,min(1.5,2*error))
            robot.apply_wheel_actions(drive.forward(command=[linear,angular]))
            world.step(render=step%120==0)
        robot.apply_wheel_actions(drive.forward(command=[0.,0.]))
        capture('final-rgb');final=robot.get_world_pose()[0].tolist();error=float(np.linalg.norm(goal-np.array(final[:2])))
        report.update({'passed':bool(reached and error<.5),'robot_asset':asset,'wheel_dof_names':['left_wheel_joint','right_wheel_joint'],
          'initial_position':initial,'final_position':final,'goal':goal.tolist(),'final_goal_error_m':error,
          'physics_dt':1/60,'maximum_controller_steps':4200,'controller_steps':step+1,'trajectory':trajectory,
          'sensor_frames':frames,'camera_intrinsics':np.asarray(camera.get_intrinsics_matrix()).tolist(),
          'controller':'closed-loop bounded differential drive','renderer':'RayTracedLighting'})
    except Exception as exc:
        report['error']={'type':type(exc).__name__,'message':str(exc)}
        raise
    finally:
        report['elapsed_seconds']=time.perf_counter()-started
        (output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
        app.close()
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=run(a.stage,a.output);print(json.dumps({k:v for k,v in result.items() if k!='trajectory'},indent=2));raise SystemExit(0 if result['passed'] else 1)
