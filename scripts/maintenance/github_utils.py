#!/usr/bin/env python3
"""GitHub API utilities for CI monitoring and secrets management.

Provides two CLI sub-commands:
  wait-ci <pr_number>   — poll PR check runs until completion
  set-secret <name>     — upload an encrypted GitHub Actions secret

Requires: requests, pynacl (for set-secret only).
Token read from macOS keychain (github_token_cyclisme).
"""

import argparse
import base64
import subprocess
import sys
import time

import requests

OWNER = "stephanejouve"
REPO = "magma-cycling"
API_BASE = f"https://api.github.com/repos/{OWNER}/{REPO}"
IGNORED_CHECKS = {"codecov/patch"}
POLL_INTERVAL = 15


def _get_token():
    """Retrieve GitHub token from macOS keychain."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "github_token_cyclisme", "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("Error: cannot read github_token_cyclisme from keychain")
        sys.exit(1)


def _headers(token):
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _keychain_value(service):
    """Read a value from macOS keychain by service name."""
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", service, "-w"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print(f"Error: cannot read '{service}' from keychain")
        sys.exit(1)


# ---------------------------------------------------------------------------
# wait-ci
# ---------------------------------------------------------------------------


def wait_ci(pr_number):
    """Poll check runs for a PR until all complete."""
    token = _get_token()
    hdrs = _headers(token)

    # Get HEAD SHA
    resp = requests.get(f"{API_BASE}/pulls/{pr_number}", headers=hdrs, timeout=15)
    resp.raise_for_status()
    sha = resp.json()["head"]["sha"]
    print(f"PR #{pr_number} — HEAD {sha[:8]}")

    while True:
        resp = requests.get(f"{API_BASE}/commits/{sha}/check-runs", headers=hdrs, timeout=15)
        resp.raise_for_status()
        runs = resp.json().get("check_runs", [])

        pending = []
        failed = []
        passed = []
        for r in runs:
            name = r["name"]
            if name in IGNORED_CHECKS:
                continue
            status = r["status"]
            conclusion = r.get("conclusion")
            if status != "completed":
                pending.append(name)
            elif conclusion == "success":
                passed.append(name)
            else:
                failed.append((name, conclusion))

        # Display current state
        print(
            f"\n[{time.strftime('%H:%M:%S')}] — {len(passed)} passed, "
            f"{len(pending)} pending, {len(failed)} failed"
        )
        for name in pending:
            print(f"  ⏳ {name}")
        for name, conclusion in failed:
            print(f"  ❌ {name} ({conclusion})")
        for name in passed:
            print(f"  ✅ {name}")

        if not pending:
            if failed:
                print(f"\nCI failed ({len(failed)} check(s))")
                sys.exit(1)
            print(f"\nAll {len(passed)} checks passed")
            return

        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# set-secret
# ---------------------------------------------------------------------------


def set_secret(secret_name, value):
    """Upload an encrypted secret to GitHub Actions."""
    from nacl.public import PublicKey, SealedBox

    token = _get_token()
    hdrs = _headers(token)

    # Get repo public key
    resp = requests.get(f"{API_BASE}/actions/secrets/public-key", headers=hdrs, timeout=15)
    resp.raise_for_status()
    key_data = resp.json()
    pub_key = PublicKey(base64.b64decode(key_data["key"]))
    key_id = key_data["key_id"]

    # Encrypt
    sealed = SealedBox(pub_key)
    encrypted = sealed.encrypt(value.encode())
    encrypted_b64 = base64.b64encode(encrypted).decode()

    # Upload
    resp = requests.put(
        f"{API_BASE}/actions/secrets/{secret_name}",
        headers=hdrs,
        json={"encrypted_value": encrypted_b64, "key_id": key_id},
        timeout=15,
    )
    resp.raise_for_status()
    print(f"Secret '{secret_name}' uploaded (HTTP {resp.status_code})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    """Entry point."""
    parser = argparse.ArgumentParser(description="GitHub API utilities")
    sub = parser.add_subparsers(dest="command", required=True)

    # wait-ci
    wci = sub.add_parser("wait-ci", help="Poll PR check runs until completion")
    wci.add_argument("pr_number", type=int, help="PR number")

    # set-secret
    ss = sub.add_parser("set-secret", help="Upload a GitHub Actions secret")
    ss.add_argument("secret_name", help="Secret name (e.g. CODECOV_TOKEN)")
    ss.add_argument("--value", help="Secret value (plain text)")
    ss.add_argument("--from-keychain", help="Read value from macOS keychain service")

    args = parser.parse_args()

    if args.command == "wait-ci":
        wait_ci(args.pr_number)
    elif args.command == "set-secret":
        if args.from_keychain:
            value = _keychain_value(args.from_keychain)
        elif args.value:
            value = args.value
        else:
            print("Error: provide --value or --from-keychain")
            sys.exit(1)
        set_secret(args.secret_name, value)


if __name__ == "__main__":
    main()
