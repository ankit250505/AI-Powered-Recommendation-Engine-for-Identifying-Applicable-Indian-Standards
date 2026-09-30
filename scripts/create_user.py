from __future__ import annotations

import argparse
import getpass
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.auth import create_user_account  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a local prototype user account.")
    parser.add_argument("username")
    parser.add_argument("--role", choices=["procurement", "reviewer", "admin"], required=True)
    parser.add_argument("--password", help="Omit to enter the password securely at the prompt.")
    args = parser.parse_args()

    password = args.password or getpass.getpass("Password: ")
    try:
        user = create_user_account(args.username, password, args.role)
    except ValueError as error:
        raise SystemExit(str(error)) from error
    print(f"Created {user.role} user: {user.username}")


if __name__ == "__main__":
    main()
