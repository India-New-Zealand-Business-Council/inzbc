"""Issue a session for local development, until GitHub OAuth exists (#42).

Deliberately a script and not an HTTP route. An endpoint that takes a GitHub username on trust
is account impersonation no matter how it is gated: one stray environment variable in a deployed
config and anyone can post an allowlisted approver's public username and become them. This needs
`DATABASE_URL` and a shell, so it cannot be reached from the network at all.

    python -m scripts.dev_session --github-login someone

Prints the cookie value. It is shown once and stored only as a digest, so losing it means issuing
another rather than looking the old one up.
"""

from __future__ import annotations

import argparse
import os
import sys

from services.api.auth import NotAuthorisedError, SessionRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--github-login", required=True)
    args = parser.parse_args(argv)

    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("DATABASE_URL is not set", file=sys.stderr)
        return 2

    try:
        principal = SessionRepository(database_url).establish_session(args.github_login)
    except NotAuthorisedError as error:
        # The allowlist refusing is the expected outcome for an unknown login, not a crash.
        print(f"refused: {error}", file=sys.stderr)
        return 1

    print(f"user:    {principal.name} ({principal.user_id})")
    print(f"roles:   {', '.join(sorted(principal.roles)) or '(none)'}")
    print(f"cookie:  inzbc_session={principal.session_id}")
    print(f"csrf:    {principal.csrf_token}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
