"""Least-privilege GitHub App draft PR publisher. No merge/deploy API exists here."""
import base64
import hashlib
import json
import os
import re
import time
from urllib.parse import quote
import httpx
from cryptography.hazmat.primitives import hashes,serialization
from cryptography.hazmat.primitives.asymmetric import padding


class PublicationBlocked(ValueError):pass


def _b64(value):return base64.urlsafe_b64encode(value).rstrip(b'=').decode()


def app_jwt():
    app_id=os.environ.get('GITHUB_APP_ID','')
    if not app_id.isdigit():raise PublicationBlocked('GitHub App configuration required')
    try:key=serialization.load_pem_private_key(os.environ['GITHUB_APP_PRIVATE_KEY'].encode(),password=None)
    except (KeyError,ValueError,TypeError):raise PublicationBlocked('GitHub App configuration required') from None
    now=int(time.time())
    body=_b64(b'{"alg":"RS256","typ":"JWT"}')+'.'+_b64(json.dumps({'iat':now-60,'exp':now+480,'iss':app_id},separators=(',',':')).encode())
    return body+'.'+_b64(key.sign(body.encode(),padding.PKCS1v15(),hashes.SHA256()))


async def publish_draft(bundle,report,job_id,config):
    payload=bundle['input'];plan=bundle['plan'];repo=payload['repository'];base=payload['base_sha']
    if config['repository']!=repo or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo):
        raise PublicationBlocked('Workspace repository binding mismatch')
    if not report.get('checks',{}).get('accepted'):raise PublicationBlocked('Successful validation evidence is required')
    if hashlib.sha256(plan['diff'].encode()).hexdigest()!=plan['patch_hash']:raise PublicationBlocked('Patch integrity mismatch')
    async with httpx.AsyncClient(base_url='https://api.github.com',timeout=20,follow_redirects=False) as client:
        async def request(method,path,token,**kwargs):
            response=await client.request(method,path,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'},**kwargs)
            if response.status_code not in (200,201):raise PublicationBlocked('GitHub rejected the operation; retry after reviewing installation, branch and permissions')
            return response.json()
        signed=app_jwt()
        # Narrow the installation token to this one server-bound repository and required permissions.
        access=await request('POST',f"/app/installations/{config['installation_id']}/access_tokens",signed,
                             json={'repositories':[repo.split('/')[1]],'permissions':{'contents':'write','pull_requests':'write'}})
        token=access['token']
        root=f'/repos/{repo}'
        metadata=await request('GET',root,token)
        if metadata.get('full_name','').lower()!=repo.lower() or metadata.get('fork'):
            raise PublicationBlocked('Repository identity must match the workspace binding; forks require a separate reviewed installation')
        branch=quote(payload['base_branch'],safe='')
        head=await request('GET',root+'/git/ref/heads/'+branch,token)
        if head['object']['sha']!=base:raise PublicationBlocked('Base branch moved; create and validate a new candidate')
        # Submitted tests/source must exactly match the selected immutable repository commit.
        prefix=payload.get('source_root','').strip('/')
        def repo_path(path):return prefix+'/'+path if prefix else path
        for path,source in payload['files'].items():
            original=await request('GET',root+'/contents/'+quote(repo_path(path),safe='/')+'?ref='+base,token)
            if original.get('type')!='file' or original.get('encoding')!='base64':raise PublicationBlocked('Only regular repository files are supported')
            if base64.b64decode(original['content']).decode()!=source:raise PublicationBlocked('Submitted snapshot does not match the immutable base commit')
            blob=await request('GET',root+'/git/blobs/'+original['sha'],token)
            if blob.get('encoding')!='base64' or base64.b64decode(blob['content']).decode()!=source:raise PublicationBlocked('Repository source mismatch')
        commit=await request('GET',root+'/git/commits/'+base,token)
        tree=await request('POST',root+'/git/trees',token,json={'base_tree':commit['tree']['sha'],
            'tree':[{'path':repo_path(e['file']),'mode':'100644','type':'blob','content':e['after']} for e in plan['edits']]})
        created=await request('POST',root+'/git/commits',token,json={'message':f'fix: reviewed request property migration ({job_id})','tree':tree['sha'],'parents':[base]})
        repair_branch='rakshex/repair-'+job_id
        # One deterministic branch per job. Never overwrite a pre-existing branch or force push.
        existing=await client.get(root+'/git/ref/heads/'+repair_branch,headers={'Authorization':'Bearer '+token})
        if existing.status_code==404:
            await request('POST',root+'/git/refs',token,json={'ref':'refs/heads/'+repair_branch,'sha':created['sha']})
        elif existing.status_code!=200:raise PublicationBlocked('Could not inspect repair branch')
        elif existing.json()['object']['sha']!=created['sha']:
            # Commit timestamps can differ on retry. Compare the full tree and parent instead.
            prior=await request('GET',root+'/git/commits/'+existing.json()['object']['sha'],token)
            if prior['tree']['sha']!=tree['sha'] or [p['sha'] for p in prior['parents']]!=[base]:raise PublicationBlocked('Repair branch already differs; manual review required')
        prs=await request('GET',root+'/pulls?state=all&head='+quote(repo.split('/')[0]+':'+repair_branch,safe='')+'&base='+branch,token)
        if prs:
            if len(prs)!=1 or not prs[0].get('draft') or prs[0].get('state')!='open':raise PublicationBlocked('Existing repair PR needs manual review')
            return {'url':prs[0]['html_url'],'number':prs[0]['number'],'branch':repair_branch}
        # Recheck base immediately before publication; no stale claim of tested HEAD.
        head=await request('GET',root+'/git/ref/heads/'+branch,token)
        if head['object']['sha']!=base:raise PublicationBlocked('Base moved before publication; review the orphan repair branch')
        body=(f"RaksHex deterministic Python requests key rename. Human review and merge required.\n\n"
              f"Base: `{base}`\nPatch SHA-256: `{plan['patch_hash']}`\n"
              f"Validation: failing baseline / passing candidate; network-disabled immutable image `{report['checks']['after']['image']}`.\n"
              f"Tests: {report['checks']['after']['tests']}. Only submitted paths were tested. No provider connectivity or full-repository compatibility claim.\n"
              f"Migration reference: {payload['rule']['provenance']}\n\nNo model-generated code, dependency installation, merge or deployment performed.")
        pr=await request('POST',root+'/pulls',token,json={'title':'fix: migrate reviewed API request property','head':repair_branch,'base':payload['base_branch'],'body':body,'draft':True})
        return {'url':pr['html_url'],'number':pr['number'],'branch':repair_branch}
