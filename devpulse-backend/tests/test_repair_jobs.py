"""Real planning, encrypted persistence, ownership, worker and publication gates."""
import copy
import json
import os
from pathlib import Path
import base64
import pytest
import pytest_asyncio
from models.tables import RepairJob
from services.db_config import AsyncSessionLocal
from services.repair_engine import plan_repair,RepairRefused,safe_files
from services.repair_sandbox import sandbox_command
from services import encryption,cache
from middleware import security,rate_limit

FIXTURE=Path(__file__).resolve().parents[2]/'repair-fixtures/python-json-rename'


def fixture_input():
    data=json.loads((FIXTURE/'contracts.json').read_text())
    data['files']={p.relative_to(FIXTURE).as_posix():p.read_text() for p in FIXTURE.rglob('*.py')}
    data.update(repository='rakshex/rakshex',base_branch='codex/rakshex-foundation-20261020',base_sha='a'*40)
    return data


@pytest.fixture(autouse=True)
def isolated(monkeypatch):
    security._request_counts.clear();rate_limit._mem_store.clear();cache._fallback.clear()
    monkeypatch.setattr(encryption,'_MASTER_KEY_ENV',base64.b64encode(b'J'*32).decode())
    yield
    security._request_counts.clear();rate_limit._mem_store.clear();cache._fallback.clear()


@pytest_asyncio.fixture
async def owner(client,auth_headers):
    result=await client.post('/api/teams/workspaces',headers=auth_headers,json={'name':'Repair tests'})
    assert result.status_code==200
    return auth_headers,result.json()['id']


def test_plan_is_a_real_bounded_diff_and_preserves_tests():
    data=fixture_input();snapshot=copy.deepcopy(data)
    plan=plan_repair(data['before'],data['after'],data['files'],data['rule'])
    assert len(plan['impacts'])==1
    assert plan['edits'][0]['file']=='client.py'
    assert "'customer_id': customer" in plan['edits'][0]['after']
    assert '-    return requests.post' in plan['diff']
    assert data==snapshot
    assert plan==plan_repair(data['before'],data['after'],data['files'],data['rule'])


@pytest.mark.parametrize('source',[
 "import requests\nrequests.post(url,json={'customer_ref':'x'})\n",
 "import requests\nrequests.post('https://api.example.com/v1/orders',json=payload)\n",
 "import requests\nrequests.post('https://api.example.com/v1/orders',json={**payload,'customer_ref':'x'})\n",
 "import requests\nrequests=object()\nrequests.post('https://api.example.com/v1/orders',json={'customer_ref':'x'})\n",
 "import requests\ndef f(requests):\n return requests.post('https://api.example.com/v1/orders',json={'customer_ref':'x'})\n",
 "import requests\nrequests.post('https://api.example.com/v1/orders',json={'customer_ref':'x','customer_id':'y'})\n",
])
def test_ambiguous_source_refused(source):
    data=fixture_input();data['files']['client.py']=source
    with pytest.raises(RepairRefused):plan_repair(data['before'],data['after'],data['files'],data['rule'])


def test_unicode_byte_offsets_and_alias_import():
    data=fixture_input();data['files']['client.py']="from requests import post as send\nname='é'; send('https://api.example.com/v1/orders',json={'customer_ref': name})\n"
    plan=plan_repair(data['before'],data['after'],data['files'],data['rule'])
    assert "name='é'; send" in plan['edits'][0]['after']
    assert "'customer_id': name" in plan['edits'][0]['after']


@pytest.mark.parametrize('path',['../client.py','/client.py','x/../client.py','.env','x//client.py','x\\client.py','tests/.hidden.py'])
def test_path_escape_refused(path):
    with pytest.raises(RepairRefused):safe_files({path:'pass'})


def test_schema_semantics_change_is_not_repaired():
    data=fixture_input();data['after']['paths']['/v1/orders']['post']['requestBody']['content']['application/json']['schema']['properties']['customer_id']['type']='integer'
    with pytest.raises(RepairRefused):plan_repair(data['before'],data['after'],data['files'],data['rule'])


def test_sandbox_command_is_pinned_restricted_and_not_a_shell():
    cmd=sandbox_command('/tmp/work','sha256:'+'a'*64,'synthetic')
    for flag in ('--network=none','--read-only','--user=65532:65532','--cap-drop=ALL','--security-opt=no-new-privileges','--pids-limit=64','--memory=256m','--pull=never'):assert flag in cmd
    assert 'type=bind,src=/tmp/work,dst=/work,readonly' in cmd
    assert not any('docker.sock' in x for x in cmd)
    with pytest.raises(ValueError):sandbox_command('/tmp/work','python:latest','synthetic')


@pytest.mark.asyncio
async def test_job_persists_encrypted_and_artifact_is_authorized(client,owner):
    headers,ws=owner;data=fixture_input();data.update(workspace_id=ws,consent=True)
    response=await client.post('/api/repair-jobs',headers=headers,json=data)
    assert response.status_code==201,response.text
    job=response.json()['job'];assert job['status']=='queued'
    assert 'synthetic-customer' not in response.text
    async with AsyncSessionLocal() as session:
        row=await session.get(RepairJob,job['id'])
        assert row.sealed_bundle.startswith('v2:')
        assert 'requests.post' not in row.sealed_bundle
    artifact=await client.get(f"/api/repair-jobs/{job['id']}/artifact",headers=headers)
    assert artifact.status_code==200 and "'customer_id'" in artifact.json()['diff']
    assert (await client.get(f"/api/repair-jobs/{job['id']}/artifact")).status_code==401
    other=await client.post('/api/auth/register',json={'email':'other-repair@test.test','username':'other-repair','password':'TestPass123!'})
    outsider={'Authorization':'Bearer '+other.json()['token']}
    assert (await client.get(f"/api/repair-jobs/{job['id']}/artifact",headers=outsider)).status_code==404
    assert (await client.delete(f"/api/repair-jobs/{job['id']}",headers=outsider)).status_code==404
    assert (await client.post('/api/repair-jobs',headers=headers,json=data)).status_code==409
    assert (await client.post(f"/api/repair-jobs/{job['id']}/publish",headers=headers,json={'consent':True,'evidence_hash':job['evidence_hash']})).status_code==409
    assert (await client.delete(f"/api/repair-jobs/{job['id']}",headers=headers)).status_code==204


@pytest.mark.asyncio
async def test_missing_consent_and_oversized_body_rejected_without_echo(client,owner):
    headers,ws=owner;data=fixture_input();data.update(workspace_id=ws,consent=False)
    response=await client.post('/api/repair-jobs',headers=headers,json=data)
    assert response.status_code==422 and 'requests.post' not in response.text
    assert (await client.post('/api/repair-jobs',headers=headers,content='x'*786433)).status_code==413


@pytest.mark.asyncio
async def test_worker_never_falls_back_to_host_execution(client,owner,monkeypatch):
    from repair_worker import process_one
    headers,ws=owner;data=fixture_input();data.update(workspace_id=ws,consent=True)
    job=(await client.post('/api/repair-jobs',headers=headers,json=data)).json()['job']
    monkeypatch.delenv('REPAIR_SANDBOX_IMAGE',raising=False)
    assert await process_one(job['id'])
    result=(await client.get('/api/repair-jobs',headers=headers,params={'workspace_id':ws})).json()['jobs'][0]
    assert result['status']=='validation_failed'
    assert not result['report']['checks'].get('accepted')


@pytest.mark.skipif(not os.getenv('REPAIR_SANDBOX_IMAGE'),reason='Dedicated Docker integration job required')
@pytest.mark.asyncio
async def test_real_isolated_worker_baseline_fails_candidate_passes(client,owner):
    from repair_worker import process_one
    headers,ws=owner;data=fixture_input();data.update(workspace_id=ws,consent=True)
    job=(await client.post('/api/repair-jobs',headers=headers,json=data)).json()['job']
    assert await process_one(job['id'])
    result=(await client.get('/api/repair-jobs',headers=headers,params={'workspace_id':ws})).json()['jobs'][0]
    assert result['status']=='validated',result
    assert result['report']['checks']['before']['exit_code']==1
    assert result['report']['checks']['after']['status']=='passed'
    assert result['report']['checks']['after']['tests']==1
    assert (await client.post(f"/api/repair-jobs/{job['id']}/publish",headers=headers,json={'consent':True,'evidence_hash':'b'*64})).status_code==409
    assert (await client.post(f"/api/repair-jobs/{job['id']}/publish",headers=headers,json={'consent':True,'evidence_hash':result['evidence_hash']})).status_code==503


@pytest.mark.skipif(not os.getenv('REPAIR_SANDBOX_IMAGE'),reason='Dedicated Docker integration job required')
def test_real_sandbox_no_credentials_network_or_write_access(monkeypatch):
    from services.repair_sandbox import run_snapshot
    monkeypatch.setenv('REPAIR_WORKER_SENTINEL','not-for-candidate')
    files={'client.py':'# read only source\n','tests/test_isolation.py':'''import os, socket, unittest
class Isolation(unittest.TestCase):
 def test_boundaries(self):
  self.assertEqual(os.getuid(),65532)
  self.assertNotIn('REPAIR_WORKER_SENTINEL',os.environ)
  self.assertNotIn('JWT_SECRET',os.environ)
  with self.assertRaises(OSError): open('/work/client.py','w')
  with self.assertRaises(OSError): open('/root-write-proof','w')
  sock=socket.socket();sock.settimeout(1)
  try:
   with self.assertRaises(OSError): sock.connect(('1.1.1.1',443))
  finally: sock.close()
'''}
    result=run_snapshot(files,os.environ['REPAIR_SANDBOX_IMAGE'])
    assert result['status']=='passed',result


@pytest.mark.skipif(not os.getenv('REPAIR_SANDBOX_IMAGE'),reason='Dedicated Docker integration job required')
def test_real_sandbox_times_out_and_caps_output(monkeypatch):
    from services import repair_sandbox
    monkeypatch.setattr(repair_sandbox,'TIME_LIMIT',2)
    result=repair_sandbox.run_snapshot({'tests/test_loop.py':'while True: pass\n'},os.environ['REPAIR_SANDBOX_IMAGE'])
    assert result['reason']=='timeout',result
    monkeypatch.setattr(repair_sandbox,'TIME_LIMIT',10)
    result=repair_sandbox.run_snapshot({'tests/test_output.py':"while True: print('x'*1000,flush=True)\n"},os.environ['REPAIR_SANDBOX_IMAGE'])
    assert result['reason']=='output_limit',result


@pytest.mark.skipif(not os.getenv('REPAIR_SANDBOX_IMAGE'),reason='Dedicated Docker integration job required')
def test_real_sandbox_rejects_bad_patch_and_green_baseline():
    from services.repair_sandbox import validate_plan
    data=fixture_input();plan=plan_repair(data['before'],data['after'],data['files'],data['rule'])
    bad=copy.deepcopy(plan);bad['edits'][0]['after']=data['files']['client.py']
    assert not validate_plan(data['files'],bad,os.environ['REPAIR_SANDBOX_IMAGE'])['accepted']
    green={**data['files'],'client.py':plan['edits'][0]['after']}
    assert not validate_plan(green,plan,os.environ['REPAIR_SANDBOX_IMAGE'])['accepted']


def test_no_final_newline_diff_is_applyable(tmp_path):
    import subprocess
    data=fixture_input();data['files']['client.py']=data['files']['client.py'].rstrip('\n')
    plan=plan_repair(data['before'],data['after'],data['files'],data['rule'])
    # Preserve exact bytes on Windows: text-mode subprocess stdin can translate
    # LF into CRLF, invalidating an otherwise well-formed unified diff.
    (tmp_path/'client.py').write_bytes(data['files']['client.py'].encode('utf-8'))
    patch_bytes=plan['diff'].encode('utf-8')
    subprocess.run(['git','apply','--check','-'],input=patch_bytes,cwd=tmp_path,check=True,capture_output=True)
    subprocess.run(['git','apply','-'],input=patch_bytes,cwd=tmp_path,check=True,capture_output=True)
    assert (tmp_path/'client.py').read_bytes()==plan['edits'][0]['after'].encode('utf-8')


@pytest.mark.asyncio
async def test_worker_rechecks_revoked_membership_before_execution(client,owner):
    from repair_worker import process_one
    from models.tables import TeamMember
    from sqlalchemy import select
    headers,ws=owner;data=fixture_input();data.update(workspace_id=ws,consent=True)
    job=(await client.post('/api/repair-jobs',headers=headers,json=data)).json()['job']
    async with AsyncSessionLocal() as session:
        member=(await session.execute(select(TeamMember).where(TeamMember.team_id==ws))).scalar_one()
        member.accepted=False;await session.commit()
    assert await process_one(job['id'])
    async with AsyncSessionLocal() as session:
        row=await session.get(RepairJob,job['id'])
        assert row.status=='rejected'
        assert not row.report['checks']


@pytest.mark.asyncio
async def test_concurrent_submission_has_one_active_job(client,owner):
    import asyncio
    from sqlalchemy import select,func
    headers,ws=owner;data=fixture_input();data.update(workspace_id=ws,consent=True)
    responses=await asyncio.gather(*(client.post('/api/repair-jobs',headers=headers,json=data) for _ in range(2)))
    assert sorted(response.status_code for response in responses)==[201,409]
    async with AsyncSessionLocal() as session:
        assert await session.scalar(select(func.count()).select_from(RepairJob).where(RepairJob.workspace_id==ws))==1


@pytest.mark.parametrize('change',['body_required','content_type','path_parameter','path_server'])
def test_other_body_or_path_semantics_refuse_rename(change):
    data=fixture_input();path=data['after']['paths']['/v1/orders'];body=path['post']['requestBody']
    if change=='body_required':body['required']=True
    elif change=='content_type':body['content']['text/plain']={'schema':{'type':'string'}}
    elif change=='path_parameter':path['parameters']=[{'name':'tenant','in':'query','required':True,'schema':{'type':'string'}}]
    else:path['servers']=[{'url':'https://different.example.com'}]
    with pytest.raises(RepairRefused):plan_repair(data['before'],data['after'],data['files'],data['rule'])
