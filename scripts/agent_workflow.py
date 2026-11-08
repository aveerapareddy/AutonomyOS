"""Local operator commands; review an exact proposal before executing its tool."""
import argparse
import json
from pathlib import Path
from backend.experiments.agent_workflow import AgentWorkflow


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path('artifacts/agent-workflows'))
    sub = parser.add_subparsers(dest='action', required=True)
    submit = sub.add_parser('submit'); submit.add_argument('inference', type=Path)
    inspect = sub.add_parser('show'); inspect.add_argument('workflow_id')
    approve = sub.add_parser('approve'); approve.add_argument('workflow_id')
    approve.add_argument('--digest', required=True); approve.add_argument('--reviewer', required=True)
    reject = sub.add_parser('reject'); reject.add_argument('workflow_id')
    reject.add_argument('--reviewer', required=True); reject.add_argument('--reason', required=True)
    execute = sub.add_parser('execute'); execute.add_argument('workflow_id')
    args = parser.parse_args()
    workflow = AgentWorkflow(args.root)
    if args.action == 'submit': result = workflow.submit_inference(args.inference)
    elif args.action == 'show': result = workflow.get(args.workflow_id)
    elif args.action == 'approve': result = workflow.approve(args.workflow_id, args.digest, args.reviewer)
    elif args.action == 'reject': result = workflow.reject(args.workflow_id, args.reviewer, args.reason)
    else: result = workflow.execute(args.workflow_id)
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main()
