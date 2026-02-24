#!/usr/bin/env python3
"""
Setup GitHub branch protection rules for main branch.

Requires: GITHUB_TOKEN environment variable with repo admin access
"""

import os
import sys

import requests


def setup_branch_protection():
    """Configure branch protection for main branch."""
    # Get GitHub token
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN environment variable not set")
        print("\n📝 To create a token:")
        print("1. Go to https://github.com/settings/tokens")
        print("2. Click 'Generate new token (classic)'")
        print("3. Select scopes: 'repo' (full control)")
        print("4. Copy the token and run:")
        print("   export GITHUB_TOKEN='your_token_here'")
        print("   python scripts/setup_branch_protection.py")
        sys.exit(1)

    # Repository info
    owner = os.environ.get("GITHUB_OWNER", "YOUR_USERNAME")
    repo = "cyclisme-training-logs"
    branch = "main"

    # API endpoint
    url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    # Branch protection configuration
    protection_config = {
        "required_status_checks": {
            "strict": True,  # Require branches to be up to date before merging
            "contexts": [
                "lint",
                "test (3.11)",
                "test (3.12)",
                "test (3.13)",
                "mcp-validation",
                "status",
            ],
        },
        "enforce_admins": False,  # Allow admins to bypass (useful for emergency fixes)
        "required_pull_request_reviews": {
            "dismiss_stale_reviews": True,
            "require_code_owner_reviews": False,
            "required_approving_review_count": 0,  # No review required (CI is enough)
        },
        "restrictions": None,  # No push restrictions
        "required_linear_history": False,
        "allow_force_pushes": False,
        "allow_deletions": False,
        "block_creations": False,
        "required_conversation_resolution": True,  # Require PR conversations resolved
        "lock_branch": False,
    }

    print(f"🔒 Setting up branch protection for {owner}/{repo}:{branch}")
    print("\nConfiguration:")
    print(
        f"  ✅ Require status checks: {', '.join(protection_config['required_status_checks']['contexts'])}"
    )
    print(
        f"  ✅ Require branches up to date: {protection_config['required_status_checks']['strict']}"
    )
    print(
        f"  ✅ Require conversation resolution: {protection_config['required_conversation_resolution']}"
    )
    print(f"  ✅ Block force pushes: {not protection_config['allow_force_pushes']}")
    print(f"  ✅ Block deletions: {not protection_config['allow_deletions']}")

    # Apply protection
    response = requests.put(url, headers=headers, json=protection_config)

    if response.status_code == 200:
        print("\n✅ Branch protection successfully configured!")
        print(f"\n🔗 View settings: https://github.com/{owner}/{repo}/settings/branches")
        print("\n📋 Protected branch rules:")
        print("  • All CI checks must pass before merge")
        print("  • Branch must be up to date with main")
        print("  • All PR conversations must be resolved")
        print("  • Force pushes and deletions are blocked")
        print("\n🎉 main branch is now protected!")
        return True
    elif response.status_code == 401:
        print("\n❌ Authentication failed")
        print("Check that your GITHUB_TOKEN has 'repo' scope")
        return False
    elif response.status_code == 403:
        print("\n❌ Permission denied")
        print("Your token needs admin access to the repository")
        return False
    elif response.status_code == 404:
        print("\n❌ Repository or branch not found")
        print(f"Check that {owner}/{repo}:{branch} exists")
        return False
    else:
        print("\n❌ Failed to configure branch protection")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        return False


def check_existing_protection():
    """Check if branch protection already exists."""
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return False

    owner = os.environ.get("GITHUB_OWNER", "YOUR_USERNAME")
    repo = "cyclisme-training-logs"
    branch = "main"

    url = f"https://api.github.com/repos/{owner}/{repo}/branches/{branch}/protection"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        print("ℹ️  Branch protection already exists. It will be updated.")
        return True
    elif response.status_code == 404:
        print("ℹ️  No existing branch protection found. Creating new rules.")
        return False
    return False


if __name__ == "__main__":
    print("=" * 60)
    print("GitHub Branch Protection Setup")
    print("=" * 60)
    print()

    check_existing_protection()
    print()

    if setup_branch_protection():
        print("\n🚀 Next steps:")
        print("  1. Try to push directly to main → Should be blocked!")
        print("  2. Create a PR → CI must pass before merge")
        print("  3. Never debug in production again! 🎊")
    else:
        print("\n⚠️  Setup failed. See instructions above.")
        sys.exit(1)
