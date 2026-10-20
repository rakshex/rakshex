"""Authenticated, account-isolated legacy static security checks.

No external URL is fetched. Results are heuristics, not security certification.
"""
import hashlib
import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from routes.auth import require_auth
from services.security_scanner import scan_code, scan_api_config
from services.security_evidence import redact_scan_evidence
from services.database import save_security_scan, get_security_scans

logger = logging.getLogger(__name__)
router = APIRouter()


class CodeScanRequest(BaseModel):
    code: str = Field(min_length=1, max_length=50000)
    language: str = Field(default='python', max_length=20)


class ApiScanRequest(BaseModel):
    url: str = Field(min_length=5, max_length=500)
    headers: Dict[str, str] = Field(default_factory=dict, max_length=100)


@router.post('/api/security/scan/code')
async def scan_code_endpoint(req: CodeScanRequest, user=Depends(require_auth)) -> Dict[str, Any]:
    try:
        result = redact_scan_evidence(scan_code(req.code, req.language))
        scan_id = await save_security_scan(user_id=user['id'], scan_type='code', target='submitted source',
            language=req.language, score=result['score'], grade=result['grade'],
            total_issues=result['total_issues'], results_json=result)
        return {**result, 'status':'success', 'scan_id':scan_id, 'scope':'static_heuristics'}
    except SQLAlchemyError:
        raise HTTPException(503, 'Scan could not be saved') from None
    except Exception as exc:
        logger.error('Code scan failed (%s)',type(exc).__name__)
        raise HTTPException(500, 'Code scan failed') from None


@router.post('/api/security/scan/api')
async def scan_api_endpoint(req: ApiScanRequest, user=Depends(require_auth)) -> Dict[str, Any]:
    try:
        result = redact_scan_evidence(scan_api_config(req.url,req.headers))
        # Endpoint credentials/query strings never become retained evidence.
        result['scanned_url'] = '[REDACTED]'
        scan_id = await save_security_scan(user_id=user['id'], scan_type='api',
            target='endpoint#'+hashlib.sha256(req.url.encode()).hexdigest(),language='configuration',
            score=result['score'],grade='review',total_issues=len(result['issues']),results_json=result)
        return {**result,'status':'success','scan_id':scan_id,'scope':'configuration_heuristics'}
    except SQLAlchemyError:
        raise HTTPException(503, 'Scan could not be saved') from None
    except Exception as exc:
        logger.error('Configuration scan failed (%s)',type(exc).__name__)
        raise HTTPException(500, 'Configuration scan failed') from None


@router.get('/api/security/scans')
async def list_scans(limit: int = Query(20,ge=1,le=100), user=Depends(require_auth)) -> Dict[str,Any]:
    try:
        scans = await get_security_scans(user_id=user['id'],limit=limit)
        return {'status':'success','scans':scans,'count':len(scans)}
    except SQLAlchemyError:
        raise HTTPException(503, 'Scan history unavailable') from None
