"""Bounded, sequential controller-budget selection without held-out leakage."""
from dataclasses import asdict
from pathlib import Path
import json

from backend.experiments.runner import digest, provenance
from backend.scenarios.benchmark_runner import run_benchmark
from backend.scenarios.generator import generate_scenarios
from backend.services.mission_service import MissionService
from backend.services.telemetry_service import TelemetryService
from backend.simulator.execution_engine import ExecutionConfig

# Frozen before running the study; change study version for new candidates/splits.
PROTOCOL = {'version':'budget-study-v1', 'candidates':[4000,8000,12000], 'baseline':8000,
            'seeds':{'training':101,'validation':202,'held_out':303},
            'counts':{'training':12,'validation':12,'held_out':30},
            'shortlist_size':2,
            'objective':'Maximize successes, then minimize all-case simulator steps, then budget.',
            'limitations':['Kinematic simulation; completion is not collision safety.',
                           'Single fixed seed per split, small sample; no statistical generalization claim.',
                           'No latency optimization or learned controller.']}


def rank(result):
    return (-result['success_count'], result['total_simulator_steps'], result['budget'])


def select(results):
    if not results:
        raise ValueError('Cannot select from no results')
    return min(results,key=rank)['budget']


def paired(baseline, selected):
    b={r['scenario_id']:r for r in baseline['scenario_results']}
    s={r['scenario_id']:r for r in selected['scenario_results']}
    if set(b) != set(s) or len(b) != len(baseline['scenario_results']) or len(s) != len(selected['scenario_results']):
        raise ValueError('Paired comparison requires identical unique scenario IDs')
    regressions=[i for i in b if b[i]['success'] and not s[i]['success']]
    improvements=[i for i in b if not b[i]['success'] and s[i]['success']]
    return {'scenario_count':len(b),'regressions':regressions,'improvements':improvements,
            'success_delta':len(improvements)-len(regressions),
            'simulator_steps_delta':sum(s[i]['simulator_steps']-b[i]['simulator_steps'] for i in b)}


def run_study(output: Path):
    output.mkdir(parents=True,exist_ok=False)
    protocol=json.loads(json.dumps(PROTOCOL))
    (output/'protocol.json').write_text(json.dumps(protocol,indent=2)+'\n')
    source=provenance()
    sequence=[]
    manifests={}
    def cases(split):
        configs=generate_scenarios(protocol['counts'][split],protocol['seeds'][split])
        manifest=[s.model_dump(mode='json') for s in configs]
        manifests[split]=digest(manifest)
        (output/f'{split}-scenarios.json').write_text(json.dumps(manifest,indent=2)+'\n')
        return configs
    def evaluate(split,configs,budget):
        if budget not in protocol['candidates']:
            raise ValueError('Budget outside candidate set')
        telemetry=TelemetryService()
        summary=run_benchmark(configs,MissionService(),telemetry,f'{split}-{budget}',
                              'bounded-budget-study',ExecutionConfig(max_steps_per_waypoint=budget))
        result=summary.model_dump(mode='json')
        result.update({'budget':budget,'split':split,'config':asdict(ExecutionConfig(max_steps_per_waypoint=budget)),
                       'total_simulator_steps':sum(r.simulator_steps for r in summary.scenario_results)})
        (output/f'{split}-{budget}.json').write_text(json.dumps(result,indent=2)+'\n')
        (output/f'{split}-{budget}-traces.json').write_text(json.dumps(telemetry.export(),indent=2)+'\n')
        sequence.append({'split':split,'budget':budget,'scenario_hash':manifests[split]})
        return result
    training_cases=cases('training')
    training=[evaluate('training',training_cases,b) for b in protocol['candidates']]
    shortlist=[r['budget'] for r in sorted(training,key=rank)[:protocol['shortlist_size']]]
    validation_cases=cases('validation')
    validation=[evaluate('validation',validation_cases,b) for b in shortlist]
    selected=select(validation)
    lock={'protocol_hash':digest(protocol),'shortlist':shortlist,'selected_budget':selected,
          'training_results_hash':digest(training),'validation_results_hash':digest(validation),
          'source':source,'selection_uses_held_out':False}
    lock_path=output/'selection-lock.json'
    lock_path.write_text(json.dumps(lock,indent=2)+'\n')
    lock_hash=digest(lock)
    # No held-out scenarios are generated or executed until selection is written.
    held_cases=cases('held_out')
    baseline=evaluate('held_out',held_cases,protocol['baseline'])
    held_selected=baseline if selected==protocol['baseline'] else evaluate('held_out',held_cases,selected)
    if digest(json.loads(lock_path.read_text())) != lock_hash:
        raise RuntimeError('Selection changed during held-out evaluation')
    result={'protocol':protocol,'source':source,'scenario_hashes':manifests,
            'selection_lock_hash':lock_hash,'selected_budget':selected,'evaluation_sequence':sequence,
            'training':[{k:r[k] for k in ('budget','success_count','total_simulator_steps')} for r in training],
            'validation':[{k:r[k] for k in ('budget','success_count','total_simulator_steps')} for r in validation],
            'held_out':{'baseline_success':baseline['success_count'],'selected_success':held_selected['success_count'],
                        'paired':paired(baseline,held_selected)},
            'claim':'Observed results on this fixed procedural test set only; no improvement assumed.'}
    (output/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
