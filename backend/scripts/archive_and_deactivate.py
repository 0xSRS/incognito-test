#!/usr/bin/env python3
"""
Archives every active flag page to the Wayback Machine, verifies each
snapshot is accessible (and contains the flag), then sets active=false
in Postgres so the live page starts 404-ing.

Authentication:
    - Anonymous (default): No API key needed. Works fine for small batches.
    - Authenticated (optional): Set WAYBACK_ACCESS_KEY and WAYBACK_SECRET_KEY
      from https://archive.org/account/s3.php for higher rate limits and
      fewer CAPTCHA/429 issues.

Requires:
    pip install psycopg2-binary requests

Usage:
    # Dry run — test what will happen without saving or modifying DB:
    python archive_and_deactivate.py --dry-run

    # Real run against live site:
    python archive_and_deactivate.py

    # Only archive (don't deactivate yet):
    python archive_and_deactivate.py --archive-only

    # Local testing:
    python archive_and_deactivate.py --base-url http://localhost:3000

Environment:
    DATABASE_URL            – Postgres connection string (required)
    WAYBACK_ACCESS_KEY      – Internet Archive S3 Access Key (optional)
    WAYBACK_SECRET_KEY      – Internet Archive S3 Secret Key (optional)
"""

import argparse
import os
import sys
import time

import psycopg2
import requests

WAYBACK_SAVE_URL = "https://web.archive.org/save/"
WAYBACK_SPN2_URL = "https://web.archive.org/save"
WAYBACK_STATUS_URL = "https://web.archive.org/save/status/"
WAYBACK_CHECK_URL = "https://web.archive.org/web/"

SAVE_DELAY = 6
VERIFY_DELAY = 10
VERIFY_RETRIES = 4


def get_active_flags(conn) -> list[dict]:
    """Fetch all active pastes joined with their flags."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT p.paste_id, p.directory, uf.flag
              FROM pastes p
              JOIN user_flags uf ON uf.flag_id = p.flag_id
             WHERE p.active = true
             ORDER BY p.paste_id
            """
        )
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def archive_page_spn2(page_url: str, access_key: str, secret_key: str) -> str | None:
    """Save Page Now 2 (Authenticated API with IA S3 keys)."""
    headers = {
        "Accept": "application/json",
        "Authorization": f"LOW {access_key}:{secret_key}",
    }
    try:
        resp = requests.post(
            WAYBACK_SPN2_URL,
            headers=headers,
            data={"url": page_url, "capture_all": "1"},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"  WARN  SPN2 error ({resp.status_code}): {resp.text}")
            return None

        job_id = resp.json().get("job_id")
        if not job_id:
            return None

        # Poll status
        for _ in range(12):
            time.sleep(3)
            status_resp = requests.get(
                f"{WAYBACK_STATUS_URL}{job_id}",
                headers=headers,
                timeout=15,
            )
            if status_resp.status_code == 200:
                data = status_resp.json()
                if data.get("status") == "success":
                    timestamp = data.get("timestamp")
                    original_url = data.get("original_url", page_url)
                    return f"https://web.archive.org/web/{timestamp}/{original_url}"
                if data.get("status") == "error":
                    print(f"  WARN  archive job failed: {data.get('message')}")
                    return None

        print("  WARN  timed out waiting for archive job")
        return None
    except requests.RequestException as e:
        print(f"  ERROR SPN2 request failed: {e}")
        return None


def archive_page_anonymous(page_url: str) -> str | None:
    """Save Page Now 1 (Anonymous GET request)."""
    try:
        resp = requests.get(
            WAYBACK_SAVE_URL + page_url,
            headers={"User-Agent": "incognito-ctf-archiver/1.0"},
            timeout=60,
            allow_redirects=True,
        )
        if resp.status_code == 200 and "web.archive.org" in resp.url:
            return resp.url
        loc = resp.headers.get("Content-Location")
        if loc:
            return "https://web.archive.org" + loc
        print(f"  WARN  unexpected response ({resp.status_code}): {resp.url}")
        return None
    except requests.RequestException as e:
        print(f"  ERROR anonymous archive failed: {e}")
        return None


def archive_page(page_url: str, access_key: str | None, secret_key: str | None) -> str | None:
    """Archive using SPN2 if keys provided, otherwise anonymous."""
    if access_key and secret_key:
        return archive_page_spn2(page_url, access_key, secret_key)
    return archive_page_anonymous(page_url)


def verify_snapshot(page_url: str, flag: str) -> bool:
    """Check that the Wayback Machine has a snapshot containing the flag."""
    check_url = WAYBACK_CHECK_URL + page_url
    for attempt in range(1, VERIFY_RETRIES + 1):
        try:
            resp = requests.get(
                check_url,
                headers={"User-Agent": "incognito-ctf-archiver/1.0"},
                timeout=30,
                allow_redirects=True,
            )
            if resp.status_code == 200 and flag in resp.text:
                return True
            if attempt < VERIFY_RETRIES:
                print(f"  RETRY ({attempt}/{VERIFY_RETRIES}) snapshot not ready yet, waiting {VERIFY_DELAY}s...")
                time.sleep(VERIFY_DELAY)
        except requests.RequestException as e:
            print(f"  RETRY ({attempt}/{VERIFY_RETRIES}) check error: {e}")
            if attempt < VERIFY_RETRIES:
                time.sleep(VERIFY_DELAY)
    return False


def deactivate(conn, paste_id: int) -> None:
    """Set active=false for a single paste row."""
    with conn.cursor() as cur:
        cur.execute("UPDATE pastes SET active = false WHERE paste_id = %s", (paste_id,))
    conn.commit()


def main():
    parser = argparse.ArgumentParser(
        description="Archive active flag pages to the Wayback Machine, then deactivate them."
    )
    parser.add_argument(
        "--base-url",
        default="https://incogito05.tech",
        help="Base URL of the live site (default: https://incogito05.tech)",
    )
    parser.add_argument(
        "--archive-only",
        action="store_true",
        help="Archive pages but don't deactivate them in the database",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Don't verify snapshots before deactivating (faster, less safe)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would happen without actually archiving or deactivating",
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL environment variable is required.", file=sys.stderr)
        sys.exit(1)

    access_key = os.environ.get("WAYBACK_ACCESS_KEY")
    secret_key = os.environ.get("WAYBACK_SECRET_KEY")

    if access_key and secret_key:
        print("Using authenticated Wayback Machine API (SPN2).\n")
    else:
        print("Using anonymous Wayback Machine API (no keys set).\n")

    conn = psycopg2.connect(db_url)
    rows = get_active_flags(conn)

    if not rows:
        print("No active flag pages found. Nothing to do.")
        conn.close()
        return

    print(f"Found {len(rows)} active flag page(s) to archive.\n")

    archived = 0
    deactivated = 0
    failed = 0

    for i, row in enumerate(rows):
        paste_id = row["paste_id"]
        directory = row["directory"]
        flag = row["flag"]
        slug = directory.split("/", 1)[1] if "/" in directory else directory
        page_url = f"{args.base_url.rstrip('/')}/{slug}"

        print(f"[{i + 1}/{len(rows)}] {directory}")

        if args.dry_run:
            print(f"  DRY   would archive {page_url}")
            print(f"  DRY   would deactivate paste_id={paste_id}")
            continue

        # --- archive ---
        print(f"  SAVE  {page_url}")
        snapshot_url = archive_page(page_url, access_key, secret_key)
        if snapshot_url:
            print(f"  OK    archived -> {snapshot_url}")
            archived += 1
        else:
            print(f"  FAIL  could not archive — skipping (will retry on next run)")
            failed += 1
            continue

        # --- verify ---
        if not args.skip_verify:
            print(f"  WAIT  pausing {VERIFY_DELAY}s before verification...")
            time.sleep(VERIFY_DELAY)
            if verify_snapshot(page_url, flag):
                print(f"  PASS  snapshot verified — flag present in archive")
            else:
                print(f"  FAIL  snapshot verification failed — leaving active")
                failed += 1
                continue

        # --- deactivate ---
        if not args.archive_only:
            deactivate(conn, paste_id)
            print(f"  DONE  paste_id={paste_id} deactivated (now 404s)")
            deactivated += 1

        if i < len(rows) - 1:
            time.sleep(SAVE_DELAY)

    conn.close()

    print(f"\n{'=' * 50}")
    print(f"Archived:    {archived}")
    print(f"Deactivated: {deactivated}")
    print(f"Failed:      {failed}")
    if failed:
        print(f"\nRerun this script to retry the {failed} failed page(s).")
    if args.archive_only and archived:
        print(f"\n--archive-only was set. Run again without it to deactivate.")


if __name__ == "__main__":
    main()
