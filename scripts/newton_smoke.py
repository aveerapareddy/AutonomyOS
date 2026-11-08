"""Optional real Newton/Warp CPU contact smoke; no GPU claim."""
import argparse
import importlib.metadata
import json
import math
from pathlib import Path
import platform

def run():
    import newton
    import newton.solvers
    import warp as wp
    wp.init()
    with wp.ScopedDevice('cpu'):
        builder=newton.ModelBuilder()
        builder.add_ground_plane()
        body=builder.add_body(xform=wp.transform(p=wp.vec3(0.,0.,1.5),q=wp.quat_identity()),label='autonomy_probe')
        builder.add_shape_box(body,hx=.1,hy=.1,hz=.1)
        model=builder.finalize(device='cpu')
        a,b=model.state(),model.state();control=model.control()
        collision=newton.CollisionPipeline(model);contacts=collision.contacts()
        solver=newton.solvers.SolverXPBD(model,iterations=10)
        initial=float(a.body_q.numpy()[body][2]);heights=[]
        for step in range(480):
            a.clear_forces();collision.collide(a,contacts);solver.step(a,b,control,contacts,1/240);a,b=b,a
            if step%24==0:heights.append({'step':step+1,'z':float(a.body_q.numpy()[body][2])})
        final=float(a.body_q.numpy()[body][2])
        return {'passed':math.isfinite(final) and .05<final<.2 and initial-final>1,
                'device':'cpu','solver':'SolverXPBD','physics_steps':480,'dt':1/240,
                'initial_z':initial,'final_z':final,'height_samples':heights,
                'versions':{p:importlib.metadata.version(p) for p in ['newton','warp-lang','numpy']},
                'platform':platform.platform(),'limitations':['CPU-only box-ground contact smoke; not a robot controller or GPU performance test.']}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    result=run();a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(result,f,indent=2);f.write('\n')
    print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
