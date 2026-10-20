"""Optional PostgreSQL row-lock proof in a unique disposable schema, never drop shared tables."""
import asyncio
import os
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from models.tables import Base
import services.database as database

URL = os.getenv('TEST_PG_URL')
pytestmark = pytest.mark.skipif(not URL, reason='TEST_PG_URL not configured; PostgreSQL locking not verified locally')


@pytest.mark.asyncio
async def test_actor_role_rechecked_after_workspace_row_lock(monkeypatch):
    schema = 'test_team_' + uuid.uuid4().hex
    control = create_async_engine(URL)
    engine = None
    owner = None
    task = None
    try:
        async with control.begin() as connection:
            await connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_async_engine(URL, connect_args={'server_settings':{'search_path':schema}})
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
            for uid, name in ((1,'owner'),(2,'admin'),(3,'member')):
                await connection.execute(text('INSERT INTO users (id,email,username,password_hash) VALUES (:id,:email,:name,\'x\')'),
                                         {'id':uid,'email':name+'@test.test','name':name})
            await connection.execute(text("INSERT INTO teams (id,name,owner_id) VALUES ('ws','Test',1)"))
            for uid, role in ((1,'owner'),(2,'admin'),(3,'member')):
                await connection.execute(text("INSERT INTO team_members (team_id,user_id,role,accepted) VALUES ('ws',:uid,:role,true)"),{'uid':uid,'role':role})
        monkeypatch.setattr(database,'AsyncSessionLocal',async_sessionmaker(engine,expire_on_commit=False))
        owner = await engine.connect()
        transaction = await owner.begin()
        await owner.execute(text("SELECT id FROM teams WHERE id='ws' FOR UPDATE"))
        await owner.execute(text("UPDATE team_members SET role='viewer' WHERE team_id='ws' AND user_id=2"))
        task = asyncio.create_task(database.apply_team_member_change('ws',2,3,'remove'))
        await asyncio.sleep(0.3)
        assert not task.done(), 'Membership mutation must wait for the workspace lock'
        await transaction.commit()
        assert (await asyncio.wait_for(task,10))[0] == 'forbidden'
        async with engine.connect() as connection:
            assert (await connection.execute(text("SELECT count(*) FROM team_members WHERE team_id='ws' AND user_id=3"))).scalar() == 1
    finally:
        if task and not task.done():
            task.cancel()
            try: await task
            except asyncio.CancelledError: pass
        if owner:
            await owner.close()
        if engine:
            await engine.dispose()
        async with control.begin() as connection:
            await connection.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        await control.dispose()
