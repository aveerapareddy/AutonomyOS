"""Real RGB/segmentation evaluation of a declared color baseline, not a learned detector."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
import pybullet as pb
from backend.simulator.environment import SimulationEnvironment
from backend.simulator.camera import default_camera_config,_view_matrix_from_config,_projection_matrix_from_config
from backend.experiments.runner import provenance

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(parents=True,exist_ok=False)
    rows=[];env=SimulationEnvironment(use_gui=False)
    try:
        for index,yaw in enumerate([0,90,180,270]):
            config=default_camera_config(width=320,height=240);config.yaw=yaw
            image=pb.getCameraImage(320,240,viewMatrix=_view_matrix_from_config(config),projectionMatrix=_projection_matrix_from_config(config),renderer=pb.ER_TINY_RENDERER,physicsClientId=env._client_id)
            rgb=np.array(image[2],dtype=np.uint8).reshape(240,320,4)[:,:,:3]
            segmentation=np.array(image[4]).reshape(240,320)
            truth=(segmentation & ((1<<24)-1))==env._world.target_id
            for variant in ['original','dimmed','red-distractor']:
                observed=rgb.copy()
                if variant=='dimmed':observed=(observed.astype(float)*.55).astype(np.uint8)
                if variant=='red-distractor':observed[20:45,20:45]=[220,30,30]
                r,g,b=[observed[:,:,i].astype(float) for i in range(3)]
                predicted=(r>70)&(r>1.7*g)&(r>1.7*b)
                tp=int(np.sum(predicted & truth));fp=int(np.sum(predicted & ~truth));fn=int(np.sum(~predicted & truth))
                row={'yaw':yaw,'variant':variant,'visible_truth_pixels':int(truth.sum()),'tp':tp,'fp':fp,'fn':fn,
                     'pixel_precision':tp/(tp+fp) if tp+fp else None,'pixel_recall':tp/(tp+fn) if tp+fn else None,
                     'pixel_iou':tp/(tp+fp+fn) if tp+fp+fn else None}
                name=f'view-{yaw}-{variant}'
                Image.fromarray(observed).save(a.output/(name+'.png'))
                Image.fromarray((truth*255).astype(np.uint8)).save(a.output/(name+'-truth.png'))
                rows.append(row)
    finally:env.shutdown()
    result={'method':'Fixed red-color segmentation baseline','truth':'Independent PyBullet object segmentation IDs',
       'case_count':len(rows),'rows':rows,'source':provenance(),
       'limitations':['No YOLO, vision-language model or learned image detector was used.','Synthetic views of one scene; no real-world generalization claim.','Red distractor deliberately tests a known baseline weakness.','Invisible target views have null recall rather than a claimed detection pass.']}
    (a.output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'original_iou':[r['pixel_iou'] for r in rows if r['variant']=='original'],'distractor_iou':[r['pixel_iou'] for r in rows if r['variant']=='red-distractor']},indent=2))
