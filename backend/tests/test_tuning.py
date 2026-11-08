import pytest
from backend.experiments.tuning import select,paired,PROTOCOL


def test_selection_prioritizes_completion_and_breaks_ties_deterministically():
    assert select([{'budget':4000,'success_count':9,'total_simulator_steps':1},
                   {'budget':8000,'success_count':10,'total_simulator_steps':100}])==8000
    assert select([{'budget':12000,'success_count':10,'total_simulator_steps':100},
                   {'budget':8000,'success_count':10,'total_simulator_steps':100}])==8000
    with pytest.raises(ValueError):select([])


def test_paired_metrics_preserve_regressions_and_reject_different_scenarios():
    b={'scenario_results':[{'scenario_id':'a','success':True,'simulator_steps':10},
                           {'scenario_id':'b','success':False,'simulator_steps':20}]}
    s={'scenario_results':[{'scenario_id':'a','success':False,'simulator_steps':5},
                           {'scenario_id':'b','success':True,'simulator_steps':30}]}
    assert paired(b,s)=={'scenario_count':2,'regressions':['a'],'improvements':['b'],'success_delta':0,'simulator_steps_delta':5}
    with pytest.raises(ValueError):paired(b,{'scenario_results':[]})


def test_protocol_has_distinct_split_seeds_and_bounded_work():
    assert len(set(PROTOCOL['seeds'].values()))==3
    assert max(PROTOCOL['candidates'])==12000
    assert sum(PROTOCOL['counts'].values())<=100


def test_held_out_not_executed_until_selection_is_persisted(tmp_path,monkeypatch):
    import json
    from types import SimpleNamespace
    from backend.experiments import tuning
    observed=[]
    def benchmark(configs,mission,telemetry,ident,name,config):
        split=ident.rsplit('-',1)[0]
        if split=='held_out':
            lock=json.loads((tmp_path/'study/selection-lock.json').read_text())
            assert lock['selection_uses_held_out'] is False
            observed.append(lock['selected_budget'])
        rows=[SimpleNamespace(simulator_steps=5)]
        return SimpleNamespace(scenario_results=rows,model_dump=lambda **kwargs:{
            'success_count':len(configs),'scenario_results':[
                {'scenario_id':c.scenario_id,'success':True,'simulator_steps':5} for c in configs]})
    monkeypatch.setattr(tuning,'run_benchmark',benchmark)
    result=tuning.run_study(tmp_path/'study')
    assert observed
    assert result['evaluation_sequence'][-1]['split']=='held_out'
    assert result['held_out']['paired']['success_delta']==0
