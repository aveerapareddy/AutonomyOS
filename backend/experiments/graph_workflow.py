"""LangGraph orchestration over the authoritative policy/approval/tool journal.

A graph resume is not an approval. Only an already-recorded exact-digest approval
allows the tool node to execute. All graph checkpoints stay in local SQLite.
"""
from pathlib import Path
from typing_extensions import TypedDict
from langgraph.graph import START,END,StateGraph
from langgraph.types import Command,interrupt
from langgraph.checkpoint.sqlite import SqliteSaver
from langsmith import tracing_context
from backend.experiments.agent_workflow import AgentWorkflow,WorkflowPolicy,WorkflowError

class State(TypedDict,total=False):
    workflow_id:str
    proposal_digest:str
    result:dict
    evaluation_passed:bool


def run_graph(root:Path,ident:str,resume=False,policy:WorkflowPolicy|None=None):
    controller=AgentWorkflow(root,policy or WorkflowPolicy(max_scenarios=10))
    controller.get(ident)  # Identifier and existence validation precede checkpoint access.
    def proposal_node(state):
        item=controller.get(state['workflow_id'])
        return {'proposal_digest':item['digest']}
    def review_node(state):
        item=controller.get(state['workflow_id'])
        if item['status']=='awaiting_approval':
            interrupt({'workflow_id':item['id'],'digest':item['digest'],'message':'Approve/reject this exact request through the operator review interface.'})
        item=controller.get(state['workflow_id'])
        if item['status'] not in {'approved','completed'}:raise WorkflowError('A graph resume cannot replace recorded approval')
        if item['digest']!=state['proposal_digest']:raise WorkflowError('Proposal changed after graph checkpoint')
        return {}
    def tool_node(state):
        return {'result':controller.execute(state['workflow_id'])}
    def evaluation_node(state):
        report=state['result']['experiment']
        if not report['evaluation_passed'] or report['status']!='completed':raise WorkflowError('Independent evaluation gate failed')
        return {'evaluation_passed':True}
    builder=StateGraph(State)
    for name,node in [('model_proposal',proposal_node),('review_gate',review_node),('simulation_tool',tool_node),('evaluation',evaluation_node)]:builder.add_node(name,node)
    for a,b in [(START,'model_proposal'),('model_proposal','review_gate'),('review_gate','simulation_tool'),('simulation_tool','evaluation'),('evaluation',END)]:builder.add_edge(a,b)
    config={'configurable':{'thread_id':ident}}
    with SqliteSaver.from_conn_string(str(controller.root/'graph-checkpoints.sqlite3')) as saver:
        graph=builder.compile(checkpointer=saver)
        before=graph.get_state(config)
        with tracing_context(enabled=False):
            if not before.values:graph.invoke({'workflow_id':ident},config)
            elif resume:graph.invoke(Command(resume=True) if before.next else None,config)
        state=graph.get_state(config)
        result={'framework':'LangGraph','workflow_id':ident,'paused':bool(state.next),
                'next_nodes':list(state.next),'evaluation_passed':state.values.get('evaluation_passed',False),
                'proposal_digest':state.values.get('proposal_digest'),
                'checkpoint_storage':'local SQLite','remote_tracing':False,
                'automatic_dispatch_guarantee':'At-most-once automatic dispatch via authoritative tool journal; no automatic retry after interrupted tool claim.'}
    return result
