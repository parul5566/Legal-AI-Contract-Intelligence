"""Idempotent seeder: users + sample documents + auto-queued analysis."""
import logging
import os
import uuid

from app.config import settings
from app.db import SessionLocal
from app.models import AnalysisJob, Document, User
from app.security import hash_password

log = logging.getLogger("seed")

SEED_USERS = [
    ("admin@legalai.test", "Admin User", "Admin@123", "admin"),
    ("analyst@legalai.test", "Ana List", "Analyst@123", "analyst"),
    ("viewer@legalai.test", "Vera Viewer", "Viewer@123", "viewer"),
]

SEED_DOCS = [
    ("msa_v1.txt", "MSA_Northbridge_Meridian_v1.txt"),
    ("msa_v2.txt", "MSA_Northbridge_Meridian_v2_revised.txt"),
    ("nda.txt", "NDA_Cascade_Harborview.txt"),
]


def seed() -> None:
    db = SessionLocal()
    try:
        admin = None
        for email, name, pw, role in SEED_USERS:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    email=email, name=name, password_hash=hash_password(pw), role=role
                )
                db.add(user)
                db.flush()
                log.info("seeded user %s (%s)", email, role)
            if role == "admin":
                admin = user
        db.commit()

        if not admin:
            log.error("no admin user; aborting doc seeding")
            return

        os.makedirs(settings.upload_dir, exist_ok=True)
        data_dir = os.path.join(os.path.dirname(__file__), "seed_data")
        for src, display in SEED_DOCS:
            exists = (
                db.query(Document)
                .filter(Document.owner_id == admin.id, Document.original_name == display)
                .first()
            )
            if exists:
                continue
            src_path = os.path.join(data_dir, src)
            with open(src_path, "rb") as f:
                content = f.read()
            stored = f"{uuid.uuid4().hex}.txt"
            with open(os.path.join(settings.upload_dir, stored), "wb") as f:
                f.write(content)
            doc = Document(
                owner_id=admin.id,
                filename=stored,
                original_name=display,
                mime="text/plain",
                size_bytes=len(content),
                status="pending",
            )
            db.add(doc)
            db.flush()
            db.add(AnalysisJob(document_id=doc.id, kind="document", status="queued"))
            log.info("seeded document %s", display)
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    seed()
