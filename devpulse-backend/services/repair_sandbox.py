"""No fallback to host execution. Requires dedicated Docker worker, never the API.

No Docker socket is mounted into the candidate. Worker host must itself be isolated
from production; Docker is a restriction layer, not a claim of VM-grade isolation.
"""
import hashlib
import os
from pathlib import Path
import re
import selectors
import subprocess
import tempfile
import time
import uuid
from services.repair_engine import safe_files

OUTPUT_LIMIT=131072
TIME_LIMIT=30


def sandbox_command(directory,image,name):
    if not re.fullmatch(r'(?:[a-zA-Z0-9./:_-]+@)?sha256:[a-f0-9]{64}',image or ''):
        raise ValueError('An immutable pre-provisioned sandbox image is required')
    return ['docker','run','--pull=never','--name',name,'--rm','--network=none','--read-only',
            '--user=65532:65532','--cap-drop=ALL','--security-opt=no-new-privileges',
            '--pids-limit=64','--memory=256m','--memory-swap=256m','--cpus=1',
            '--ulimit=nofile=128:128','--ulimit=fsize=1048576:1048576',
            '--tmpfs=/tmp:rw,noexec,nosuid,size=16m',
            '--mount',f'type=bind,src={directory},dst=/work,readonly',image]


def run_snapshot(files,image):
    files=safe_files(files)
    name='rakshex-check-'+uuid.uuid4().hex
    env={'PATH':os.defpath,'HOME':'/nonexistent','LANG':'C.UTF-8'}
    output=bytearray();reason='completed';exit_code=None
    with tempfile.TemporaryDirectory(prefix='rakshex-candidate-') as directory:
        os.chmod(directory,0o755)
        for path,source in files.items():
            dest=Path(directory)/path;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_text(source);dest.chmod(0o444)
        command=sandbox_command(directory,image,name)
        process=None
        try:
            process=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=env)
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout,selectors.EVENT_READ)
                deadline=time.monotonic()+TIME_LIMIT
                while selector.get_map():
                    if time.monotonic()>deadline:
                        reason='timeout';break
                    for key,_ in selector.select(timeout=0.1):
                        chunk=os.read(key.fileobj.fileno(),8192)
                        if not chunk:selector.unregister(key.fileobj);continue
                        if len(output)+len(chunk)>OUTPUT_LIMIT:
                            reason='output_limit';break
                        output.extend(chunk)
                    if reason!='completed':break
                if reason=='completed':exit_code=process.wait(timeout=3)
        except (FileNotFoundError,OSError,subprocess.SubprocessError):reason='runner_unavailable'
        finally:
            if process:
                if process.poll() is None:process.kill()
                process.wait(timeout=5)
                process.stdout.close()
            try:subprocess.run(['docker','rm','-f',name],env=env,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=5)
            except (OSError,subprocess.SubprocessError):pass
    text=output.decode('utf-8',errors='replace')
    match=re.search(r'Ran (\d+) tests? in ',text)
    count=int(match.group(1)) if match else 0
    return {'status':'passed' if reason=='completed' and exit_code==0 and count>0 else 'failed',
            'exit_code':exit_code,'tests':count,'reason':reason,'output_hash':hashlib.sha256(output).hexdigest(),
            'image':image,'network':'none','source_mounted':'read_only'}


def validate_plan(files,plan,image):
    before=run_snapshot(files,image)
    after_files={**files,**{edit['file']:edit['after'] for edit in plan['edits']}}
    after=run_snapshot(after_files,image)
    # No green-on-green patches, skipped checks, empty collection, timeout or infra errors.
    baseline_failed=(before['reason']=='completed' and before['exit_code']==1 and before['tests']>0)
    accepted=baseline_failed and after['status']=='passed' and before['tests']==after['tests']
    return {'accepted':accepted,'before':before,'after':after,
            'message':'Failing baseline and passing candidate observed' if accepted else 'Validation rejected: require a failing baseline and passing candidate with equal nonzero test counts'}
