"""GitHub preflight must fail closed before source validation."""
import base64
import hashlib
import json
import httpx
import pytest
from services import repair_preflight

SHA='a'*40
TREE='b'*40
BLOB='c'*40
SOURCE=b'print(123)\\n'
PAYLOAD={'repository':'rakshex/rakshex','base_branch':'development','base_sha':SHA,
         'source_root':'','files':{'client.py':SOURCE.decode()}}
CONFIG={'repository':'rakshex/rakshex','installation_id':42}

@pytest.mark.asyncio
async def test_immutable_source_preflight(monkeypatch):
    monkeypatch.setattr(repair_preflight,'app_jwt',lambda:'signed')
    seen=[]
    def respond(request):
        p=request.url.path
        seen.append((request.method,p))
        if p.endswith('/access_tokens'):
            assert json.loads(request.content)['permissions']=={'contents':'read'}
            return httpx.Response(201,json={'token':'installation-token'})
        if p=='/repos/rakshex/rakshex':return httpx.Response(200,json={'full_name':'rakshex/rakshex','fork':False})
        if '/git/ref/heads/' in p:return httpx.Response(200,json={'object':{'sha':SHA}})
        if '/git/commits/' in p:return httpx.Response(200,json={'tree':{'sha':TREE}})
        if '/git/trees/' in p:return httpx.Response(200,json={'tree':[{'path':'client.py','sha':BLOB,'mode':'100644','type':'blob'}]})
        if '/git/blobs/' in p:return httpx.Response(200,json={'encoding':'base64','content':base64.b64encode(SOURCE).decode()})
        raise AssertionError(p)
    result=await repair_preflight.verify_repair_source(PAYLOAD,CONFIG,transport=httpx.MockTransport(respond))
    assert result['status']=='verified_at_preflight'
    assert result['file_count']==1
    assert result['verified_files'][0]['content_hash']==hashlib.sha256(SOURCE).hexdigest()
    assert all(method=='GET' for method,path in seen[1:])

@pytest.mark.asyncio
@pytest.mark.parametrize('field,value',[('repository','../escape'),('base_sha','synthetic'),
 ('source_root','../other'),('files',{'../secret.py':'x'})])
async def test_invalid_input_no_egress(field,value):
    payload={**PAYLOAD,field:value}
    def unexpected(request):raise AssertionError('unexpected egress')
    with pytest.raises(repair_preflight.PreflightBlocked):
        await repair_preflight.verify_repair_source(payload,CONFIG,transport=httpx.MockTransport(unexpected))

@pytest.mark.asyncio
async def test_moved_commit_refused(monkeypatch):
    monkeypatch.setattr(repair_preflight,'app_jwt',lambda:'signed')
    def respond(request):
        p=request.url.path
        if p.endswith('/access_tokens'):return httpx.Response(201,json={'token':'x'})
        if p=='/repos/rakshex/rakshex':return httpx.Response(200,json={'full_name':'rakshex/rakshex'})
        return httpx.Response(200,json={'object':{'sha':'d'*40}})
    with pytest.raises(repair_preflight.PreflightBlocked,match='branch moved'):
        await repair_preflight.verify_repair_source(PAYLOAD,CONFIG,transport=httpx.MockTransport(respond))
