"""Configure the local Comvoly owner's password and session secret."""

from __future__ import annotations

import getpass
import secrets
from pathlib import Path

from auth import hash_password


BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = BACKEND_DIR / ".env"


def update_setting(lines: list[str], name: str, value: str) -> list[str]:
    prefix = f"{name}="
    replacement = f"{prefix}{value}\n"
    for index, line in enumerate(lines):
        if line.startswith(prefix):
            lines[index] = replacement
            return lines
    if lines and lines[-1].strip():
        lines.append("\n")
    lines.append(replacement)
    return lines


def main() -> None:
    print("Configure the local Comvoly owner sign-in.")
    password = getpass.getpass("New owner password (12+ characters): ")
    confirmation = getpass.getpass("Confirm owner password: ")
    if password != confirmation:
        raise SystemExit("The passwords did not match. Nothing was changed.")
    password_hash = hash_password(password)
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines(keepends=True) if ENV_PATH.exists() else []
    update_setting(lines, "COMVOLY_OWNER_PASSWORD_HASH", password_hash)
    update_setting(lines, "COMVOLY_SESSION_SECRET", secrets.token_urlsafe(48))
    ENV_PATH.write_text("".join(lines), encoding="utf-8")
    print("Owner sign-in configured. Existing sessions have been signed out.")


if __name__ == "__main__":
    main()
