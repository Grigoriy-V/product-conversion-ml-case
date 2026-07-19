"""Append-only, schema-checked agent ledger helper."""
import argparse, json, os, re, sys, uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]; SCHEMA=ROOT/'reports'/'agent_execution_ledger.schema.json'
class LedgerError(ValueError): pass
def utc(): return datetime.now(timezone.utc).isoformat().replace('+00:00','Z')
def load_schema(): return json.loads(SCHEMA.read_text(encoding='utf-8'))
def read_events(path):
    if not path.exists(): return []
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x.strip()]
def validate(event):
    check_schema(event,load_schema())
    if event['event_type'] in {'started','completed','failed','interrupted'} and event['supervisor_decision'] is not None: raise LedgerError('worker event cannot decide')
    if any(not isinstance(x,str) or re.match(r'^(?:[A-Za-z]:|/|\\)',x) for x in event['files_changed']): raise LedgerError('absolute file path')
def lifecycle(events,event):
    all_events=events+[event]; state={}
    for x in all_events:
        run=x['agent_run_id']; prior=state.setdefault(run,[]); kind=x['event_type']
        if kind=='started' and any(y['event_type']=='started' for y in prior): raise LedgerError('duplicate run start')
        if kind in {'completed','failed','interrupted'} and (not any(y['event_type']=='started' for y in prior) or any(y['event_type'] in {'completed','failed','interrupted'} for y in prior)): raise LedgerError('invalid terminal transition')
        if kind=='reviewed' and (not any(y['event_type'] in {'completed','failed','interrupted'} for y in prior) or any(y['event_type']=='reviewed' for y in prior)): raise LedgerError('invalid review transition')
        prior.append(x)
def check_schema(value,schema,path='$'):
    if 'allOf' in schema:
        for s in schema['allOf']: check_schema(value,s,path)
    if 'if' in schema:
        try: check_schema(value,schema['if'],path)
        except LedgerError: pass
        else:
            if 'then' in schema: check_schema(value,schema['then'],path)
    if 'const' in schema and value!=schema['const']: raise LedgerError(f'{path}: const')
    if 'enum' in schema and value not in schema['enum']: raise LedgerError(f'{path}: enum')
    typ=schema.get('type')
    if typ:
        types=typ if isinstance(typ,list) else [typ]; ok=False
        for t in types:
            ok |= (t=='object' and isinstance(value,dict)) or (t=='array' and isinstance(value,list)) or (t=='string' and isinstance(value,str)) or (t=='number' and isinstance(value,(int,float)) and not isinstance(value,bool)) or (t=='null' and value is None)
        if not ok: raise LedgerError(f'{path}: type')
    if isinstance(value,dict):
        for k in schema.get('required',[]):
            if k not in value: raise LedgerError(f'{path}.{k}: required')
        props=schema.get('properties',{})
        if schema.get('additionalProperties') is False and any(k not in props for k in value): raise LedgerError(f'{path}: unknown property')
        for k,v in value.items():
            if k in props: check_schema(v,props[k],f'{path}.{k}')
    if isinstance(value,list) and 'items' in schema:
        for i,v in enumerate(value): check_schema(v,schema['items'],f'{path}[{i}]')
    if isinstance(value,str):
        if 'minLength' in schema and len(value)<schema['minLength']: raise LedgerError(f'{path}: minLength')
        if 'pattern' in schema and not re.search(schema['pattern'],value): raise LedgerError(f'{path}: pattern')
    if isinstance(value,(int,float)) and 'minimum' in schema and value<schema['minimum']: raise LedgerError(f'{path}: minimum')
@contextmanager
def locked(path):
    path.parent.mkdir(parents=True,exist_ok=True)
    # Atomic sidecar creation is fail-closed on every platform. A stale file
    # blocks work; remove it manually only after confirming no writer exists.
    lock_path=path.with_name(path.name+'.lock')
    try: fd=os.open(lock_path,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError as exc: raise LedgerError(f'lock exists: {lock_path}; fail closed') from exc
    try:
        os.write(fd,b'locked\n'); os.close(fd)
        with open(path,'a+',encoding='utf-8',newline='\n') as f: yield f
    finally:
        try: os.close(fd)
        except OSError: pass
        try: os.unlink(lock_path)
        except FileNotFoundError: pass
def append(path,event,dry=False):
    validate(event)
    if dry:return
    with locked(path) as f:
        events=read_events(path); lifecycle(events,event)
        if any(x['event_id']==event['event_id'] for x in events): raise LedgerError('duplicate event id')
        f.seek(0,2); f.write(json.dumps(event,ensure_ascii=False,separators=(',',':'))+'\n'); f.flush(); os.fsync(f.fileno())
def base(meta):
    required=['agent_run_id','parent_task','agent_name','requested_model','requested_reasoning','task_type','roadmap_step','scope_summary','constraints','commands','files_changed','git_commit_before','git_commit_after','ml_ledger_event_ids','notes']
    if not isinstance(meta,dict) or any(k not in meta for k in required): raise LedgerError('start metadata missing required field')
    return {**meta,'schema_version':'1.0','event_id':str(uuid.uuid4()),'timestamp_utc':utc(),'event_type':'started','status':'started','supervisor_decision':None,'outcome_summary':None,'duration_seconds':None}
def main(argv=None):
 p=argparse.ArgumentParser(); p.add_argument('--ledger',type=Path,default=ROOT/'reports'/'agent_execution_ledger.jsonl'); p.add_argument('--dry-run',action='store_true'); s=p.add_subparsers(dest='cmd',required=True); a=s.add_parser('start');g=a.add_mutually_exclusive_group(required=True);g.add_argument('--metadata-json');g.add_argument('--metadata-file',type=Path); a=s.add_parser('terminal');a.add_argument('--run-id',required=True);a.add_argument('--status',choices=['completed','failed','interrupted'],required=True);a.add_argument('--outcome-summary',required=True);a.add_argument('--files-changed-json',required=True);a.add_argument('--commands-json',required=True);a.add_argument('--notes',default='Created by tools/agent_ledger.py.'); a=s.add_parser('review');a.add_argument('--run-id',required=True);a.add_argument('--decision',choices=['accept','reject','change'],required=True);a.add_argument('--outcome-summary',required=True);a.add_argument('--reviewer-agent-name',required=True);a.add_argument('--reviewer-model',required=True);a.add_argument('--reviewer-reasoning',required=True);a.add_argument('--parent-task',required=True);a.add_argument('--notes',default='Created by tools/agent_ledger.py.');s.add_parser('validate'); args=p.parse_args(argv)
 try:
  events=read_events(args.ledger)
  if args.cmd=='validate':
   prior=[]
   for e in events: validate(e); lifecycle(prior,e); prior.append(e)
   print(f'valid: {len(events)} events'); return 0
  if args.cmd=='start': event=base(json.loads(args.metadata_file.read_text(encoding='utf-8') if args.metadata_file else args.metadata_json))
  else:
   old=[x for x in events if x['agent_run_id']==args.run_id]; starts=[x for x in old if x['event_type']=='started']
   if len(starts)!=1: raise LedgerError('expected exactly one start')
   seed={k:starts[0][k] for k in ('schema_version','agent_run_id','parent_task','agent_name','requested_model','requested_reasoning','task_type','roadmap_step','scope_summary','constraints','git_commit_before','git_commit_after','ml_ledger_event_ids')}; event={**seed,'event_id':str(uuid.uuid4()),'timestamp_utc':utc(),'notes':args.notes}
   if args.cmd=='terminal':
    commands=json.loads(args.commands_json); files=json.loads(args.files_changed_json)
    if not isinstance(commands,list) or not commands: raise LedgerError('terminal requires actual commands')
    event.update(event_type=args.status,status=args.status,commands=commands,files_changed=files,outcome_summary=args.outcome_summary,supervisor_decision=None,duration_seconds=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(starts[0]['timestamp_utc'].replace('Z','+00:00'))).total_seconds()))
   else: event.update(event_type='reviewed',status='reviewed',commands=[],files_changed=[],outcome_summary=args.outcome_summary,supervisor_decision=args.decision,duration_seconds=None,agent_name=args.reviewer_agent_name,requested_model=args.reviewer_model,requested_reasoning=args.reviewer_reasoning,parent_task=args.parent_task)
  append(args.ledger,event,args.dry_run); print(json.dumps(event,ensure_ascii=False,separators=(',',':'))); return 0
 except (ValueError,LedgerError,OSError) as e: print(f'error: {e}',file=sys.stderr); return 2
if __name__=='__main__': raise SystemExit(main())
