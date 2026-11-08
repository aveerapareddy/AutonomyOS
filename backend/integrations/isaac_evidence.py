"""Independent postcondition checks: simulator process exit status is insufficient."""
import hashlib
import json
import math
from pathlib import Path
import struct


def verify_robot_evidence(directory: Path, stage: Path) -> dict:
    report=json.loads((directory/'report.json').read_text())
    if report.get('passed') is not True:raise ValueError('Isaac robot report did not pass')
    if report.get('stage_sha256')!=hashlib.sha256(stage.read_bytes()).hexdigest():raise ValueError('Isaac input stage hash mismatch')
    vectors=[report.get('initial_position'),report.get('final_position'),report.get('goal')]
    for vector,size in zip(vectors,[3,3,2]):
        if not isinstance(vector,list) or len(vector)!=size or any(not isinstance(v,(int,float)) or not math.isfinite(v) for v in vector):raise ValueError('Invalid Isaac pose')
    initial,final,goal=vectors
    error=math.dist(final[:2],goal)
    if error>=.5 or abs(error-report.get('final_goal_error_m',math.inf))>1e-6 or math.dist(initial[:2],final[:2])<10:raise ValueError('Isaac trajectory did not reach the lane goal')
    if not 100<report.get('controller_steps',0)<=4200 or len(report.get('trajectory',[]))<2:raise ValueError('Missing bounded Isaac trajectory')
    frames=report.get('sensor_frames',{})
    if set(frames)!={'initial-rgb','final-rgb'}:raise ValueError('Missing required RTX frames')
    for name,frame in frames.items():
        if frame.get('path')!=name+'.png':raise ValueError('Unsafe sensor frame path')
        raw=(directory/frame['path']).read_bytes()
        if hashlib.sha256(raw).hexdigest()!=frame.get('sha256'):raise ValueError('RTX frame hash mismatch')
        if raw[:8]!=b'\x89PNG\r\n\x1a\n' or struct.unpack('>II',raw[16:24])!=(320,240):raise ValueError('Invalid RTX PNG dimensions')
        if frame.get('shape')!=[240,320,4] or not math.isfinite(frame.get('rgb_std',0)) or frame.get('rgb_std',0)<=1:raise ValueError('RTX frame is missing nonblank evidence')
    return {'passed':True,'final_goal_error_m':error,'controller_steps':report['controller_steps'],
            'frames_verified':2,'isaacsim':report.get('isaacsim'),'stage_sha256':report['stage_sha256']}
