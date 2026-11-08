import hashlib
import json
import struct
import pytest
from backend.integrations.isaac_evidence import verify_robot_evidence


def test_zero_exit_cannot_override_failed_isaac_report(tmp_path):
    (tmp_path/'report.json').write_text(json.dumps({'passed':False,'process_exit_code':0}))
    with pytest.raises(ValueError,match='did not pass'):verify_robot_evidence(tmp_path,tmp_path/'stage.usda')


def test_isaac_artifact_gate_rejects_movement_and_frame_corruption(tmp_path):
    stage=tmp_path/'stage.usda';stage.write_text('#usda 1.0')
    # Deliberately minimal PNG header: this test validates dimensions/hash gates, not image decoding.
    raw=b'\x89PNG\r\n\x1a\n'+b'\0'*8+struct.pack('>II',320,240)
    frames={}
    for name in ['initial-rgb','final-rgb']:
        (tmp_path/(name+'.png')).write_bytes(raw)
        frames[name]={'path':name+'.png','sha256':hashlib.sha256(raw).hexdigest(),'shape':[240,320,4],'rgb_std':20}
    report={'passed':True,'stage_sha256':hashlib.sha256(stage.read_bytes()).hexdigest(),'initial_position':[0,-6,.1],
            'final_position':[0,5.8,.1],'goal':[0,6],'final_goal_error_m':.2,'controller_steps':3000,'trajectory':[{},{}],'sensor_frames':frames}
    def save(): (tmp_path/'report.json').write_text(json.dumps(report))
    save();assert verify_robot_evidence(tmp_path,stage)['frames_verified']==2
    report['initial_position']=[0,5,.1];save()
    with pytest.raises(ValueError,match='trajectory'):verify_robot_evidence(tmp_path,stage)
    report['initial_position']=[0,-6,.1];save();(tmp_path/'final-rgb.png').write_bytes(b'corrupted')
    with pytest.raises(ValueError,match='hash mismatch'):verify_robot_evidence(tmp_path,stage)
