"""Synthetic-only crypto, tenant isolation, redaction, replay and failure regressions."""
import base64
import copy
import hashlib
import hmac
import json
from pathlib import Path
import time

import pytest
import pytest_asyncio
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select

from models.tables import ApiKey, SecurityScan, CicdRun
from routes.auth import create_token
from services import encryption, storage_crypto, cache, ai_security_engine
from services.database import create_user
from services.db_config import AsyncSessionLocal, engine
from services.security_evidence import redact_scan_evidence
from middleware import security, rate_limit

SYNTHETIC = 'sk-proj-abcdefghijklmnopqrstuvwxyz1234567890AABBCCDD'
LEGACY = json.loads((Path(__file__).parent/'fixtures/legacy_synthetic_credential.json').read_text())


@pytest.fixture(autouse=True)
def isolate_test_security_state(monkeypatch):
    security._request_counts.clear();rate_limit._mem_store.clear();cache._fallback.clear()
    monkeypatch.setattr(encryption,'_MASTER_KEY_ENV',base64.b64encode(b'S'*32).decode())
    yield
    security._request_counts.clear();rate_limit._mem_store.clear();cache._fallback.clear()


@pytest_asyncio.fixture
async def accounts(db):
    result = {}
    for name in ('owner','outsider'):
        uid = await create_user(name+'@secure.test','secure-'+name,'synthetic-no-login')
        result[name]={'id':uid,'headers':{'Authorization':'Bearer '+create_token(uid,name+'@secure.test')}}
    return result


@pytest.mark.asyncio
async def test_independent_standard_aesgcm_interoperability_and_randomness():
    first = await storage_crypto.encrypt_for_storage(SYNTHETIC)
    second = await storage_crypto.encrypt_for_storage(SYNTHETIC)
    assert first.startswith('v2:') and first != second
    raw=base64.b64decode(first[3:])
    assert AESGCM(hashlib.sha256(b'S'*32).digest()).decrypt(raw[:12],raw[12:],storage_crypto.AAD).decode()==SYNTHETIC
    assert await storage_crypto.decrypt_from_storage(first)==SYNTHETIC
    with pytest.raises(RuntimeError): encryption.encrypt_aes256(SYNTHETIC)


@pytest.mark.asyncio
async def test_original_legacy_fixture_is_read_without_mutation():
    original = copy.deepcopy(LEGACY)
    assert await storage_crypto.decrypt_from_storage(LEGACY['ciphertext'])==LEGACY['plaintext']
    candidate = await storage_crypto.upgrade_ciphertext(LEGACY['ciphertext'])
    assert candidate.startswith('v2:')
    assert await storage_crypto.decrypt_from_storage(candidate)==LEGACY['plaintext']
    assert await storage_crypto.upgrade_ciphertext(candidate)==candidate
    assert LEGACY==original


@pytest.mark.asyncio
@pytest.mark.parametrize('value',['','v3:AAA','v2:AA==','v2:!!!','not base64'])
async def test_malformed_and_unknown_ciphertexts_are_rejected(value):
    with pytest.raises(ValueError): await storage_crypto.decrypt_from_storage(value)


@pytest.mark.asyncio
async def test_tamper_and_wrong_key_fail_closed(monkeypatch):
    value = await storage_crypto.encrypt_for_storage(SYNTHETIC)
    raw=bytearray(base64.b64decode(value[3:]));raw[-1]^=1
    with pytest.raises(ValueError): await storage_crypto.decrypt_from_storage('v2:'+base64.b64encode(raw).decode())
    monkeypatch.setattr(encryption,'_MASTER_KEY_ENV',base64.b64encode(b'T'*32).decode())
    with pytest.raises(ValueError): await storage_crypto.decrypt_from_storage(value)
    with pytest.raises(ValueError): await storage_crypto.decrypt_from_storage(LEGACY['ciphertext'])


@pytest.mark.asyncio
@pytest.mark.parametrize('configured',['', 'too-short',base64.b64encode(b'A'*16).decode(),base64.b64encode(b'A'*48).decode()])
async def test_production_writes_require_dedicated_canonical_master(monkeypatch,configured):
    monkeypatch.setenv('ENV','production');monkeypatch.setattr(encryption,'_MASTER_KEY_ENV',configured)
    with pytest.raises(ValueError): await storage_crypto.encrypt_for_storage(SYNTHETIC)


@pytest.mark.asyncio
async def test_key_creation_and_lists_never_disclose_ciphertext(client,accounts):
    owner=accounts['owner']['headers']; outsider=accounts['outsider']['headers']
    response=await client.post('/api/keys',headers=owner,json={'key_name':'Synthetic','api_provider':'openai','api_key':SYNTHETIC,'budget_period':'weekly'})
    assert response.status_code==201,response.text
    key_id=response.json()['key']['id']
    async with AsyncSessionLocal() as session:
        row=await session.get(ApiKey,key_id)
        cipher=row.encrypted_key
        assert cipher.startswith('v2:') and row.budget_period=='weekly'
        assert await storage_crypto.decrypt_from_storage(cipher)==SYNTHETIC
    for path in ('/api/keys','/api/budget'):
        r=await client.get(path,headers=owner)
        assert r.status_code==200 and 'encrypted_key' not in r.text and SYNTHETIC not in r.text and cipher not in r.text
    assert (await client.get('/api/keys',headers=outsider)).json()['keys']==[]
    await client.put('/api/keys/'+str(key_id),headers=outsider,json={'is_active':False})
    async with AsyncSessionLocal() as session:
        assert (await session.get(ApiKey,key_id)).is_active is True
    assert (await client.put('/api/keys/'+str(key_id),headers=owner,json={'is_active':False})).json()['status']=='success'
    async with AsyncSessionLocal() as session:
        assert (await session.get(ApiKey,key_id)).is_active is False


@pytest.mark.asyncio
async def test_bad_credential_configuration_returns_no_false_success(client,accounts,monkeypatch):
    monkeypatch.setattr(encryption,'_MASTER_KEY_ENV','bad configuration')
    r=await client.post('/api/keys',headers=accounts['owner']['headers'],json={'key_name':'Synthetic','api_provider':'openai','api_key':SYNTHETIC})
    assert r.status_code==503 and SYNTHETIC not in r.text
    async with AsyncSessionLocal() as session:
        assert (await session.execute(select(ApiKey))).scalars().all()==[]


@pytest.mark.asyncio
async def test_validation_does_not_reflect_secret_input(client,accounts):
    r=await client.post('/api/keys',headers=accounts['owner']['headers'],json={'key_name':'Synthetic','api_provider':'openai','api_key':SYNTHETIC*20})
    assert r.status_code==422 and SYNTHETIC not in r.text


@pytest.mark.asyncio
@pytest.mark.parametrize('path',['/api/security/scan/code','/api/security/scan/api','/api/cicd/check','/api/cicd/webhook'])
async def test_legacy_mutations_require_authentication(client,path):
    payload={'code':'print(1)','url':'https://example.test','event':'test'}
    assert (await client.post(path,json=payload)).status_code==401


@pytest.mark.asyncio
@pytest.mark.parametrize('path',['/api/security/scans','/api/cicd/runs','/api/cicd/badge/default'])
async def test_legacy_history_and_badges_require_authentication(client,path):
    assert (await client.get(path)).status_code==401


@pytest.mark.asyncio
async def test_real_legacy_scan_persists_redacted_account_isolated_history(client,accounts):
    headers=accounts['owner']['headers']
    r=await client.post('/api/security/scan/code',headers=headers,json={'code':'api_key="'+SYNTHETIC+'"'})
    assert r.status_code==200 and r.json()['status']=='success',r.text
    assert SYNTHETIC not in r.text
    rows=(await client.get('/api/security/scans',headers=headers)).json()['scans']
    assert len(rows)==1 and rows[0]['id']==r.json()['scan_id']
    assert SYNTHETIC not in json.dumps(rows)
    assert (await client.get('/api/security/scans',headers=accounts['outsider']['headers'])).json()['scans']==[]
    async with AsyncSessionLocal() as session:
        row=await session.get(SecurityScan,r.json()['scan_id'])
        assert row.user_id==accounts['owner']['id'] and SYNTHETIC not in json.dumps(row.results_json)


@pytest.mark.asyncio
async def test_configuration_scan_does_not_retain_credentials_in_url_or_headers(client,accounts):
    r=await client.post('/api/security/scan/api',headers=accounts['owner']['headers'],json={'url':'https://example.test?api_key='+SYNTHETIC,'headers':{'Authorization':'Bearer '+SYNTHETIC}})
    assert r.status_code==200 and SYNTHETIC not in r.text
    async with AsyncSessionLocal() as session:
        row=await session.get(SecurityScan,r.json()['scan_id'])
        assert SYNTHETIC not in row.target+json.dumps(row.results_json)


@pytest.mark.asyncio
async def test_cicd_records_only_observed_checks_and_isolates_history(client,accounts):
    r=await client.post('/api/cicd/check',headers=accounts['owner']['headers'],json={'code':'api_key="'+SYNTHETIC+'"','pipeline_id':'shared-name'})
    assert r.status_code==200 and r.json()['status']=='success',r.text
    assert r.json()['budget_status']=='not_run' and r.json()['compatibility_status']=='not_run'
    assert SYNTHETIC not in r.text
    async with AsyncSessionLocal() as session:
        row=await session.get(CicdRun,r.json()['run_id'])
        assert row.budget_ok is None and row.compatibility_score is None
        assert SYNTHETIC not in json.dumps(row.details_json)
    assert len((await client.get('/api/cicd/runs',headers=accounts['owner']['headers'])).json()['runs'])==1
    assert (await client.get('/api/cicd/runs',headers=accounts['outsider']['headers'])).json()['runs']==[]
    badge=await client.get('/api/cicd/badge/shared-name',headers=accounts['outsider']['headers'])
    assert badge.status_code==200 and 'N/A' in badge.text


@pytest.mark.asyncio
async def test_forged_expired_and_replayed_webhooks_are_denied(client,accounts,monkeypatch):
    secret='S'*48;monkeypatch.setenv('CICD_WEBHOOK_SECRET',secret)
    body=json.dumps({'event':'synthetic','code':'print(1)'},separators=(',',':'))
    stamp=str(int(time.time()))
    headers={**accounts['owner']['headers'],'Content-Type':'application/json','X-Rakshex-Timestamp':stamp,'X-Rakshex-Signature':'sha256='+'0'*64}
    assert (await client.post('/api/cicd/webhook',headers=headers,content=body)).status_code==403
    headers['X-Rakshex-Signature']='sha256='+hmac.new(secret.encode(),stamp.encode()+b'.'+body.encode(),hashlib.sha256).hexdigest()
    assert (await client.post('/api/cicd/webhook',headers=headers,content=body)).status_code==200
    assert (await client.post('/api/cicd/webhook',headers=headers,content=body)).status_code==409
    headers['X-Rakshex-Timestamp']=str(int(stamp)-600)
    assert (await client.post('/api/cicd/webhook',headers=headers,content=body)).status_code==403


@pytest.mark.asyncio
async def test_unconfigured_webhook_is_unavailable_not_success(client,accounts,monkeypatch):
    monkeypatch.delenv('CICD_WEBHOOK_SECRET',raising=False)
    assert (await client.post('/api/cicd/webhook',headers=accounts['owner']['headers'],json={'event':'test'})).status_code==503


def test_redaction_copies_nested_and_historical_json():
    data={'findings':[{'matched_text':SYNTHETIC,'snippet':SYNTHETIC,'nested':{'Authorization':SYNTHETIC},'rule_id':'static'}]}
    original=copy.deepcopy(data)
    result=redact_scan_evidence(json.dumps(data))
    assert SYNTHETIC not in json.dumps(result) and data==original
    assert result['findings'][0]['rule_id']=='static'
    assert engine.sync_engine.hide_parameters is True


@pytest.mark.asyncio
async def test_model_processing_is_opt_in_and_canonical_metadata_only(monkeypatch):
    import httpx
    calls=[]
    class FakeClient:
        async def __aenter__(self):return self
        async def __aexit__(self,*args):pass
        async def post(self,*args,**kwargs):
            calls.append(kwargs['json'])
            return httpx.Response(200,json={'choices':[{'message':{'content':'[]'}}]})
    monkeypatch.setattr(ai_security_engine,'GROQ_API_KEY','synthetic-only-key')
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kwargs:FakeClient())
    rule=ai_security_engine.TOKEN_PATTERNS[0]['id']
    findings=[{'rule_id':rule,'description':SYNTHETIC,'matched_text':SYNTHETIC,'severity':'critical','line':1}]
    await ai_security_engine.generate_fix_suggestions(findings,SYNTHETIC)
    assert calls==[]
    await ai_security_engine.generate_fix_suggestions(findings,SYNTHETIC,allow_model=True)
    assert len(calls)==1 and SYNTHETIC not in json.dumps(calls)


@pytest.mark.asyncio
async def test_email_unconfigured_is_not_reported_as_delivered(monkeypatch):
    from services import email_service
    monkeypatch.setattr(email_service,'SENDGRID_API_KEY','')
    assert email_service._send('synthetic@test.test','Synthetic','Synthetic') is False

@pytest.mark.asyncio
async def test_cached_evidence_is_redacted_and_not_shared_between_accounts(client, accounts, monkeypatch):
    from routes import ai_security
    calls=[]
    async def old_cache(key):
        calls.append(key)
        return {'score':20,'grade':'F','total_threats':1,
                'all_findings':[{'severity':'high','matched_text':SYNTHETIC,'snippet':SYNTHETIC}]}
    monkeypatch.setattr(ai_security,'cache_get',old_cache)
    for who in ('owner','outsider'):
        response=await client.post('/api/v1/security/scan/full',headers=accounts[who]['headers'],
                                   json={'code':'synthetic source','language':'python'})
        assert response.status_code==200
        assert response.json()['cached'] is True
        assert SYNTHETIC not in response.text
    assert calls[0]!=calls[1]


@pytest.mark.asyncio
async def test_historical_scan_reads_redact_without_rewriting_evidence(db, accounts):
    from services.database import get_security_scans
    original={'vulnerabilities':[{'matched_text':SYNTHETIC,'snippet':SYNTHETIC}]}
    async with AsyncSessionLocal() as session:
        record=SecurityScan(user_id=accounts['owner']['id'],scan_type='code',target='historical',
                            language='python',score=20,grade='F',total_issues=1,results_json=original)
        session.add(record)
        await session.commit()
        record_id=record.id
    visible=await get_security_scans(accounts['owner']['id'])
    assert SYNTHETIC not in json.dumps(visible)
    async with AsyncSessionLocal() as session:
        stored=await session.get(SecurityScan,record_id)
        assert stored.results_json==original  # retention cleanup requires a separate reviewed migration
