#!/usr/bin/env python3
"""
Reads magic_links_out.csv and, per user:

  1. Creates a secret GitHub Gist whose content is the directory URL
     (https://incogito05.tech/<slug>) -- NOT the flag.
  2. Picks an encoding (base64 / base32 / rot13) and encodes the
     resulting *gist URL* with it -- this encoded string is what
     eventually gets shown to the user after they decode the magic link.

Solve path this supports:
    magic link -> encoded_str -> decode -> gist URL -> open gist ->
    directory URL -> visit directory (404, since it'll be deleted) ->
    hint to check Wayback Machine -> archived page shows the flag.

Requires a GitHub Personal Access Token with the "gist" scope:
    https://github.com/settings/tokens -> Generate new token (classic) -> check "gist"
Pass it via --token or the GITHUB_TOKEN env var.

Same "don't touch existing records" + "resume on failure" behavior as
generate_pastes.py: rerunning only creates gists for emails not already
in the output file, and progress is saved after every single success.

Usage:
    python generate_gists.py magic_links_out.csv --token YOUR_PAT --out gists_out.csv

    # test the pipeline without hitting the real API:
    python generate_gists.py magic_links_out.csv --dry-run --out gists_out.csv
"""

import argparse
import base64
import codecs
import csv
import os
import secrets
import time

import requests

GITHUB_API_URL = "https://api.github.com/gists"
ENCODINGS = ["base64", "base32", "rot13"]


def encode(text: str, scheme: str) -> str:
    if scheme == "base64":
        return base64.b64encode(text.encode()).decode()
    if scheme == "base32":
        return base64.b32encode(text.encode()).decode()
    if scheme == "rot13":
        return codecs.encode(text, "rot13")
    raise ValueError(f"unknown scheme: {scheme}")


def create_gist(token: str, name: str, directory_url: str) -> str:
    """Create a secret gist containing the directory URL. Returns the gist's html_url."""
    resp = requests.post(
        GITHUB_API_URL,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
        },
        json={
            "description": f"{name}",
            "public": False,  # "secret" gist -- unlisted, not truly private
            "files": {"note.txt": {"content": directory_url}},
        },
        timeout=15,
    )
    if resp.status_code != 201:
        raise RuntimeError(f"GitHub API error for {name} ({resp.status_code}): {resp.text}")
    return resp.json()["html_url"]


def load_existing(out_path: str) -> dict:
    if not os.path.exists(out_path):
        return {}
    with open(out_path, newline="", encoding="utf-8") as f:
        return {row["email"]: row for row in csv.DictReader(f)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("magic_links_csv", help="Output of generate_magic_links.py")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN"))
    parser.add_argument("--out", default="gists_out.csv")
    parser.add_argument("--dry-run", action="store_true", help="Skip real API calls, use a fake URL")
    args = parser.parse_args()

    if not args.dry_run and not args.token:
        parser.error("--token or GITHUB_TOKEN env var is required (or use --dry-run)")

    existing = load_existing(args.out)
    results = dict(existing)
    fieldnames = ["name", "email", "flag", "directory", "gist_url", "encoding_type", "encoded_str", "magic_url"]

    def save():
        with open(args.out, "w", newline="", encoding="utf-8") as f_out:
            writer = csv.DictWriter(f_out, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results.values())

    with open(args.magic_links_csv, newline="", encoding="utf-8") as f_in:
        pending = [row for row in csv.DictReader(f_in) if row["email"].strip() not in results]

    stopped_early = False
    for i, row in enumerate(pending):
        email = row["email"].strip()
        directory_url = f"https://{row['directory']}"

        try:
            if args.dry_run:
                gist_url = f"https://gist.github.com/fake/{email[:8]}"
            else:
                gist_url = create_gist(args.token, row["name"], directory_url)
        except Exception as e:
            print(f"STOP at {row['name']} ({email}): {e}")
            print("Progress so far is saved -- rerun this same command later to pick up where it left off.")
            stopped_early = True
            break

        encoding_type = secrets.choice(ENCODINGS)
        encoded_str = encode(gist_url, encoding_type)
        magic_url = f"https://incogito05.tech/magic/{row['magic_link']}"

        results[email] = {
            "name": row["name"],
            "email": email,
            "flag": row["flag"],
            "directory": row["directory"],
            "gist_url": gist_url,
            "encoding_type": encoding_type,
            "encoded_str": encoded_str,
            "magic_url": magic_url,
        }
        print(f"NEW  {row['name']:<15} {email:<30} {gist_url}  enc={encoding_type}")
        save()

        if not args.dry_run and i < len(pending) - 1:
            time.sleep(1)

    added = len(results) - len(existing)
    print(f"\n{'Stopped early' if stopped_early else 'Done'}. {added} new gist(s) created. Total: {len(results)}. Written to {args.out}")


if __name__ == "__main__":
    main()