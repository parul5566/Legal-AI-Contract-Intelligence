"""Analysis queue worker: polls analysis_jobs and runs the pipeline."""
import logging
import os
import time
import traceback
from datetime import datetime, timezone

from app.config import settings
from app.db import SessionLocal
from app.models import AnalysisJob, Document

log = logging.getLogger("worker")
logging.basicConfig(level=logging.INFO)


def claim_next_job():
    db = SessionLocal()
    try:
        job = (
            db.query(AnalysisJob)
            .filter(AnalysisJob.status == "queued")
            .order_by(AnalysisJob.id)
            .first()
        )
        if not job:
            return None
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        job.attempts += 1
        db.commit()
        return job.id
    finally:
        db.close()


def run_job(job_id: int) -> None:
    db = SessionLocal()
    try:
        job = db.get(AnalysisJob, job_id)
        if not job:
            return
        try:
            if job.kind == "document" and job.document_id:
                from app.engine.pipeline import analyze_document

                doc = db.get(Document, job.document_id)
                if not doc:
                    raise ValueError(f"document {job.document_id} missing")
                analyze_document(db, doc, settings.upload_dir)
                job.status = "done"
                job.error = None
            elif job.kind == "comparison" and job.comparison_id:
                from app.engine.pipeline import analyze_comparison
                from app.models import Comparison

                cmp_ = db.get(Comparison, job.comparison_id)
                if not cmp_:
                    raise ValueError(f"comparison {job.comparison_id} missing")
                analyze_comparison(db, cmp_)
                job.status = "done"
                job.error = None
            else:
                job.status = "failed"
                job.error = "unknown job kind or missing target"
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            log.error("job %s failed: %s", job_id, exc)
            traceback.print_exc()
            job = db.get(AnalysisJob, job_id)
            job.status = "failed"
            job.error = str(exc)[:2000]
            if job.kind == "document" and job.document_id:
                doc = db.get(Document, job.document_id)
                if doc:
                    doc.status = "failed"
                    doc.error = str(exc)[:2000]
            if job.kind == "comparison" and job.comparison_id:
                cmp_ = db.get(Comparison, job.comparison_id)
                if cmp_:
                    cmp_.status = "failed"
                    cmp_.error = str(exc)[:2000]
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


def main() -> None:
    log.info("worker started (pid %s)", os.getpid())
    idle_wait = 2.0
    while True:
        try:
            job_id = claim_next_job()
            if job_id is None:
                time.sleep(idle_wait)
                continue
            idle_wait = 2.0
            log.info("running job %s", job_id)
            run_job(job_id)
        except KeyboardInterrupt:
            log.info("worker stopped")
            return
        except Exception as exc:  # noqa: BLE001
            log.exception("worker loop error: %s", exc)
            time.sleep(5)


if __name__ == "__main__":
    main()
