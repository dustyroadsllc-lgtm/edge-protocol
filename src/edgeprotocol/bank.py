"""Load the locked question bank and verify its cryptographic lock.

Hard constraint 3: the program refuses to run if the SHA-256 of the bank
file does not match protocol/LOCK. Changing questions requires a new
versioned bank file with its own lock — never editing v0.1.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BANK_PATH = PROJECT_ROOT / "protocol" / "bank_v0_1.json"
LOCK_PATH = PROJECT_ROOT / "protocol" / "LOCK"


class BankIntegrityError(RuntimeError):
    """Raised when the bank file does not match its lock."""


def verify_lock(bank_path: Path = BANK_PATH, lock_path: Path = LOCK_PATH) -> str:
    """Return the bank's sha256 hex digest, or raise BankIntegrityError."""
    if not bank_path.exists():
        raise BankIntegrityError(f"Bank file missing: {bank_path}")
    if not lock_path.exists():
        raise BankIntegrityError(f"LOCK file missing: {lock_path}")
    actual = hashlib.sha256(bank_path.read_bytes()).hexdigest()
    expected = lock_path.read_text(encoding="ascii").strip()
    if actual != expected:
        raise BankIntegrityError(
            "Question bank does not match protocol/LOCK.\n"
            f"  expected: {expected}\n"
            f"  actual:   {actual}\n"
            "The bank is pre-registered and immutable. If you need different "
            "questions, create bank_v0_2.json with its own LOCK."
        )
    return actual


def load_bank(bank_path: Path = BANK_PATH, lock_path: Path = LOCK_PATH) -> dict[str, Any]:
    """Verify the lock, then load and return the bank."""
    verify_lock(bank_path, lock_path)
    bank = json.loads(bank_path.read_text(encoding="utf-8"))
    return bank


def get_question(bank: dict[str, Any], question_id: str) -> dict[str, Any]:
    for question in bank["questions"]:
        if question["id"] == question_id:
            return question
    valid = ", ".join(q["id"] for q in bank["questions"])
    raise KeyError(f"Unknown question id {question_id!r}. Valid ids: {valid}")


def question_ids(bank: dict[str, Any]) -> list[str]:
    return [q["id"] for q in bank["questions"]]
