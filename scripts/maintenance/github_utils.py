#!/usr/bin/env python3
"""GitHub API utilities for CI monitoring, secrets, and PR lifecycle.

Provides CLI sub-commands:
  wait-ci <pr_number>        — poll PR check runs until completion
  set-secret <name>          — upload an encrypted GitHub Actions secret
  merge-pr <pr_number>       — merge a PR, delete branch, pull main
  create-pr                  — create PR from current branch to main
  wait-main                  — poll CI checks on latest main commit
  codecov-status [--compare] — show current Codecov coverage and delta
  list-prs [--state open]    — list pull requests

Full PR lifecycle in 2 commands:
  python scripts/maintenance/github_utils.py create-pr --title "feat: ..."
  python scripts/maintenance/github_utils.py merge-pr 142 --wait

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
# merge-pr
# ---------------------------------------------------------------------------


def merge_pr(pr_number, wait=False):
    """Merge a PR, delete remote/local branch, pull main."""
    token = _get_token()
    hdrs = _headers(token)

    # Optionally wait for CI first
    if wait:
        print(f"Waiting for CI on PR #{pr_number}...")
        wait_ci(pr_number)

    # 1. Get PR info and verify it's open
    resp = requests.get(f"{API_BASE}/pulls/{pr_number}", headers=hdrs, timeout=15)
    resp.raise_for_status()
    pr_data = resp.json()

    if pr_data["state"] != "open":
        print(f"Error: PR #{pr_number} is not open (state: {pr_data['state']})")
        sys.exit(1)

    branch_name = pr_data["head"]["ref"]
    pr_title = pr_data["title"]
    print(f"PR #{pr_number}: {pr_title}")
    print(f"Branch: {branch_name}")

    # 2. Merge
    resp = requests.put(
        f"{API_BASE}/pulls/{pr_number}/merge",
        headers=hdrs,
        json={"merge_method": "merge"},
        timeout=15,
    )
    resp.raise_for_status()
    merge_data = resp.json()

    if not merge_data.get("merged"):
        print(f"Error: merge failed — {merge_data.get('message', 'unknown')}")
        sys.exit(1)

    print(f"Merged: {merge_data['sha'][:8]}")

    # 3. Delete remote branch
    resp = requests.delete(f"{API_BASE}/git/refs/heads/{branch_name}", headers=hdrs, timeout=15)
    if resp.status_code == 204:
        print(f"Deleted remote branch: {branch_name}")
    else:
        print(f"Warning: could not delete remote branch (HTTP {resp.status_code})")

    # 4. Checkout main if currently on the deleted branch
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    if current_branch == branch_name:
        subprocess.run(["git", "checkout", "main"], capture_output=True, text=True, check=True)

    # 5. Delete local branch (ignore errors if absent)
    try:
        subprocess.run(
            ["git", "branch", "-d", branch_name],
            capture_output=True,
            text=True,
            check=True,
        )
        print(f"Deleted local branch: {branch_name}")
    except subprocess.CalledProcessError:
        pass  # Branch doesn't exist locally

    # 6. Pull main
    try:
        subprocess.run(["git", "checkout", "main"], capture_output=True, text=True, check=True)
        subprocess.run(
            ["git", "pull", "origin", "main"],
            capture_output=True,
            text=True,
            check=True,
        )
        print("Pulled latest main")
    except subprocess.CalledProcessError as e:
        print(f"Warning: git pull failed — {e.stderr.strip()}")

    print(f"\nPR #{pr_number} merged and cleaned up")


# ---------------------------------------------------------------------------
# wait-main
# ---------------------------------------------------------------------------


def wait_main():
    """Poll CI checks on the latest main commit until completion."""
    token = _get_token()
    hdrs = _headers(token)

    # Get latest commit on main
    resp = requests.get(f"{API_BASE}/commits/main", headers=hdrs, timeout=15)
    resp.raise_for_status()
    sha = resp.json()["sha"]
    message = resp.json()["commit"]["message"].split("\n")[0][:60]
    print(f"main — {sha[:8]} — {message}")

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
            print(f"\nAll {len(passed)} checks passed on main")
            return

        time.sleep(POLL_INTERVAL)


# ---------------------------------------------------------------------------
# codecov-status
# ---------------------------------------------------------------------------

CODECOV_API = "https://api.codecov.io/api/v2/github/stephanejouve/repos/magma-cycling"


def codecov_status(compare=False):
    """Show current Codecov coverage, optionally compare with parent commit."""
    token = _get_token()
    hdrs = _headers(token)

    # Get latest main SHA
    resp = requests.get(f"{API_BASE}/commits/main", headers=hdrs, timeout=15)
    resp.raise_for_status()
    sha = resp.json()["sha"]

    # Fetch coverage from Codecov API (public repo, no auth needed)
    resp = requests.get(f"{CODECOV_API}/commits/{sha}", timeout=15)
    if resp.status_code == 200:
        data = resp.json()
        totals = data.get("totals", {})
        coverage = totals.get("coverage")
        if coverage is not None:
            print(f"Codecov main ({sha[:8]}): {coverage:.1f}%")
        else:
            print(f"Codecov main ({sha[:8]}): coverage data not available yet")
            return
    elif resp.status_code == 404:
        print(f"Codecov: no data for commit {sha[:8]} (CI may still be uploading)")
        return
    else:
        print(f"Codecov API error: HTTP {resp.status_code}")
        return

    # Compare with parent commit
    if compare:
        parent_sha = requests.get(f"{API_BASE}/commits/main", headers=hdrs, timeout=15).json()[
            "parents"
        ][0]["sha"]

        resp = requests.get(f"{CODECOV_API}/commits/{parent_sha}", timeout=15)
        if resp.status_code == 200:
            parent_totals = resp.json().get("totals", {})
            parent_coverage = parent_totals.get("coverage")
            if parent_coverage is not None:
                delta = coverage - parent_coverage
                sign = "+" if delta >= 0 else ""
                print(f"Previous ({parent_sha[:8]}): {parent_coverage:.1f}%")
                print(f"Delta: {sign}{delta:.1f}pp")
            else:
                print(f"Previous ({parent_sha[:8]}): no coverage data")
        else:
            print("Previous commit: no Codecov data available")


# ---------------------------------------------------------------------------
# list-prs
# ---------------------------------------------------------------------------


def list_prs(state="open"):
    """List pull requests for the repository."""
    token = _get_token()
    hdrs = _headers(token)

    resp = requests.get(
        f"{API_BASE}/pulls",
        headers=hdrs,
        params={"state": state, "per_page": 20},
        timeout=15,
    )
    resp.raise_for_status()
    prs = resp.json()

    if not prs:
        print(f"No {state} pull requests")
        return

    for pr in prs:
        number = pr["number"]
        title = pr["title"]
        branch = pr["head"]["ref"]
        author = pr["user"]["login"]
        print(f"  #{number}  {title}  ({branch}) — {author}")

    print(f"\n{len(prs)} {state} PR(s)")


# ---------------------------------------------------------------------------
# create-pr
# ---------------------------------------------------------------------------


def create_pr(title=None, body=None):
    """Create a PR from the current branch to main.

    If title/body not provided, deduces them from the last commit message.
    Returns the PR number.
    """
    # 1. Detect current branch
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True,
        text=True,
    ).stdout.strip()

    if current_branch == "main":
        print("Error: cannot create PR from main branch")
        sys.exit(1)

    # 2. Deduce title from last commit if not provided
    if not title:
        title = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            capture_output=True,
            text=True,
        ).stdout.strip()

    # 3. Deduce body from last commit if not provided
    if not body:
        body = subprocess.run(
            ["git", "log", "-1", "--format=%b"],
            capture_output=True,
            text=True,
        ).stdout.strip()

    # 4. Push branch to remote (in case not yet pushed)
    try:
        subprocess.run(
            ["git", "push", "-u", "origin", current_branch],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        # Branch may already be pushed, that's fine
        if "Everything up-to-date" not in e.stderr:
            print(f"Warning: git push — {e.stderr.strip()}")

    # 5. Create PR via API
    token = _get_token()
    hdrs = _headers(token)

    resp = requests.post(
        f"{API_BASE}/pulls",
        headers=hdrs,
        json={
            "title": title,
            "head": current_branch,
            "base": "main",
            "body": body,
        },
        timeout=15,
    )
    resp.raise_for_status()
    pr_data = resp.json()

    pr_number = pr_data["number"]
    pr_url = pr_data["html_url"]
    print(f"PR #{pr_number}: {title}")
    print(f"URL: {pr_url}")

    return pr_number


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

    # merge-pr
    mp = sub.add_parser("merge-pr", help="Merge PR, delete branch, pull main")
    mp.add_argument("pr_number", type=int, help="PR number")
    mp.add_argument("--wait", action="store_true", help="Wait for CI before merging")

    # wait-main
    sub.add_parser("wait-main", help="Poll CI checks on latest main commit")

    # codecov-status
    cs = sub.add_parser("codecov-status", help="Show Codecov coverage for main")
    cs.add_argument("--compare", action="store_true", help="Compare with parent commit")

    # list-prs
    lp = sub.add_parser("list-prs", help="List pull requests")
    lp.add_argument("--state", default="open", choices=["open", "closed", "all"])

    # create-pr
    cp = sub.add_parser("create-pr", help="Create PR from current branch to main")
    cp.add_argument("--title", help="PR title (default: last commit subject)")
    cp.add_argument("--body", help="PR body (default: last commit body)")

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
    elif args.command == "merge-pr":
        merge_pr(args.pr_number, wait=args.wait)
    elif args.command == "wait-main":
        wait_main()
    elif args.command == "codecov-status":
        codecov_status(compare=args.compare)
    elif args.command == "list-prs":
        list_prs(state=args.state)
    elif args.command == "create-pr":
        create_pr(title=args.title, body=args.body)


if __name__ == "__main__":
    main()
