"""Allowlisted subprocess worker. Has its own wall-clock watchdog."""
import argparse
import json
import os
from pathlib import Path
from threading import Timer
from backend.operations.jobs import JobRequest
from backend.experiments.runner import digest,run_experiment,provenance
from backend.experiments.ledger import Ledger
from backend.services.mission_service import MissionService
from backend.services.telemetry_service import TelemetryService
from backend.services.orchestrator_service import OrchestratorService
from backend.schemas.mission import MissionRequest
from backend.scenarios.benchmark_runner import _layout_from_scenario,_world_layout_spec_from_scenario


def execute(directory):
    request=JobRequest.model_validate_json((directory/'request.json').read_text())
    output=directory/'run';output.mkdir(exist_ok=False)
    if request.kind=='experiment':
        report=run_experiment(request.experiment,Ledger(directory/'experiments.sqlite3'),output/'experiment')
        result={'kind':'experiment','report':report.model_dump(mode='json'),'evaluation_passed':report.evaluation_passed}
    else:
        site=request.site;scenario=site.scenario();telemetry=TelemetryService();missions=MissionService()
        mission=missions.create(MissionRequest(mission_text='Go to target'))
        orchestrator=OrchestratorService(missions,telemetry,world_layout_provider=lambda:_layout_from_scenario(scenario),
          robot_start_provider=lambda:scenario.robot_start_position,
          execution_world_layout_provider=lambda:_world_layout_spec_from_scenario(scenario),geometry_aware=True)
        summary=orchestrator.execute(mission.mission_id)
        result={'kind':'site','evaluation_passed':summary.status=='completed','site':site.model_dump(mode='json'),'site_hash':digest(site.model_dump(mode='json')),
                'scenario':scenario.model_dump(mode='json'),'summary':summary.model_dump(mode='json'),
                'telemetry':telemetry.export()[mission.mission_id],'source':provenance()}
        (output/'site.json').write_text(site.model_dump_json(indent=2)+'\n')
    result['input_hash']=digest(request.model_dump(mode='json'))
    (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--directory',type=Path,required=True);args=parser.parse_args()
    watchdog=Timer(60,lambda:os._exit(124));watchdog.daemon=True;watchdog.start()
    try:execute(args.directory)
    finally:watchdog.cancel()
