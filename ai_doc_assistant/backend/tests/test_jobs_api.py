import pytest
import io
from httpx import AsyncClient, ASGITransport
import aiosqlite

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.database import init_db
from backend.app.queue.queue_manager import queue_manager


@pytest.mark.anyio
async def test_documents_upload_and_jobs_api():
    await init_db()
    await queue_manager.clear_all()

    kb_id = "kb_api_test"
    async with aiosqlite.connect(settings.DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO knowledge_bases (id, name, version) VALUES (?, ?, ?)", (kb_id, "API Test KB", 1))
        await db.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Upload document asynchronously via /api/documents/upload
        file_content = b"# Real-time Ingestion API\n\nFastAPI handles upload and returns 202 Accepted."
        files = {"file": ("api_guide.md", io.BytesIO(file_content), "text/markdown")}
        data = {"knowledge_base_id": kb_id, "priority": "7"}

        upload_res = await client.post("/api/documents/upload", files=files, data=data)
        assert upload_res.status_code == 202
        upload_data = upload_res.json()
        assert upload_data["status"] == "queued"
        assert "document_id" in upload_data
        assert "job_id" in upload_data
        job_id = upload_data["job_id"]

        # 2. Get Job Details via /api/jobs/{job_id}
        job_res = await client.get(f"/api/jobs/{job_id}")
        assert job_res.status_code == 200
        job_detail = job_res.json()
        assert job_detail["job_id"] == job_id
        assert job_detail["status"] == "QUEUED"
        assert job_detail["priority"] == 7

        # 3. List Jobs via /api/jobs
        list_res = await client.get("/api/jobs?status=QUEUED")
        assert list_res.status_code == 200
        list_data = list_res.json()
        assert list_data["total"] >= 1
        assert any(j["job_id"] == job_id for j in list_data["jobs"])

        # 4. Queue Stats via /api/queue/stats
        stats_res = await client.get("/api/queue/stats")
        assert stats_res.status_code == 200
        stats_data = stats_res.json()
        assert stats_data["queued"] >= 1
        assert stats_data["queue_depth"] >= 1

        # 5. Cancel Job via /api/jobs/{job_id}/cancel
        cancel_res = await client.post(f"/api/jobs/{job_id}/cancel", json={"reason": "User cancelled via API"})
        assert cancel_res.status_code == 200
        assert cancel_res.json()["status"] == "CANCELLED"

        # 6. Retry Job via /api/jobs/{job_id}/retry
        retry_res = await client.post(f"/api/jobs/{job_id}/retry", json={"reset_attempts": True, "priority": 9})
        assert retry_res.status_code == 200
        assert retry_res.json()["status"] == "QUEUED"
