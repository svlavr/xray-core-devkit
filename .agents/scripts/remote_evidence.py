"""Read one exact remote ref; never substitute local HEAD for a failed query."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess

import workspace


def now():return datetime.now(timezone.utc).isoformat()


def observe(remote,ref,expected=None,runner=subprocess.run):
    if (not isinstance(remote,str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*',remote)
            or not isinstance(ref,str) or not re.fullmatch(r'refs/heads/[A-Za-z0-9_./-]+',ref)
            or '..' in ref or any(not p or p.startswith('.') or p.endswith(('.', '.lock')) for p in ref.split('/'))):
        raise ValueError('Use a configured remote name and an exact refs/heads/... ref')
    if expected is not None and not re.fullmatch(r'[0-9a-f]{40}',expected):
        raise ValueError('Expected identity must be a full commit SHA')
    result={'remote':remote,'url':None,'ref':ref,'query_started_at':now(),
            'status':'UNAVAILABLE','sha':None,'expected_sha':expected,'matches_expected':None}
    args=[workspace.git_executable(),'-c','gc.auto=0','-c','maintenance.auto=false',
          '-C',str(workspace.ROOT),'ls-remote','--exit-code','--refs',remote,ref]
    try:
        result['url']=workspace.git('remote','get-url',remote)
        query=runner(args,capture_output=True,text=True,encoding='utf-8',
                     timeout=35,creationflags=workspace.FLAGS)
        result['exit_code']=query.returncode
        result['stdout_sha256']=hashlib.sha256(query.stdout.encode('utf-8')).hexdigest()
        if query.returncode:
            result['error']=(query.stderr or 'Remote ref lookup failed').strip()
        else:
            rows=[line.split() for line in query.stdout.splitlines()]
            if len(rows)!=1 or len(rows[0])!=2 or rows[0][1]!=ref or not re.fullmatch(r'[0-9a-f]{40}',rows[0][0]):
                result['error']='Remote output does not identify exactly the requested ref'
            else:
                result.update(status='LIVE',sha=rows[0][0],observed_at=now(),
                              matches_expected=rows[0][0]==expected if expected else None)
    except (OSError,RuntimeError,subprocess.SubprocessError) as error:
        result['error']=str(error)
    result['query_finished_at']=now()
    return result


def reuse(prior,source):
    """Keep the original observation time and identity when citing older evidence."""
    if (prior.get('status') not in ('LIVE','REUSED') or not prior.get('observed_at')
            or not prior.get('ref') or not prior.get('url') or not source
            or not re.fullmatch(r'[0-9a-f]{40}',prior.get('sha',''))):
        raise ValueError('Reused evidence needs a successful observation, original time and source')
    return {**prior,'status':'REUSED','reused_at':now(),'evidence_source':source}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--remote',required=True)
    parser.add_argument('--ref',required=True)
    parser.add_argument('--expected')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    workspace.repository_guard()
    output=args.output.absolute()
    if not output.resolve().is_relative_to((workspace.ROOT/'.local').resolve()) or output.exists():
        raise ValueError('Use a new ignored .local receipt path; never overwrite historical evidence')
    result=observe(args.remote,args.ref,args.expected)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8',newline='\n') as handle:
        json.dump(result,handle,indent=2);handle.write('\n')
    print(json.dumps(result))
    return 0 if result['status']=='LIVE' and result['matches_expected'] is not False else 1


if __name__=='__main__':raise SystemExit(main())
