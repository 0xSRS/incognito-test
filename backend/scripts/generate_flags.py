#!/usr/bin/env python3
"""
CSV (Full Name, Email Address, ...) -> flags in the form:  FirstName{8-char-random}
Alphabet for the random part: A-Z a-z 0-9 $ _ @

Usage:
    python generate_flags.py participants.csv --out flags_out.csv
"""

import argparse
import csv
import hashlib
import os
import secrets
import string

ALPHABET = string.ascii_letters + string.digits + "$_@"


def make_flag(name: str) -> str:
    suffix = "".join(secrets.choice(ALPHABET) for _ in range(8))
    return f"{name}{{{suffix}}}"


def load_existing(out_path: str) -> dict:
    """email -> row, for people already present in a previous run's output."""
    if not os.path.exists(out_path):
        return {}
    with open(out_path, newline="", encoding="utf-8") as f:
        return {row["email"]: row for row in csv.DictReader(f)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", help="Input CSV with columns: name,email")
    parser.add_argument("--out", default="flags_out.csv", help="Output CSV path")
    args = parser.parse_args()

    existing = load_existing(args.out)  # keyed by email, kept as-is
    results = dict(existing)

    with open(args.csv_path, newline="", encoding="utf-8") as f_in:
        for row in csv.DictReader(f_in):
            name = row["Full Name"].strip().split()[0]  # first word only
            email = row["Email Address"].strip()

            if email in results:
                continue  # already has a flag from a previous run -- don't touch it

            flag = make_flag(name)
            flag_hash = hashlib.sha256(flag.encode()).hexdigest()
            results[email] = {"name": name, "email": email, "flag": flag, "flag_hash": flag_hash}
            print(f"NEW  {name:<15} {email:<30} {flag}")

    with open(args.out, "w", newline="", encoding="utf-8") as f_out:
        writer = csv.DictWriter(f_out, fieldnames=["name", "email", "flag", "flag_hash"])
        writer.writeheader()
        writer.writerows(results.values())

    print(f"\nDone. {len(results) - len(existing)} new record(s) added. Total: {len(results)}. Written to {args.out}")


if __name__ == "__main__":
    main()