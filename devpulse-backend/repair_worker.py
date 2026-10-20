"""Dedicated worker entry point: python -m repair_worker [--job UUID].

Never start this inside the API container. Provision a disposable worker host and
immutable sandbox image first. No host execution fallback exists.
"""
import argparse
import asyncio
import copy
import os
from sqlalchemy import select
from models.tables import RepairJob
from routes.repair_analyses import _access
from routes.repair_jobs import configured_repository,open_bundle
from services.contract_analysis import digest
from services.db_config import AsyncSessionLocal
from services.repair_engine import plan_repair
from services.repair_sandbox import validate_plan
from services.repair_github import publish_draft
from services.repair_preflight import verify_repair_source, PreflightBlocked


async def process_one(job_id=None):
    async with AsyncSessionLocal() as session:
        stmt=select(RepairJob).where(RepairJob.status.in_(['queued','publication_queued'])).order_by(RepairJob.created_at).with_for_update(skip_locked=True)
        if job_id:stmt=stmt.where(RepairJob.id==job_id)
        row=(await session.execute(stmt.limit(1))).scalar_one_or_none()
        if row is None:return False
        ident=row.id;publication=row.status=='publication_queued'
        try:
            await _access(session,row.workspace_id,row.approved_by if publication else row.actor_id,write=True,delete=publication)
            bundle=await open_bundle(row)
            # Recompute the patch from sealed source/contracts; don't trust stale/tampered plan metadata.
            payload=bundle['input'];plan=plan_repair(payload['before'],payload['after'],payload['files'],payload['rule'])
            if digest(plan)!=digest(bundle['plan']) or plan['patch_hash']!=row.patch_hash:raise ValueError('integrity')
            report=copy.deepcopy(row.report)
            if report.get('before_hash')!=digest(payload['before']) or report.get('after_hash')!=digest(payload['after']):
                raise ValueError('contract binding')
            if publication:
                expected=digest({'patch_hash':row.patch_hash,'report':report})
                if row.approval_hash!=expected:raise ValueError('approval')
            row.status='publishing' if publication else 'validating'
            await session.commit()
        except Exception:
            row.status='rejected';row.report={**row.report,'message':'Authorization or artifact integrity failed; create a new candidate'}
            await session.commit();return True
    # Candidate execution never happens in the API process or in this worker process.
    try:
        if publication:
            async with AsyncSessionLocal() as session:
                row=(await session.execute(select(RepairJob).where(RepairJob.id==ident).with_for_update())).scalar_one()
                await _access(session,row.workspace_id,row.approved_by,write=True,delete=True)
                config=configured_repository(row.workspace_id)
                if not config:raise ValueError('configuration')
                result=await asyncio.wait_for(publish_draft(bundle,report,ident,config),timeout=120)
                row.status='draft_published';row.report={**report,'publication':result,'message':'Draft PR published. Human review and merge required.'}
                await session.commit()
        else:
            # Resolve immutable repository identity before any submitted source is
            # handed to the isolated candidate-validation sandbox. Absence of a
            # GitHub App installation fails closed, never host-executes.
            config=configured_repository(payload['workspace_id'])
            if not config:
                raise PreflightBlocked('Workspace-bound GitHub source verification unavailable')
            preflight=await verify_repair_source(payload,config)
            checks=await asyncio.to_thread(validate_plan,payload['files'],plan,os.environ.get('REPAIR_SANDBOX_IMAGE',''))
            async with AsyncSessionLocal() as session:
                row=(await session.execute(select(RepairJob).where(RepairJob.id==ident).with_for_update())).scalar_one()
                await _access(session,row.workspace_id,row.actor_id,write=True)
                row.status='validated' if checks['accepted'] else 'validation_failed'
                row.report={**report,'source_preflight':preflight,'checks':checks,'message':checks['message']}
                await session.commit()
    except Exception:
        async with AsyncSessionLocal() as session:
            row=await session.get(RepairJob,ident)
            if row:
                row.status='publication_failed' if publication else 'validation_failed'
                row.report={**report,'message':'Worker could not complete this stage. Check configuration, immutable base, permissions and worker health. Raw source/output was not logged.'}
                await session.commit()
    return True


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--job',help='Process one explicitly selected queued job')
    parser.add_argument('--watch',action='store_true',help='Poll the dedicated worker queue until stopped')
    args=parser.parse_args()
    async def main():
        while True:
            worked=await process_one(args.job)
            if not args.watch:break
            if not worked:await asyncio.sleep(3)
    asyncio.run(main())
