"""Authenticated static CI security checks and signed, replay-conflict webhooks.

These do not execute a repository, check budgets, or claim isolated repair tests.
"""
import hashlib
import hmac
import logging
import os
import re
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from routes.auth import require_auth
from services.database import save_cicd_run, get_cicd_runs_db
from services.security_evidence import redact_scan_evidence
from services.security_scanner import scan_code

router = APIRouter()
logger = logging.getLogger(__name__)
BADGE_TEMPLATE = '<svg xmlns="http://www.w3.org/2000/svg" width="120" height="20"><rect width="120" height="20" fill="{color}"/><text x="60" y="14" text-anchor="middle" fill="white">RaksHex: {label}</text></svg>'


class CICDCheckRequest(BaseModel):
    code: str = Field(min_length=1,max_length=50000)
    language: str = Field(default='python',max_length=20)
    pipeline_id: str = Field(default='default',max_length=100)
    repo: str = Field(default='unknown',max_length=200)
    branch: str = Field(default='main',max_length=100)
    min_score: int = Field(default=70,ge=0,le=100)


class WebhookPayload(BaseModel):
    event: str = Field(max_length=50)
    pipeline_id: str = Field(default='default',max_length=100)
    repo: str = Field(default='unknown',max_length=200)
    branch: str = Field(default='main',max_length=100)
    commit_sha: str = Field(default='',max_length=50)
    code: Optional[str] = Field(default=None,max_length=50000)
    language: str = Field(default='python',max_length=20)


async def _persist(run_id, pipeline_id, repo, branch, status, score, details, user):
    await save_cicd_run(run_id=run_id,pipeline_id=pipeline_id,repo=repo,branch=branch,
        gate_result=status,security_score=score,compatibility_score=None,budget_ok=None,
        details=redact_scan_evidence(details),triggered_by=f"user:{user['id']}")


@router.post('/api/cicd/check')
async def cicd_check(req: CICDCheckRequest, user=Depends(require_auth)):
    result = redact_scan_evidence(scan_code(req.code,req.language))
    passed = result['score'] >= req.min_score
    run_id = 'run-'+uuid.uuid4().hex
    try:
        await _persist(run_id,req.pipeline_id,req.repo,req.branch,'pass' if passed else 'fail',result['score'],result,user)
    except SQLAlchemyError:
        raise HTTPException(503,'CI check could not be saved') from None
    return {'status':'success','run_id':run_id,'passed':passed,'security_score':result['score'],
            'grade':result['grade'],'vulnerabilities_found':result['total_issues'],
            'threshold':req.min_score,'verdict':'PASS' if passed else 'FAIL','details':result['vulnerabilities'],
            'scope':'static_security_rules','compatibility_status':'not_run','budget_status':'not_run'}


@router.post('/api/cicd/webhook')
async def cicd_webhook(request: Request, payload: WebhookPayload, user=Depends(require_auth)):
    secret = os.getenv('CICD_WEBHOOK_SECRET','')
    if len(secret) < 32:
        raise HTTPException(503,'CI webhook signing is not configured')
    stamp = request.headers.get('x-rakshex-timestamp','')
    signature = request.headers.get('x-rakshex-signature','')
    try:
        if abs(time.time()-int(stamp)) > 300:
            raise ValueError()
    except ValueError:
        raise HTTPException(403,'Invalid or expired webhook signature') from None
    raw = await request.body()
    expected = 'sha256='+hmac.new(secret.encode(),stamp.encode()+b'.'+raw,hashlib.sha256).hexdigest()
    if not re.fullmatch(r'sha256=[0-9a-f]{64}',signature) or not hmac.compare_digest(signature,expected):
        raise HTTPException(403,'Invalid or expired webhook signature')
    run_id = 'hook-'+hashlib.sha256(str(user['id']).encode()+b'.'+stamp.encode()+b'.'+raw).hexdigest()[:40]
    result = redact_scan_evidence(scan_code(payload.code,payload.language)) if payload.code else {}
    status = ('pass' if result['score']>=70 else 'fail') if result else 'received'
    try:
        await _persist(run_id,payload.pipeline_id,payload.repo,payload.branch,status,result.get('score'),result,user)
    except IntegrityError:
        raise HTTPException(409,'This signed event has already been recorded') from None
    except SQLAlchemyError:
        raise HTTPException(503,'CI event could not be saved') from None
    return {'status':'success','run_id':run_id,'event_status':status,'scope':'authenticated_ci_event'}


@router.get('/api/cicd/runs')
async def list_runs(limit: int=Query(20,ge=1,le=100),pipeline_id: Optional[str]=Query(None,max_length=100),user=Depends(require_auth)):
    try:
        runs = await get_cicd_runs_db(limit=limit,pipeline_id=pipeline_id,actor_id=user['id'])
        return {'status':'success','runs':runs,'count':len(runs)}
    except SQLAlchemyError:
        raise HTTPException(503,'CI history unavailable') from None


@router.get('/api/cicd/badge/{pipeline_id}')
async def status_badge(pipeline_id: str, user=Depends(require_auth)):
    try:
        runs = await get_cicd_runs_db(limit=1,pipeline_id=pipeline_id,actor_id=user['id'])
    except SQLAlchemyError:
        raise HTTPException(503,'CI badge unavailable') from None
    status = runs[0]['status'] if runs else 'unknown'
    label,color = {'pass':('PASS','#22863a'),'fail':('FAIL','#b31d28'),'received':('RECEIVED','#555')}.get(status,('N/A','#555'))
    return Response(BADGE_TEMPLATE.format(color=color,label=label),media_type='image/svg+xml')
