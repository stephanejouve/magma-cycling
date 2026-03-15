# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| Latest on `main` | Yes |

## Reporting a Vulnerability

**Non-critical bugs**: please open a [GitHub Issue](https://github.com/stephanejouve/magma-cycling/issues).

**Critical security vulnerabilities**: please use
[GitHub Security Advisories](https://github.com/stephanejouve/magma-cycling/security/advisories/new)
to report privately. Do **not** open a public issue for critical vulnerabilities.

Alternatively, you can email the maintainer directly at the address listed in
the git commit history.

## Response timeline

- Acknowledgement within **48 hours**.
- Initial assessment within **7 days**.
- Fix or mitigation plan communicated within **30 days**.

## Scope

This project is a personal training analytics tool. It interacts with:

- **Intervals.icu API** (OAuth / API key)
- **Withings Health API** (OAuth)
- **OpenAI / Anthropic APIs** (API key)

Secrets are managed via environment variables and macOS Keychain. They are
**never** committed to the repository. A `detect-private-key` pre-commit hook
is active.
