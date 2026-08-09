#!/usr/bin/env python3
"""Idempotently push a question-bank package from git to Supabase.

Upserts packages, subtests, questions, options, and answer keys via the
PostgREST API using the service-role key, and uploads any images to the
public `question-images` Storage bucket. Safe to re-run after edits
(stable IDs derived from bank paths; `resolution=merge-duplicates`).

Environment (never commit these):
    SUPABASE_URL                e.g. https://xxxx.supabase.co
    SUPABASE_SERVICE_ROLE_KEY   service-role secret (Project Settings → API)

Usage:
    python3 push_to_supabase.py --package 1 [--publish] [--bank-dir PATH] [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import sys
from pathlib import Path

import requests

from common import BANK_DIR, BLUEPRINT, iter_bank_questions

BUCKET = "question-images"


class Client:
    def __init__(self, url: str, key: str):
        self.rest = url.rstrip("/") + "/rest/v1"
        self.storage = url.rstrip("/") + "/storage/v1"
        self.public_object = url.rstrip("/") + f"/storage/v1/object/public/{BUCKET}"
        self.s = requests.Session()
        self.s.headers.update({
            "apikey": key,
            "Authorization": f"Bearer {key}",
        })

    def upsert(self, table: str, rows: list[dict], on_conflict: str) -> None:
        if not rows:
            return
        r = self.s.post(
            f"{self.rest}/{table}",
            params={"on_conflict": on_conflict},
            headers={
                "Content-Type": "application/json",
                "Prefer": "resolution=merge-duplicates,return=minimal",
            },
            data=json.dumps(rows),
            timeout=30,
        )
        if r.status_code not in (200, 201, 204):
            sys.exit(f"upsert {table} failed: HTTP {r.status_code}: {r.text[:500]}")
        print(f"  upserted {len(rows):3d} row(s) into {table}")

    def upload_image(self, local: Path, object_path: str) -> str:
        ctype = mimetypes.guess_type(local.name)[0] or "application/octet-stream"
        r = self.s.post(
            f"{self.storage}/object/{BUCKET}/{object_path}",
            headers={"Content-Type": ctype, "x-upsert": "true"},
            data=local.read_bytes(),
            timeout=60,
        )
        if r.status_code not in (200, 201):
            sys.exit(f"image upload {object_path} failed: HTTP {r.status_code}: {r.text[:300]}")
        print(f"  uploaded image {object_path}")
        return f"{self.public_object}/{object_path}"


def load_package(bank_dir: Path, package_id: int) -> tuple[dict, list[dict]]:
    pkg_dir = bank_dir / str(package_id)
    if not pkg_dir.is_dir():
        sys.exit(f"no such package directory: {pkg_dir}")
    manifest_path = pkg_dir / "package.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {"id": package_id, "title": f"Paket {package_id}", "description": ""}

    questions = []
    for path, q, err in iter_bank_questions(bank_dir):
        if err:
            sys.exit(f"{path}: {err} — run validate_bank.py first")
        if q["package"] == package_id:
            questions.append(q)
    if not questions:
        sys.exit(f"package {package_id} has no questions — generate some first")
    return manifest, questions


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--package", type=int, required=True)
    ap.add_argument("--publish", action="store_true",
                    help="set is_published=true (default keeps current draft state)")
    ap.add_argument("--bank-dir", type=Path, default=BANK_DIR)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    manifest, questions = load_package(args.bank_dir, args.package)
    subtest_keys = sorted({q["subtest"] for q in questions},
                          key=lambda k: BLUEPRINT[k][1])
    print(f"package {args.package}: {len(questions)} questions "
          f"across {len(subtest_keys)} subtest(s): {', '.join(subtest_keys)}")

    if args.dry_run:
        print("dry run — nothing pushed")
        return

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        sys.exit("set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in the environment")
    client = Client(url, key)

    pkg_row = {
        "id": args.package,
        "title": manifest.get("title", f"Paket {args.package}"),
        "description": manifest.get("description", ""),
    }
    if args.publish:
        pkg_row["is_published"] = True
    client.upsert("packages", [pkg_row], on_conflict="id")

    subtest_rows = []
    for k in subtest_keys:
        name, position, qcount, duration, passing = BLUEPRINT[k]
        subtest_rows.append({
            "id": f"{args.package}-{k}",
            "package_id": args.package,
            "key": k,
            "name": name,
            "position": position,
            "question_count": qcount,
            "duration_seconds": duration,
            "passing_grade": passing,
        })
    client.upsert("subtests", subtest_rows, on_conflict="id")

    q_rows, opt_rows, key_rows = [], [], []
    for q in sorted(questions, key=lambda x: x["id"]):
        image_url = None
        if q.get("image"):
            local = args.bank_dir / str(args.package) / q["image"]
            object_path = f"{args.package}/{Path(q['image']).name}"
            image_url = client.upload_image(local, object_path)
        q_rows.append({
            "id": q["id"],
            "subtest_id": f"{q['package']}-{q['subtest']}",
            "number": q["number"],
            "qtype": q["type"],
            "question_text": q["question_text"],
            "passage": q.get("passage"),
            "image_url": image_url,
            "difficulty": q["difficulty"],
        })
        for o in q["options"]:
            opt_rows.append({
                "question_id": q["id"],
                "key": o["key"],
                "text": o["text"],
            })
        key_rows.append({
            "question_id": q["id"],
            "correct_option": q["correct_option"],
            "explanations": q["explanations"],
        })

    client.upsert("questions", q_rows, on_conflict="id")
    client.upsert("question_options", opt_rows, on_conflict="question_id,key")
    client.upsert("answer_keys", key_rows, on_conflict="question_id")
    print("done — remember: git is the source of truth; commit the bank too")


if __name__ == "__main__":
    main()
