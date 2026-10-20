"""Authenticated contract-analysis intake; no source, provider or model egress."""
import json
import uuid
from datetime import timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from models.tables import RepairAnalysis, Team, TeamMember
from routes.auth import require_auth
from services.contract_analysis import UnsupportedContract, analyze_contracts, digest
from services.db_config import AsyncSessionLocal

router = APIRouter(prefix="/api/repair-analyses", tags=["Repair analysis"])
MAX_BYTES = 262144


class AnalysisInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    workspace_id: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    consent: Literal[True]
    before: dict[str, Any]
    after: dict[str, Any]


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


async def _input(request: Request) -> AnalysisInput:
    body = bytearray()
    async for chunk in request.stream():
        if len(body) + len(chunk) > MAX_BYTES:
            raise HTTPException(413, "Analysis input exceeds 256 KiB")
        body.extend(chunk)
    try:
        data = json.loads(body, object_pairs_hook=_unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite JSON")))
        if not isinstance(data, dict) or data.get("consent") is not True:
            raise ValueError("Explicit consent required")
        return AnalysisInput.model_validate(data)
    except (ValueError, ValidationError, RecursionError, UnicodeError):
        # Never echo Pydantic's input values (which may contain a pasted credential).
        raise HTTPException(422, "Invalid analysis input; provide workspace, explicit consent and two JSON contracts") from None


async def _access(session, workspace_id: str, user_id: int, write=False, delete=False):
    statement = (select(TeamMember).join(Team, TeamMember.team_id == Team.id)
                 .where(Team.id == workspace_id, TeamMember.user_id == user_id, TeamMember.accepted.is_(True)))
    if write:
        # Same workspace lock as membership changes; authorization cannot go stale before persistence.
        statement = statement.with_for_update(of=Team)
    member = (await session.execute(statement)).scalar_one_or_none()
    if member is None:
        raise HTTPException(404, "Workspace not found")
    allowed = ("owner", "admin") if delete else ("owner", "admin", "member")
    if write and member.role not in allowed:
        raise HTTPException(403, "Workspace role cannot perform this operation")


def _serialize(row):
    return {"id": row.id, "workspace_id": row.workspace_id, "actor_id": row.actor_id,
            "created_at": row.created_at.replace(tzinfo=row.created_at.tzinfo or timezone.utc).isoformat(), "stage": "contract_analysis",
            "report": row.report, "evidence_hash": row.evidence_hash}


@router.post("", status_code=201)
async def create_analysis(request: Request, user: dict = Depends(require_auth)):
    payload = await _input(request)
    try:
        async with AsyncSessionLocal() as session:
            await _access(session, payload.workspace_id, user["id"], write=True)
            try:
                report = analyze_contracts(payload.before, payload.after)
            except (UnsupportedContract, ValueError, RecursionError):
                raise HTTPException(422, "Unsupported or invalid contract; only bounded inline OpenAPI 3 operations are supported") from None
            row = RepairAnalysis(id=str(uuid.uuid4()), workspace_id=payload.workspace_id,
                                 actor_id=user["id"], report=report, evidence_hash=digest(report))
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return {"status": "success", "analysis": _serialize(row)}
    except SQLAlchemyError:
        raise HTTPException(503, "Analysis storage unavailable") from None


@router.get("")
async def list_analyses(workspace_id: str = Query(min_length=1, max_length=64),
                        limit: int = Query(default=20, ge=1, le=100), user: dict = Depends(require_auth)):
    try:
        async with AsyncSessionLocal() as session:
            await _access(session, workspace_id, user["id"])
            rows = (await session.execute(select(RepairAnalysis).where(RepairAnalysis.workspace_id == workspace_id)
                    .order_by(RepairAnalysis.created_at.desc(), RepairAnalysis.id).limit(limit))).scalars().all()
            return {"status": "success", "analyses": [_serialize(row) for row in rows]}
    except SQLAlchemyError:
        raise HTTPException(503, "Analysis storage unavailable") from None


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: uuid.UUID, user: dict = Depends(require_auth)):
    try:
        async with AsyncSessionLocal() as session:
            row = await session.get(RepairAnalysis, str(analysis_id))
            if row is None:
                raise HTTPException(404, "Analysis not found")
            await _access(session, row.workspace_id, user["id"])
            return {"status": "success", "analysis": _serialize(row)}
    except SQLAlchemyError:
        raise HTTPException(503, "Analysis storage unavailable") from None


@router.delete("/{analysis_id}", status_code=204)
async def delete_analysis(analysis_id: uuid.UUID, user: dict = Depends(require_auth)):
    try:
        async with AsyncSessionLocal() as session:
            row = await session.get(RepairAnalysis, str(analysis_id))
            if row is None:
                raise HTTPException(404, "Analysis not found")
            await _access(session, row.workspace_id, user["id"], write=True, delete=True)
            await session.delete(row)
            await session.commit()
    except SQLAlchemyError:
        raise HTTPException(503, "Analysis storage unavailable") from None
