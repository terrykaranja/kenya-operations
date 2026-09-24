"""Create a user from the command line.

Usage:
    python -m app.cli.create_user <username> <password> [--admin]
"""

import argparse
import sys

from app.auth import hash_password
from app.db import SessionLocal
from app.models.user import User


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a SEZ Ledger user")
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("--admin", action="store_true", help="Grant admin privileges")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == args.username).first():
            print(f"User '{args.username}' already exists", file=sys.stderr)
            raise SystemExit(1)

        user = User(
            username=args.username,
            password_hash=hash_password(args.password),
            is_admin=args.admin,
            is_active=True,
        )
        db.add(user)
        db.commit()
        print(f"Created user '{user.username}' (admin={user.is_admin})")
    finally:
        db.close()


if __name__ == "__main__":
    main()
