"""Protocol tests use a fake GitHub transport; these are not live App evidence."""
import base64
import copy
import hashlib
import json
import time
import pytest
import httpx
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import rsa,padding
from services import repair_github as github
from services.repair_engine import plan_repair
from test_repair_jobs import fixture_input


def test_app_jwt_is_signed_short_lived_and_excludes_source(monkeypatch):
    key=rsa.generate_private_key(public_exponent=65537,key_size=2048)
    pem=key.private_bytes(serialization.Encoding.PEM,serialization.PrivateFormat.PKCS8,serialization.NoEncryption()).decode()
    monkeypatch.setenv('GITHUB_APP_ID','123');monkeypatch.setenv('GITHUB_APP_PRIVATE_KEY',pem)
    token=github.app_jwt();header,payload,signature=token.split('.')
    decoded=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
    assert decoded['iss']=='123' and decoded['exp']-decoded['iat']==540
    assert decoded['exp']>time.time() and decoded['exp']<time.time()+600
    key.public_key().verify(base64.urlsafe_b64decode(signature+'='*(-len(signature)%4)),(header+'.'+payload).encode(),padding.PKCS1v15(),hashes.SHA256())


class FakeGitHub:
    def __init__(self,bundle):self.bundle=bundle;self.writes=[];self.ref=None;self.pr=None;self.moved=False;self.wrong_source=False;self.denied=False
    def handle(self,request):
        path=request.url.path;method=request.method
        body=json.loads(request.content) if request.content else {}
        if self.denied:return httpx.Response(403,json={'message':'synthetic private error'})
        if method=='POST':self.writes.append((path,body))
        if path.startswith('/app/installations/'):
            assert body['repositories']==['rakshex']
            assert body['permissions']=={'contents':'write','pull_requests':'write'}
            result={'token':'installation-only-test-token'}
        elif path=='/repos/rakshex/rakshex':result={'full_name':'rakshex/rakshex','fork':False}
        elif path.endswith('/git/ref/heads/main'):result={'object':{'sha':'c'*40 if self.moved else 'a'*40}}
        elif '/contents/' in path:
            file=path.split('/contents/')[1]
            prefix=self.bundle['input'].get('source_root','')
            if prefix:file=file[len(prefix)+1:]
            source=self.bundle['input']['files'][file]
            if self.wrong_source:source+=' # changed'
            result={'type':'file','encoding':'base64','content':base64.b64encode(source.encode()).decode(),'sha':hashlib.sha256(file.encode()).hexdigest()}
        elif '/git/blobs/' in path:
            sha=path.split('/')[-1];source=next(src for p,src in self.bundle['input']['files'].items() if hashlib.sha256(p.encode()).hexdigest()==sha)
            result={'encoding':'base64','content':base64.b64encode(source.encode()).decode()}
        elif path.endswith('/git/commits/'+'a'*40):result={'tree':{'sha':'d'*40}}
        elif path.endswith('/git/trees'):result={'sha':'e'*40}
        elif path.endswith('/git/commits'):
            assert body['parents']==['a'*40];result={'sha':'b'*40}
        elif '/git/ref/heads/rakshex/repair-' in path:
            if not self.ref:return httpx.Response(404,json={})
            result={'object':{'sha':self.ref}}
        elif path.endswith('/git/refs'):
            assert body['ref']=='refs/heads/rakshex/repair-synthetic';self.ref=body['sha'];result={'ref':body['ref']}
        elif path.endswith('/pulls'):
            if method=='GET':result=[self.pr] if self.pr else []
            else:
                assert body['draft'] is True and body['base']=='main'
                self.pr={'html_url':'https://github.com/rakshex/rakshex/pull/999','number':999,'draft':True,'state':'open'};result=self.pr
        else:raise AssertionError((method,path))
        return httpx.Response(201 if method=='POST' else 200,json=result)


@pytest.fixture
def protocol(monkeypatch):
    data=fixture_input();data['base_branch']='main'
    plan=plan_repair(data['before'],data['after'],data['files'],data['rule'])
    bundle={'input':data,'plan':plan}
    report={'checks':{'accepted':True,'after':{'image':'sha256:'+'1'*64,'tests':1}}}
    fake=FakeGitHub(bundle)
    original=httpx.AsyncClient
    monkeypatch.setattr(github,'app_jwt',lambda:'synthetic-app-token')
    monkeypatch.setattr(github.httpx,'AsyncClient',lambda **kwargs:original(transport=httpx.MockTransport(fake.handle),**kwargs))
    return bundle,report,fake


@pytest.mark.asyncio
async def test_publication_matches_snapshot_pins_parent_and_only_creates_one_draft(protocol):
    bundle,report,fake=protocol
    config={'repository':'rakshex/rakshex','installation_id':123}
    result=await github.publish_draft(bundle,report,'synthetic',config)
    assert result['number']==999
    assert (await github.publish_draft(bundle,report,'synthetic',config))==result
    assert len([p for p,b in fake.writes if p.endswith('/pulls')])==1
    assert len([p for p,b in fake.writes if p.endswith('/git/refs')])==1
    for path,body in fake.writes:
        assert not path.endswith('/merge')
        assert '/deployments' not in path
        if path.endswith('/git/trees'):
            assert [e['path'] for e in body['tree']]==['client.py']
            assert body['tree'][0]['content']==bundle['plan']['edits'][0]['after']


@pytest.mark.asyncio
@pytest.mark.parametrize('kind',['moved','wrong_source','denied','unvalidated','tampered','other_repository'])
async def test_publication_fails_closed_before_branch_or_pr_write(protocol,kind):
    bundle,report,fake=protocol;config={'repository':'rakshex/rakshex','installation_id':123}
    if kind in ('moved','wrong_source','denied'):setattr(fake,kind,True)
    elif kind=='unvalidated':report['checks']['accepted']=False
    elif kind=='tampered':bundle['plan']['diff']+='tamper'
    else:config['repository']='Akshu1245/Rakshex-complete-codebase'
    with pytest.raises(github.PublicationBlocked):await github.publish_draft(bundle,report,'synthetic',config)
    assert not fake.ref and not fake.pr


@pytest.mark.asyncio
async def test_publication_preserves_repository_subdirectory(protocol):
    bundle,report,fake=protocol
    bundle['input']['source_root']='services/orders'
    await github.publish_draft(bundle,report,'synthetic',{'repository':'rakshex/rakshex','installation_id':123})
    tree=next(body for path,body in fake.writes if path.endswith('/git/trees'))
    assert tree['tree'][0]['path']=='services/orders/client.py'
