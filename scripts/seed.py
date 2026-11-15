"""Demo Database Seeding Script for Custodian AI.

Creates the demo accounts (student1, student2, faculty1) and seeds the
"Demo Exam" (10 MCQs + 2 Written Questions, 30-minute timer) from AGENTS.md Section 9.
Fully idempotent: safe to execute multiple times without duplicating records.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Add project root to sys.path so core and shared modules can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.ledger import SQLAlchemyLedgerRepository
from shared.auth import hash_password
from shared.config import get_settings


def seed_demo_data(database_url: str | None = None) -> None:
    settings = get_settings()
    db_url = database_url or settings.database_url
    print(f"[seed] Initializing database at: {db_url}")

    repo = SQLAlchemyLedgerRepository(database_url=db_url)
    repo.init_db()

    # 1. Seed Demo Accounts
    accounts = [
        (settings.demo_student1_username, settings.demo_student1_password, "student"),
        (settings.demo_student2_username, settings.demo_student2_password, "student"),
        (settings.demo_faculty1_username, settings.demo_faculty1_password, "faculty"),
    ]

    for username, password, role in accounts:
        existing = repo.get_user(username)
        if not existing:
            hashed = hash_password(password)
            user = repo.create_user(
                username=username,
                password_hash=hashed,
                role=role,
                created_at=time.time(),
            )
            print(f"[seed] Created {role} account: '{username}' (id={user.id})")
        else:
            print(f"[seed] Account '{username}' already exists (id={existing.id})")

    # 2. Seed Demo Exam
    existing_exam = repo.get_exam(1)
    if not existing_exam:
        exam_questions = {
            "multiple_choice": [
                {
                    "id": 1,
                    "question": "What is the primary objective of Custodian AI?",
                    "options": [
                        "A) Automatic disqualification",
                        "B) Evidence under uncertainty and human holding",
                        "C) Continuous facial recognition storage",
                        "D) Raw audio recording",
                    ],
                    "answer": "B",
                },
                {
                    "id": 2,
                    "question": "What is the default risk score half-life (H) in seconds?",
                    "options": ["A) 60s", "B) 120s", "C) 240s", "D) 480s"],
                    "answer": "C",
                },
                {
                    "id": 3,
                    "question": "Which channel cap (Kc) prevents single-sensor warnings?",
                    "options": ["A) 40.0", "B) 50.0", "C) 75.0", "D) 100.0"],
                    "answer": "A",
                },
                {
                    "id": 4,
                    "question": "What threshold score is required for candidate WARNED tier?",
                    "options": ["A) 25", "B) 45", "C) 65", "D) 80"],
                    "answer": "B",
                },
                {
                    "id": 5,
                    "question": "What is the duration of the initial calibration window?",
                    "options": ["A) 10 seconds", "B) 30 seconds", "C) 60 seconds", "D) 5 minutes"],
                    "answer": "B",
                },
                {
                    "id": 6,
                    "question": "What resolution multiplier does a TECHNICAL finding receive?",
                    "options": ["A) 1.0", "B) 0.40", "C) 0.15", "D) 0.0"],
                    "answer": "D",
                },
                {
                    "id": 7,
                    "question": "Which Bayes hypothesis represents environmental distraction?",
                    "options": ["A) deliberate", "B) technical", "C) ordinary", "D) inconclusive"],
                    "answer": "C",
                },
                {
                    "id": 8,
                    "question": "What happens when an exam is escalated to HELD?",
                    "options": [
                        "A) Automatic grade 0 is assigned",
                        "B) Exam terminates permanently",
                        "C) Exam pauses and is referred to human faculty",
                        "D) Candidate is blocked from university",
                    ],
                    "answer": "C",
                },
                {
                    "id": 9,
                    "question": "How long must candidate tier hold before transition?",
                    "options": ["A) 2 seconds", "B) 6 seconds", "C) 15 seconds", "D) 30 seconds"],
                    "answer": "B",
                },
                {
                    "id": 10,
                    "question": "What extra benefit is provided upon receiving a Second Notice?",
                    "options": [
                        "A) Bonus marks",
                        "B) 10 minutes added off-the-clock",
                        "C) Immediate retake",
                        "D) Exam skip",
                    ],
                    "answer": "B",
                },
            ],
            "written_questions": [
                {
                    "id": 11,
                    "question": "Explain difference between score threshold and escalation gate.",
                    "points": 5,
                },
                {
                    "id": 12,
                    "question": "Why is the evidence ledger designed to be strictly append-only?",
                    "points": 5,
                },
            ],
        }

        exam = repo.create_exam(
            title="Demo Exam",
            description=json.dumps(exam_questions),
            duration_minutes=30,
            created_at=time.time(),
        )
        print(
            f"[seed] Created Demo Exam: '{exam.title}' (id={exam.id}, "
            f"duration={exam.duration_minutes}m)"
        )
    else:
        print(f"[seed] Demo Exam already exists (id={existing_exam.id})")

    print("[seed] Seeding completed successfully.")


if __name__ == "__main__":
    db_arg = sys.argv[1] if len(sys.argv) > 1 else None
    seed_demo_data(db_arg)
