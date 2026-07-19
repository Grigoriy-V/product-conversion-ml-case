import argparse, hashlib, json, re, sys, tomllib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REQUIRED=['README.md','AGENTS.md','VERSION','ORCHESTRATION_ROADMAP.md','PROJECT_LOG.md','tools/agent_ledger.py','tools/bootstrap_project.py','tools/sync_core.py','reports/agent_execution_ledger.schema.json','reports/agent_execution_ledger.jsonl','core/task_spec.schema.json','core/project_manifest.schema.json','docs/agent_orchestration.md','orchestration_manifest.json']
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=ROOT);p.add_argument('--write-manifest',action='store_true');a=p.parse_args(argv); root=a.root.resolve(); errors=[]
 adapter=(root/'orchestration.lock.json').is_file()
 if adapter:
  required=['AGENTS.md','ML_PROJECT_ROADMAP.md','PROJECT_LOG.md','PROJECT_ROADMAP.md','orchestration.lock.json','tools/agent_ledger.py','tools/validate_core_pin.py','tools/experiment_ledger.py','reports/agent_execution_ledger.schema.json','reports/agent_execution_ledger.jsonl','reports/experiment_ledger.schema.json','reports/experiment_ledger.jsonl','core/orchestration_lock.schema.json','docs/agent_orchestration.md','docs/classical_ml_adapter.md']
 else: required=REQUIRED
 for x in required:
  if not (root/x).exists(): errors.append('missing '+x)
 for x in [root/'.codex/config.toml',*sorted((root/'.codex/agents').glob('*.toml'))]:
  try: tomllib.loads(x.read_text(encoding='utf-8'))
  except Exception as e: errors.append(f'TOML {x.relative_to(root)}: {e}')
 for x in ['reports/agent_execution_ledger.schema.json','core/task_spec.schema.json','core/project_manifest.schema.json',*([] if not adapter else ['reports/experiment_ledger.schema.json','core/orchestration_lock.schema.json'])]:
  try:
   data=json.loads((root/x).read_text(encoding='utf-8'))
   if not isinstance(data,dict) or data.get('type')!='object': raise ValueError('expected object schema')
  except Exception as e: errors.append(f'schema {x}: {e}')
 try:
  sys.path.insert(0,str(root/'tools')); import agent_ledger as ledger
  for e in ledger.read_events(root/'reports/agent_execution_ledger.jsonl'): ledger.validate(e)
 except Exception as e: errors.append(f'ledger: {e}')
 if adapter:
  try:
   import validate_core_pin
   validate_core_pin.validate_pin(root=root)
  except Exception as e: errors.append(f'Core pin: {e}')
  try:
   import experiment_ledger
   experiment_ledger.validate_ledger(root/'reports/experiment_ledger.jsonl',root=root)
  except Exception as e: errors.append(f'experiment ledger: {e}')
 mutable={'PROJECT_LOG.md','ORCHESTRATION_ROADMAP.md'}
 owned={str(x.relative_to(root)).replace('\\','/'):digest(x) for x in sorted(root.rglob('*')) if x.is_file() and '.git' not in x.parts and x.name!='orchestration_manifest.json' and x.name not in mutable and ('reports' not in x.parts or x.name.endswith('.schema.json')) and not x.name.endswith('.lock') and '__pycache__' not in x.parts}
 if a.write_manifest: (root/'orchestration_manifest.json').write_text(json.dumps({'core_version':(root/'VERSION').read_text().strip(),'owned_files':owned},indent=2)+'\n',encoding='utf-8')
 elif not adapter:
  try:
   man=json.loads((root/'orchestration_manifest.json').read_text(encoding='utf-8'))
   if not isinstance(man,dict) or not isinstance(man.get('core_version'),str) or not isinstance(man.get('owned_files'),dict): raise ValueError('invalid manifest shape')
   if man['owned_files']!=owned: errors.append('manifest hashes differ')
   for critical in ('tools/agent_ledger.py','tools/validate_orchestration.py','tools/bootstrap_project.py','tools/sync_core.py','reports/agent_execution_ledger.schema.json','core/task_spec.schema.json','core/project_manifest.schema.json'):
    if critical not in man['owned_files']: errors.append('manifest missing critical '+critical)
  except Exception as e: errors.append(f'manifest: {e}')
 tracked='\n'.join(str(x.relative_to(root)) for x in root.rglob('*') if x.is_file() and '.git' not in x.parts)
 if re.search(r'(?im)(?:[A-Z]:\\Users\\|/home/|api[_-]?key\s*=)',tracked): errors.append('absolute/private-pattern scan failed')
 if errors: print('\n'.join(errors),file=sys.stderr); return 2
 print('valid: orchestration core'); return 0
if __name__=='__main__': raise SystemExit(main())
