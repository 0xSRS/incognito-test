#!/usr/bin/env python3
"""
Reads flags_out.csv (from generate_flags.py) and, per user, generates:

  - directory  : random path, e.g. incogito05.tech/gseigshuvesugrsuecmr
                 (this is the page that will show the flag, get
                 snapshotted via Wayback Machine, then get deleted)
  - magic_link : random token, stored and emailed as-is (no hashing --
                 fine for a short-lived project like this one)

NOTE: encoding happens later (in generate_gists.py), applied to the Gist
URL -- not to the directory itself. This script only builds the directory
+ magic link.

Same "don't touch existing records" rule as generate_flags.py: rerunning
only adds rows for emails not already in the output file.

Usage:
    python generate_magic_links.py flags_out.csv --out magic_links_out.csv
"""

import argparse
import csv
import os
import secrets
import string

DOMAIN = "incogito05.tech"
DIR_LEN = 20


def make_directory() -> str:
    slug = "".join(secrets.choice(string.ascii_lowercase) for _ in range(DIR_LEN))
    return f"{DOMAIN}/{slug}"


def load_existing(out_path: str) -> dict:
    if not os.path.exists(out_path):
        return {}
    fields = ["name", "email", "flag", "directory", "magic_link"]
    with open(out_path, newline="", encoding="utf-8") as f:
        # keep only the fields this version writes -- drops any stale
        # columns (e.g. magic_link_hash, encoding_type) left over from
        # an older version of this script's output file
        return {row["email"]: {k: row[k] for k in fields} for row in csv.DictReader(f)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("flags_csv", help="Output of generate_flags.py")
    parser.add_argument("--out", default="magic_links_out.csv")
    args = parser.parse_args()

    existing = load_existing(args.out)
    results = dict(existing)

    with open(args.flags_csv, newline="", encoding="utf-8") as f_in:
        for row in csv.DictReader(f_in):
            email = row["email"].strip()
            if email in results:
                continue  # already has a directory/magic link -- don't touch it

            directory = make_directory()
            magic_link = secrets.token_urlsafe(24)

            results[email] = {
                "name": row["name"],
                "email": email,
                "flag": row["flag"],
                "directory": directory,
                "magic_link": magic_link,
            }
            print(f"NEW  {row['name']:<15} {email:<30} dir=/{directory.split('/')[1]}")

    fieldnames = ["name", "email", "flag", "directory", "magic_link"]
    with open(args.out, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results.values())

    print(f"\nDone. {len(results) - len(existing)} new record(s) added. Total: {len(results)}. Written to {args.out}")


if __name__ == "__main__":
    main()