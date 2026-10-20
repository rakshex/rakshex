"""Consented repair planning. Execution/publication happens only in a separate worker."""
import json
import os
import uuid
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query,Request
from pydantic import BaseModel,ConfigDict,Field,ValidationError,field_validator
from sqlalchemy import select,func
from sqlalchemy.exc import SQLAlchemyError,IntegrityError
from models.tables import RepairJob
from routes.auth import require_auth
from routes.repair_analyses import _access,_unique_object
from services.contract_analysis import digest
from services.repair_engine import plan_repair,RepairRefused
from services.storage_crypto import encrypt_for_storage,decrypt_from_storage

router=APIRouter(prefix='/api/repair-jobs',tags=['Self-Repair'])


class Rule(BaseModel):
    model_config=ConfigDict(extra='forbid')
    method: Literal['POST','PUT','PATCH']
    path: str=Field(min_length=1,max_length=200)
    origin: str=Field(min_length=1,max_length=200)
    removed: str=Field(min_length=1,max_length=64)
    added: str=Field(min_length=1,max_length=64)
    provenance: str=Field(min_length=1,max_length=500)


class JobInput(BaseModel):
    model_config=ConfigDict(extra='forbid')
    workspace_id: str=Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    consent: Literal[True]
    repository: str=Field(pattern=r'^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$',max_length=150)
    source_root: str=Field(default='',pattern=r'^(?:[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*)?$',max_length=150)
    base_branch: str=Field(pattern=r'^[A-Za-z0-9_/-]{1,100}$')
    base_sha: str=Field(pattern=r'^[a-f0-9]{40}$')
    before: dict
    after: dict
    files: dict[str,str]
    rule: Rule


class Approval(BaseModel):
    model_config=ConfigDict(extra='forbid')
    @field_validator('consent',mode='before')
    @classmethod
    def explicit_consent(cls,value):
        if value is not True:raise ValueError('Explicit consent required')
        return value
    evidence_hash: str=Field(pattern=r'^[a-f0-9]{64}$')
    consent: Literal[True]


def configured_repository(workspace):
    try:
        config=json.loads(os.getenv('REPAIR_REPOSITORIES','{}')).get(workspace)
        if not isinstance(config,dict) or set(config)!= {'repository','installation_id'} or not isinstance(config['installation_id'],int):return None
        return config
    except (ValueError,TypeError):return None


def serialize(row):
    return {'id':row.id,'workspace_id':row.workspace_id,'status':row.status,'patch_hash':row.patch_hash,
            'report':row.report,'evidence_hash':digest({'patch_hash':row.patch_hash,'report':row.report}),
            'created_at':row.created_at.isoformat()}


async def open_bundle(row):
    bundle=json.loads(await decrypt_from_storage(row.sealed_bundle))
    if bundle.get('job_id')!=row.id or bundle.get('workspace_id')!=row.workspace_id or bundle.get('plan',{}).get('patch_hash')!=row.patch_hash:
        raise ValueError('Repair bundle identity mismatch')
    return bundle


async def read_input(request):
    data=bytearray()
    async for chunk in request.stream():
        if len(data)+len(chunk)>786432:raise HTTPException(413,'Repair input exceeds 768 KiB')
        data.extend(chunk)
    try:
        obj=json.loads(data,object_pairs_hook=_unique_object,parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
        if obj.get('consent') is not True:raise ValueError()
        return JobInput.model_validate(obj)
    except (ValueError,TypeError,AttributeError,RecursionError,UnicodeError,ValidationError):
        raise HTTPException(422,'Invalid repair input; explicit source processing consent is required') from None


from services.db_config import AsyncSessionLocal


@router.post('',status_code=201)
async def create_job(request:Request,user=Depends(require_auth)):
    payload=await read_input(request)
    try:
        async with AsyncSessionLocal() as session:
            await _access(session,payload.workspace_id,user['id'],write=True)
            active=await session.scalar(select(func.count()).select_from(RepairJob).where(RepairJob.workspace_id==payload.workspace_id,RepairJob.status.in_(['queued','validating','publication_queued','publishing'])))
            if active:raise HTTPException(409,'A repair is already active in this workspace')
            try:plan=plan_repair(payload.before,payload.after,payload.files,payload.rule.model_dump())
            except (ValueError,RecursionError):raise HTTPException(422,'Repair refused: use a single confirmed JSON property rename, static Python requests calls and scoped Python tests') from None
            if not any(p.startswith('tests/test_') for p in payload.files):raise HTTPException(422,'Include existing tests/test_*.py regression tests')
            job_id=str(uuid.uuid4())
            bundle={'job_id':job_id,'workspace_id':payload.workspace_id,'input':payload.model_dump(),'plan':plan}
            try:sealed=await encrypt_for_storage(json.dumps(bundle,ensure_ascii=True))
            except ValueError:raise HTTPException(503,'Repair artifact encryption is not configured') from None
            report={'adapter':plan['adapter'],'impacts':plan['impacts'],'scope':plan['scope'],
                    'repository':payload.repository,'source_root':payload.source_root,'base_branch':payload.base_branch,'base_sha':payload.base_sha,
                    'source_hash':plan['source_hash'],'before_hash':digest(payload.before),'after_hash':digest(payload.after),
                    'migration':{key:getattr(payload.rule,key) for key in ('removed','added','provenance')},'checks':{},'limitations':plan['limitations'],
                    'message':'Patch planned. Awaiting an isolated validation worker.'}
            row=RepairJob(id=job_id,workspace_id=payload.workspace_id,actor_id=user['id'],status='queued',sealed_bundle=sealed,patch_hash=plan['patch_hash'],report=report)
            session.add(row);await session.commit();await session.refresh(row)
            return {'job':serialize(row)}
    except IntegrityError:raise HTTPException(409,'Another repair became active; refresh and retry') from None
    except SQLAlchemyError:raise HTTPException(503,'Repair storage unavailable') from None


@router.get('')
async def list_jobs(workspace_id:str=Query(min_length=1,max_length=64),user=Depends(require_auth)):
    async with AsyncSessionLocal() as session:
        await _access(session,workspace_id,user['id'])
        rows=(await session.execute(select(RepairJob).where(RepairJob.workspace_id==workspace_id).order_by(RepairJob.created_at.desc()).limit(20))).scalars()
        return {'jobs':[serialize(row) for row in rows],
                'publication_configured':bool(configured_repository(workspace_id) and os.getenv('GITHUB_APP_ID') and os.getenv('GITHUB_APP_PRIVATE_KEY'))}


async def authorized_job(session,job_id,user,write=False,admin=False):
    row=(await session.execute(select(RepairJob).where(RepairJob.id==str(job_id)).with_for_update())).scalar_one_or_none()
    if row is None:raise HTTPException(404,'Repair not found')
    await _access(session,row.workspace_id,user['id'],write=write,delete=admin)
    return row


@router.get('/{job_id}/artifact')
async def artifact(job_id:uuid.UUID,user=Depends(require_auth)):
    async with AsyncSessionLocal() as session:
        row=await authorized_job(session,job_id,user)
        try:bundle=await open_bundle(row)
        except (ValueError,KeyError):raise HTTPException(503,'Repair artifact unavailable') from None
        return {'diff':bundle['plan']['diff'],'patch_hash':row.patch_hash}


@router.post('/{job_id}/publish',status_code=202)
async def approve_publication(job_id:uuid.UUID,payload:Approval,user=Depends(require_auth)):
    async with AsyncSessionLocal() as session:
        row=await authorized_job(session,job_id,user,write=True,admin=True)
        if row.status!='validated':raise HTTPException(409,'Only a validated candidate can be approved')
        if serialize(row)['evidence_hash']!=payload.evidence_hash:raise HTTPException(409,'Evidence changed; review again')
        config=configured_repository(row.workspace_id)
        if not config or config['repository']!=row.report['repository'] or not os.getenv('GITHUB_APP_ID') or not os.getenv('GITHUB_APP_PRIVATE_KEY'):
            raise HTTPException(503,'A workspace-bound GitHub App installation must be configured')
        row.approved_by=user['id'];row.approval_hash=payload.evidence_hash;row.status='publication_queued'
        try:await session.commit()
        except IntegrityError:raise HTTPException(409,'Another repair is active; wait and review evidence again') from None
        return {'job':serialize(row)}


@router.delete('/{job_id}',status_code=204)
async def delete_job(job_id:uuid.UUID,user=Depends(require_auth)):
    async with AsyncSessionLocal() as session:
        row=await authorized_job(session,job_id,user,write=True,admin=True)
        if row.status in ('validating','publishing','publication_queued'):raise HTTPException(409,'Wait for the active worker to finish before deleting evidence')
        await session.delete(row);await session.commit()
