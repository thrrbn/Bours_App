"""
Tests de `analysis_lab/job_repository.py` (Phase 3, 31/07/2026 - voir
db_models.py::TrainingJob). Meme convention que test_portfolio_costs.py /
test_price_bar_validation.py : requetes compilees + session factice, pas de
base de donnees reelle (voir tests/conftest.py).
"""
import uuid
from types import SimpleNamespace

import pytest

from app.domains.analysis_lab.db_models import STATUS_FAILED, STATUS_PENDING, STATUS_RUNNING
from app.domains.analysis_lab.job_repository import (
    create_job,
    get_job,
    mark_completed,
    mark_failed,
    mark_running,
)


class _CapturingSession:
    def __init__(self, scalar_result=None):
        self.captured_stmt = None
        self.added = []
        self.commit_count = 0
        self.refresh_count = 0
        self._scalar_result = scalar_result

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        self.commit_count += 1

    async def refresh(self, obj):
        self.refresh_count += 1

    async def execute(self, stmt):
        self.captured_stmt = stmt

        class _Result:
            def scalar_one_or_none(self_inner):
                return self._scalar_result

        return _Result()


@pytest.mark.asyncio
async def test_create_job_adds_a_pending_training_job_with_expected_fields():
    session = _CapturingSession()
    asset_id = uuid.uuid4()

    job = await create_job(session, asset_id, "lstm", "medium")

    assert len(session.added) == 1
    added_job = session.added[0]
    assert added_job.asset_id == asset_id
    assert added_job.model_name == "lstm"
    assert added_job.horizon == "medium"
    assert added_job.status == STATUS_PENDING
    assert session.commit_count == 1
    assert session.refresh_count == 1
    assert job is added_job


@pytest.mark.asyncio
async def test_get_job_query_filters_by_id():
    job_id = uuid.uuid4()
    session = _CapturingSession(scalar_result=None)

    await get_job(session, job_id)

    compiled = str(session.captured_stmt.compile(compile_kwargs={"literal_binds": True}))
    assert "training_jobs" in compiled
    # asyncpg/psycopg compilent le literal UUID sans tirets - on compare le hex brut.
    assert job_id.hex in compiled.replace("-", "")


@pytest.mark.asyncio
async def test_mark_running_sets_status_and_commits():
    session = _CapturingSession()
    job = SimpleNamespace(status=STATUS_PENDING)

    await mark_running(session, job)

    assert job.status == STATUS_RUNNING
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_mark_completed_stores_result_and_completed_at():
    session = _CapturingSession()
    job = SimpleNamespace(status=STATUS_RUNNING, result=None, completed_at=None)
    result_payload = {"model_name": "lstm", "predicted_direction": "hausse"}

    await mark_completed(session, job, result_payload)

    assert job.status == "completed"
    assert job.result == result_payload
    assert job.completed_at is not None
    assert session.commit_count == 1


@pytest.mark.asyncio
async def test_mark_failed_sets_error_message_truncated_to_500_chars():
    session = _CapturingSession()
    job = SimpleNamespace(status=STATUS_RUNNING, error_message=None, completed_at=None)
    long_error = "x" * 1000

    await mark_failed(session, job, long_error)

    assert job.status == STATUS_FAILED
    assert len(job.error_message) == 500
    assert job.completed_at is not None
