#!/usr/bin/env python3
"""Publish one complete, immutable package release to Supabase (v3).

Git remains the source of truth. Images are uploaded under content-addressed
paths, then the whole 60-question payload is committed through one Postgres RPC
transaction. Re-running an unchanged package is a no-op; direct content-table
upserts are intentionally no longer part of the publisher.

Environment (never commit these):
    SUPABASE_URL
    SUPABASE_SERVICE_ROLE_KEY

Usage:
    python3 push_to_supabase.py --package 1 [--publish] [--bank-dir PATH]
    python3 push_to_supabase.py --package 1 --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Any, Optional

import requests

from common import BANK_DIR, BLUEPRINT, iter_bank_questions, package_difficulty

BUCKET = "question-images"
DIFFICULTIES = {"easy", "medium", "hard"}


def _postgres_jsonb_order(value: Any) -> Any:
    """Order object keys exactly as PostgreSQL jsonb does for text output."""
    if isinstance(value, dict):
        keys = sorted(value, key=lambda key: (len(key.encode("utf-8")), key.encode("utf-8")))
        return OrderedDict((key, _postgres_jsonb_order(value[key])) for key in keys)
    if isinstance(value, list):
        return [_postgres_jsonb_order(item) for item in value]
    return value


def canonical_hash(value: Any) -> str:
    # schema_v3.sql hashes jsonb::text. PostgreSQL jsonb orders object keys by
    # UTF-8 byte length and then byte value, and renders a space after each
    # comma/colon. Mirroring that representation makes the publisher's
    # diagnostic hash identical to the server-authoritative hash.
    encoded = json.dumps(
        _postgres_jsonb_order(value),
        ensure_ascii=False,
        separators=(", ", ": "),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Client:
    def __init__(self, url: str, key: str):
        self.rest = url.rstrip("/") + "/rest/v1"
        self.storage = url.rstrip("/") + "/storage/v1"
        self.public_object = url.rstrip("/") + f"/storage/v1/object/public/{BUCKET}"
        self.s = requests.Session()
        self.s.headers.update({"apikey": key, "Authorization": f"Bearer {key}"})

    def upload_content_addressed(self, local: Path, object_path: str) -> str:
        object_url = f"{self.storage}/object/{BUCKET}/{object_path}"
        exists = self.s.head(object_url, timeout=30)
        if exists.status_code == 200:
            print(f"  reused image   {object_path}")
            return f"{self.public_object}/{object_path}"
        if exists.status_code not in (400, 404):
            sys.exit(
                f"image probe {object_path} failed: HTTP {exists.status_code}: "
                f"{exists.text[:300]}"
            )

        ctype = mimetypes.guess_type(local.name)[0] or "application/octet-stream"
        response = self.s.post(
            object_url,
            headers={"Content-Type": ctype, "x-upsert": "false"},
            data=local.read_bytes(),
            timeout=60,
        )
        # A concurrent publisher may win between HEAD and POST. The path is the
        # bytes' SHA-256, so 409 means the desired immutable object now exists.
        if response.status_code not in (200, 201, 409):
            sys.exit(
                f"image upload {object_path} failed: HTTP {response.status_code}: "
                f"{response.text[:300]}"
            )
        verb = "reused image" if response.status_code == 409 else "uploaded image"
        print(f"  {verb:<14} {object_path}")
        return f"{self.public_object}/{object_path}"

    def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        response = self.s.post(
            f"{self.rest}/rpc/publish_package_release",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"p_payload": payload}, ensure_ascii=False),
            timeout=120,
        )
        if response.status_code not in (200, 201):
            sys.exit(
                f"publish_package_release failed: HTTP {response.status_code}: "
                f"{response.text[:1000]}"
            )
        return response.json()


def load_package(bank_dir: Path, package_id: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    package_dir = bank_dir / str(package_id)
    manifest_path = package_dir / "package.json"
    if not manifest_path.is_file():
        sys.exit(f"package manifest not found: {manifest_path}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"invalid package manifest {manifest_path}: {exc}")

    if manifest.get("id") != package_id:
        sys.exit(f"{manifest_path}: id must be {package_id}")
    if manifest.get("difficulty") not in DIFFICULTIES:
        sys.exit(f"{manifest_path}: difficulty must be easy, medium, or hard")
    for field in ("title", "description", "ai_model", "ai_company", "ai_model_description"):
        if not isinstance(manifest.get(field), str) or (field != "description" and not manifest[field].strip()):
            sys.exit(f"{manifest_path}: {field} must be a valid string")
    if len(manifest["ai_company"].strip()) > 100:
        sys.exit(f"{manifest_path}: ai_company must be at most 100 characters")
    if len(manifest["ai_model_description"].strip()) > 300:
        sys.exit(f"{manifest_path}: ai_model_description must be at most 300 characters")

    questions: list[dict[str, Any]] = []
    for path, question, error in iter_bank_questions(bank_dir):
        if error:
            sys.exit(f"{path}: {error} — run validate_bank.py first")
        if question["package"] == package_id:
            questions.append(question)
    questions.sort(key=lambda item: item["id"])

    counts = Counter(question["subtest"] for question in questions)
    expected_total = sum(details[2] for details in BLUEPRINT.values())
    if len(questions) != expected_total:
        sys.exit(f"package {package_id}: expected {expected_total} questions, found {len(questions)}")
    for key, (_, _, expected, _, _) in BLUEPRINT.items():
        if counts[key] != expected:
            sys.exit(f"package {package_id}/{key}: expected {expected}, found {counts[key]}")
    calculated, index = package_difficulty(Counter(q["difficulty"] for q in questions))
    if manifest["difficulty"] != calculated:
        sys.exit(
            f"{manifest_path}: difficulty {manifest['difficulty']!r} does not match "
            f"calculated {calculated!r} (index {float(index):.2f})"
        )
    return manifest, questions


def build_question_payload(
    bank_dir: Path,
    package_id: int,
    question: dict[str, Any],
    client: Optional[Client],
) -> tuple[dict[str, Any], str]:
    image_sha: Optional[str] = None
    image_url: Optional[str] = None
    if question.get("image"):
        local = bank_dir / str(package_id) / question["image"]
        if not local.is_file():
            sys.exit(f"{question['id']}: missing image {local}")
        image_sha = file_sha256(local)
        extension = local.suffix.lower() or ".bin"
        object_path = f"{package_id}/{question['id']}/{image_sha}{extension}"
        if client:
            image_url = client.upload_content_addressed(local, object_path)
        else:
            image_url = f"content-addressed://{BUCKET}/{object_path}"

    canonical = {
        "id": question["id"],
        "subtest": question["subtest"],
        "number": question["number"],
        "type": question["type"],
        "question_text": question["question_text"],
        "passage": question.get("passage"),
        "image_sha256": image_sha,
        "difficulty": question["difficulty"],
        "options": question["options"],
        "correct_option": question["correct_option"],
        "explanations": question["explanations"],
    }
    content_hash = canonical_hash(canonical)
    payload = {
        "id": question["id"],
        "subtest_id": f"{package_id}-{question['subtest']}",
        "subtest": question["subtest"],
        "number": question["number"],
        "qtype": question["type"],
        "question_text": question["question_text"],
        "passage": question.get("passage"),
        "image_url": image_url,
        "image_sha256": image_sha,
        "difficulty": question["difficulty"],
        "options": question["options"],
        "correct_option": question["correct_option"],
        "explanations": question["explanations"],
        # Diagnostic only. The SQL RPC independently recomputes its hash.
        "client_content_hash": content_hash,
    }
    return payload, content_hash


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=int, required=True)
    parser.add_argument("--publish", action="store_true", help="publish the resulting release")
    parser.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    manifest, questions = load_package(args.bank_dir, args.package)
    client: Optional[Client] = None
    if not args.dry_run:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            sys.exit("set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment")
        client = Client(url, key)

    question_payloads: list[dict[str, Any]] = []
    hash_pairs: list[list[str]] = []
    for question in questions:
        payload, content_hash = build_question_payload(
            args.bank_dir, args.package, question, client
        )
        question_payloads.append(payload)
        hash_pairs.append([question["id"], content_hash])

    subtests = []
    for key, (name, position, count, duration, passing) in sorted(
        BLUEPRINT.items(), key=lambda item: item[1][1]
    ):
        subtests.append({
            "id": f"{args.package}-{key}",
            "key": key,
            "name": name,
            "position": position,
            "question_count": count,
            "duration_seconds": duration,
            "passing_grade": passing,
        })

    package_hash = canonical_hash({
        "id": args.package,
        "title": manifest["title"],
        "description": manifest["description"],
        "difficulty": manifest["difficulty"],
        "ai_model": manifest["ai_model"],
        "ai_company": manifest["ai_company"],
        "ai_model_description": manifest["ai_model_description"],
        "questions": hash_pairs,
    })
    payload = {
        "package": {
            "id": args.package,
            "title": manifest["title"],
            "description": manifest["description"],
            "difficulty": manifest["difficulty"],
            "ai_model": manifest["ai_model"],
            "ai_company": manifest["ai_company"],
            "ai_model_description": manifest["ai_model_description"],
            # null preserves the current publication state; true publishes.
            "is_published": True if args.publish else None,
            "client_content_hash": package_hash,
        },
        "subtests": subtests,
        "questions": question_payloads,
    }

    print(
        f"package {args.package}: {len(questions)} questions, "
        f"difficulty={manifest['difficulty']}, model={manifest['ai_model']} "
        f"({manifest['ai_company']})"
    )
    print(f"  local package hash {package_hash}")
    if args.dry_run:
        print("dry run — content-addressed paths and canonical hashes computed; nothing uploaded or published")
        return

    assert client is not None
    result = client.publish(payload)
    action = "created" if result.get("created") else "unchanged"
    print(
        f"done — release v{result.get('version')} {action}; "
        f"{result.get('new_question_revisions', 0)} new question revision(s)"
    )


if __name__ == "__main__":
    main()
