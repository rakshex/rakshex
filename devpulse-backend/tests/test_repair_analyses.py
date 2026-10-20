"""Real database/API tests for consent, tenancy, evidence and bounded intake."""
import copy
import json

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.exc import OperationalError

from models.tables import RepairAnalysis, TeamMember
from services.contract_analysis import analyze_contracts, digest, UnsupportedContract
from services.database import create_user, save_team
from services.db_config import AsyncSessionLocal
from routes.auth import create_token
from middleware import security

BASE = {"openapi": "3.0.3", "paths": {"/payments": {"get": {"responses": {"200": {"description": "ok"}}}}}}


@pytest.fixture(autouse=True)
def reset_throttle():
    security._request_counts.clear()
    yield
    security._request_counts.clear()


@pytest_asyncio.fixture
async def actors(db):
    ids = {name: await create_user(f"repair-{name}@test.test", f"repair-{name}", "x")
           for name in ("owner", "member", "viewer", "pending", "outsider")}
    await save_team("repair-ws", "Repair", ids["owner"])
    async with AsyncSessionLocal() as s:
        for name, role in (("member", "member"), ("viewer", "viewer"), ("pending", "admin")):
            s.add(TeamMember(team_id="repair-ws", user_id=ids[name], role=role, accepted=name != "pending"))
        await s.commit()
    return {name: {"Authorization": f"Bearer {create_token(uid, f'{name}@test.test')}"} for name, uid in ids.items()}


def payload():
    after = copy.deepcopy(BASE)
    after["paths"] = {}
    return {"workspace_id": "repair-ws", "consent": True, "before": copy.deepcopy(BASE), "after": after}


@pytest.mark.asyncio
async def test_authenticated_persistent_analysis_and_readback(client, actors):
    response = await client.post('/api/repair-analyses', json=payload(), headers=actors['member'])
    assert response.status_code == 201, response.text
    record = response.json()['analysis']
    assert record['report']['outcome'] == 'review_required'
    assert record['report']['changes'][0]['kind'] == 'operation_removed'
    assert record['report']['changes'][0]['compatibility'] == 'breaking'
    assert record['evidence_hash'] == digest(record['report'])
    assert record['created_at'].endswith('+00:00')
    assert (await client.get('/api/repair-analyses/'+record['id'], headers=actors['viewer'])).json()['analysis'] == record
    history = await client.get('/api/repair-analyses?workspace_id=repair-ws', headers=actors['viewer'])
    assert history.json()['analyses'][0] == record
    async with AsyncSessionLocal() as session:
        assert (await session.get(RepairAnalysis, record['id'])).evidence_hash == record['evidence_hash']


@pytest.mark.asyncio
@pytest.mark.parametrize('name,status', [('viewer',403),('pending',404),('outsider',404)])
async def test_roles_cannot_submit(client, actors, name, status):
    assert (await client.post('/api/repair-analyses', json=payload(), headers=actors[name])).status_code == status
    async with AsyncSessionLocal() as session:
        assert (await session.execute(select(RepairAnalysis))).scalars().all() == []


@pytest.mark.asyncio
async def test_auth_and_cross_workspace_object_access(client, actors):
    assert (await client.post('/api/repair-analyses', json=payload())).status_code == 401
    record = (await client.post('/api/repair-analyses', json=payload(), headers=actors['owner'])).json()['analysis']
    for name in ('outsider','pending'):
        assert (await client.get('/api/repair-analyses/'+record['id'], headers=actors[name])).status_code == 404
        assert (await client.get('/api/repair-analyses?workspace_id=repair-ws', headers=actors[name])).status_code == 404
        assert (await client.delete('/api/repair-analyses/'+record['id'], headers=actors[name])).status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize('consent', [False, 1, 'true', None])
async def test_explicit_consent_is_required(client, actors, consent):
    data = payload(); data['consent'] = consent
    assert (await client.post('/api/repair-analyses', json=data, headers=actors['owner'])).status_code == 422


@pytest.mark.asyncio
async def test_no_raw_contract_or_secret_retained_or_echoed(client, actors):
    data = payload()
    secret = 'sk_test_synthetic_do_not_use_123456789'
    data['before']['info'] = {'title':secret,'version':'1'}
    data['before']['paths'] = {'/'+secret: {'get': {'description':secret, 'responses':{}}}}
    response = await client.post('/api/repair-analyses', json=data, headers=actors['owner'])
    assert response.status_code == 201
    assert secret not in response.text
    async with AsyncSessionLocal() as session:
        row = (await session.execute(select(RepairAnalysis))).scalar_one()
        assert secret not in json.dumps(row.report)
        assert not hasattr(row,'before')
    data['unexpected'] = secret
    failure = await client.post('/api/repair-analyses', json=data, headers=actors['owner'])
    assert failure.status_code == 422 and secret not in failure.text


@pytest.mark.asyncio
async def test_oversized_actual_body_without_length_is_rejected(client, actors):
    async def body():
        yield b'{' + b' ' * 131072
        yield b' ' * 131073 + b'}'
    response = await client.post('/api/repair-analyses', content=body(), headers=actors['owner'])
    assert response.status_code == 413


@pytest.mark.asyncio
@pytest.mark.parametrize('body', ['{bad', '{"consent":true,"consent":false}', '{"before": NaN}', '['*2000])
async def test_malformed_duplicate_and_deep_json_fail_safely(client, actors, body):
    response = await client.post('/api/repair-analyses', content=body, headers=actors['owner'])
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_external_references_rejected_without_network_access(client, actors, monkeypatch):
    import httpx
    async def forbidden(*args, **kwargs):
        raise AssertionError('Provider egress must not happen')
    monkeypatch.setattr(httpx.AsyncClient,'get',forbidden)
    data = payload(); data['before']['paths']['/payments']['get']['$ref'] = 'http://127.0.0.1/secret'
    response = await client.post('/api/repair-analyses', json=data, headers=actors['owner'])
    assert response.status_code == 422 and '127.0.0.1' not in response.text


@pytest.mark.asyncio
async def test_storage_outage_is_503_and_no_false_success(client, actors, monkeypatch):
    from routes import repair_analyses
    class Broken:
        async def __aenter__(self):
            raise OperationalError('unavailable', {}, Exception())
        async def __aexit__(self,*args):
            pass
    monkeypatch.setattr(repair_analyses,'AsyncSessionLocal',Broken)
    response = await client.post('/api/repair-analyses', json=payload(), headers=actors['owner'])
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_delete_requires_owner_or_admin(client, actors):
    record = (await client.post('/api/repair-analyses', json=payload(), headers=actors['member'])).json()['analysis']
    path = '/api/repair-analyses/'+record['id']
    assert (await client.delete(path, headers=actors['member'])).status_code == 403
    assert (await client.delete(path, headers=actors['owner'])).status_code == 204
    assert (await client.get(path, headers=actors['owner'])).status_code == 404


def test_deterministic_operation_diff_and_documentation_ignored():
    after = copy.deepcopy(BASE)
    after['paths']['/payments']['get']['summary'] = 'docs only'
    assert analyze_contracts(BASE,after)['changes'] == []
    after['paths']['/payments']['get']['responses']['200']['content'] = {'application/json': {'schema':{'type':'string'}}}
    result = analyze_contracts(BASE, after)
    assert result['changes'][0]['kind'] == 'operation_changed'
    assert result == analyze_contracts(BASE, after)
    with pytest.raises(UnsupportedContract): analyze_contracts({},after)


def test_schema_property_named_description_is_not_ignored():
    old = copy.deepcopy(BASE)
    schema = {'type':'object','properties':{'description':{'type':'string'}}}
    old['paths']['/payments']['get']['responses']['200']['content'] = {'application/json':{'schema':schema}}
    new = copy.deepcopy(old)
    new['paths']['/payments']['get']['responses']['200']['content']['application/json']['schema']['properties']['description']['type'] = 'integer'
    assert len(analyze_contracts(old,new)['changes']) == 1
