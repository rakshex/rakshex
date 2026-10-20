"""Emit a synthetic local-validation manifest; not a real provider migration."""
import argparse
import json
from pathlib import Path
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--repository',required=True)
parser.add_argument('--base-sha',required=True)
parser.add_argument('--base-branch',required=True)
args=parser.parse_args()
fixture=Path(__file__).resolve().parents[1]/'repair-fixtures/python-json-rename'
manifest=json.loads((fixture/'contracts.json').read_text())
manifest['files']={p.relative_to(fixture).as_posix():p.read_text() for p in fixture.rglob('*.py')}
manifest['source_root']='repair-fixtures/python-json-rename'
manifest.update(repository=args.repository,base_sha=args.base_sha,base_branch=args.base_branch)
print(json.dumps(manifest,indent=2))
