"""Read-only GitHub source preflight BEFORE untrusted repair validation.

This verifies a repository snapshot, not permission for arbitrary scanning or
trusted provenance of an API provider's claimed contract changes.
"""
import base64
import hashlib
import re
from urllib.parse import quote
import httpx
from services.repair_github import app_jwt

class PreflightBlocked(ValueError):
    pass

async def verify_repair_source(payload, config, *, transport=None):
    repo=payload.get('repository','')
    branch=payload.get('base_branch','')
    sha=payload.get('base_sha','')
    files=payload.get('files')
    root=payload.get('source_root','')
    if (not isinstance(repo,str) or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',repo)
        or any(p in ('.','..') or p.startswith('.') for p in repo.split('/'))
        or not isinstance(config,dict) or config.get('repository')!=repo
        or type(config.get('installation_id')) is not int
        or not isinstance(sha,str) or not re.fullmatch(r'[a-f0-9]{40}',sha)
        or not isinstance(branch,str) or not re.fullmatch(r'[A-Za-z0-9_/-]{1,100}',branch)
        or branch.startswith('/') or '..' in branch.split('/')
        or not isinstance(root,str) or (root and not re.fullmatch(r'[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*',root))
        or not isinstance(files,dict) or not 1<=len(files)<=40):
        raise PreflightBlocked('Unverified repository binding or invalid source scope')
    for path,source in files.items():
        if not isinstance(path,str) or not re.fullmatch(r'(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+\\.py',path) or not isinstance(source,str):
            raise PreflightBlocked('Invalid source scope')
    async with httpx.AsyncClient(base_url='https://api.github.com',timeout=15,follow_redirects=False,transport=transport) as client:
        async def request(method,path,token,**kwargs):
            response=await client.request(method,path,headers={
                'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json',
                'X-GitHub-Api-Version':'2022-11-28'},**kwargs)
            if response.status_code not in (200,201):
                raise PreflightBlocked('GitHub source verification unavailable')
            try:return response.json()
            except ValueError as exc:raise PreflightBlocked('Malformed GitHub verification response') from exc
        access=await request('POST',f"/app/installations/{config['installation_id']}/access_tokens",app_jwt(),
                             json={'repositories':[repo.split('/')[1]],'permissions':{'contents':'read'}})
        token=access.get('token')
        if not isinstance(token,str) or not token:raise PreflightBlocked('Missing GitHub installation token')
        prefix='/repos/'+repo
        metadata=await request('GET',prefix,token)
        if metadata.get('full_name','').lower()!=repo.lower() or metadata.get('fork'):
            raise PreflightBlocked('Repository identity mismatch')
        head=await request('GET',prefix+'/git/ref/heads/'+quote(branch,safe=''),token)
        if head.get('object',{}).get('sha')!=sha:
            raise PreflightBlocked('Immutable base branch moved')
        commit=await request('GET',prefix+'/git/commits/'+sha,token)
        tree_sha=commit.get('tree',{}).get('sha')
        if not isinstance(tree_sha,str) or not re.fullmatch(r'[a-f0-9]{40}',tree_sha):
            raise PreflightBlocked('Missing immutable source tree')
        trees={}
        checked=[]
        for relative,source in sorted(files.items()):
            path=root+'/'+relative if root else relative
            node=tree_sha
            for i,part in enumerate(path.split('/')):
                if node not in trees:trees[node]=await request('GET',prefix+'/git/trees/'+node,token)
                tree=trees[node]
                if tree.get('truncated'):raise PreflightBlocked('Incomplete source tree')
                entries=[entry for entry in tree.get('tree',[]) if entry.get('path')==part]
                if len(entries)!=1:raise PreflightBlocked('Source path not found')
                entry=entries[0]
                if i==len(path.split('/'))-1:
                    if entry.get('mode')!='100644' or entry.get('type')!='blob':
                        raise PreflightBlocked('Nonregular source file refused')
                    blob_sha=entry.get('sha')
                else:
                    if entry.get('mode')!='040000' or entry.get('type')!='tree':
                        raise PreflightBlocked('Link/submodule traversal refused')
                    node=entry.get('sha')
            blob=await request('GET',prefix+'/git/blobs/'+blob_sha,token)
            if blob.get('encoding')!='base64':raise PreflightBlocked('Unsupported blob encoding')
            try: actual=base64.b64decode(blob['content'],validate=True)
            except (ValueError,KeyError) as exc:raise PreflightBlocked('Malformed blob content') from exc
            if actual!=source.encode('utf-8'):raise PreflightBlocked('Source differs from immutable commit')
            checked.append({'path_hash':hashlib.sha256(path.encode()).hexdigest(),
                            'content_hash':hashlib.sha256(actual).hexdigest()})
        return {'repository':repo,'base_sha':sha,'file_count':len(checked),
                'verified_files':checked,'status':'verified_at_preflight'}
