import argparse
from pathlib import Path
from backend.operations.site import SiteSpec
from backend.integrations.openusd import export_scenario

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--site',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    site=SiteSpec.model_validate_json(a.site.read_text());a.output.parent.mkdir(parents=True,exist_ok=True);export_scenario(site.scenario(),a.output)
