"""Rehearse repair migration in temporary SQLite; never uses caller DATABASE_URL."""
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

backend = Path(__file__).resolve().parents[1] / 'devpulse-backend'
with tempfile.TemporaryDirectory(prefix='rakshex-migration-') as directory:
    database = Path(directory) / 'rehearsal.db'
    env = {**os.environ, 'ENV': 'test', 'DATABASE_URL': 'sqlite+aiosqlite:///' + str(database)}
    def migrate(*args):
        result = subprocess.run([sys.executable, '-m', 'alembic', *args], cwd=backend,
                                env=env, capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise RuntimeError('Migration rehearsal failed: ' + result.stderr)
    migrate('upgrade', 'head')
    with sqlite3.connect(database) as connection:
        connection.execute("INSERT INTO users (id,email,username,password_hash) VALUES (1,'migration@test.test','migration','synthetic')")
        assert {row[1] for row in connection.execute('PRAGMA table_info(repair_analyses)')} == {
            'id','workspace_id','actor_id','report','evidence_hash','created_at'}
        assert connection.execute('PRAGMA foreign_key_list(repair_analyses)').fetchall()
        assert connection.execute('PRAGMA foreign_key_list(repair_jobs)').fetchall()
        assert any(row[1]=='uq_repair_jobs_active_workspace' and row[2]==1 for row in connection.execute('PRAGMA index_list(repair_jobs)'))
    migrate('downgrade', '002_onboarding_progress')
    with sqlite3.connect(database) as connection:
        assert not connection.execute("SELECT name FROM sqlite_master WHERE name='repair_analyses'").fetchall()
        assert connection.execute('SELECT username FROM users WHERE id=1').fetchone() == ('migration',)
    migrate('upgrade', 'head')
    with sqlite3.connect(database) as connection:
        assert connection.execute('SELECT version_num FROM alembic_version').fetchone() == ('20261020_active_repair',)
        assert connection.execute('SELECT username FROM users WHERE id=1').fetchone() == ('migration',)
    print('PASS: isolated upgrade/downgrade/upgrade; schema, foreign keys and parent data preserved')
