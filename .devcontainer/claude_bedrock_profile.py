#!/usr/bin/env python3
"""Launch Claude Code with a Bedrock API key stored in an AWS profile.

AWS does not natively load Bedrock bearer tokens from the shared credentials
file. This launcher reads the repository-specific AWS_BEARER_TOKEN_BEDROCK
entry from the selected profile and exposes it only to the Claude Code process.
"""

from __future__ import annotations

import configparser
import json
import os
from pathlib import Path
import sys
from typing import Mapping

AWS_PROFILE = "AWS_PROFILE"
AWS_SHARED_CREDENTIALS_FILE = "AWS_SHARED_CREDENTIALS_FILE"
BEDROCK_BEARER_TOKEN = "AWS_BEARER_TOKEN_BEDROCK"
REAL_CLAUDE = Path("/home/vscode/.local/bin/claude")


class ConfigurationError(RuntimeError):
    """A configuration file could not be used safely."""


def _profile_from_settings(path: Path) -> str | None:
    if not path.is_file():
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ConfigurationError(f"Claude settings could not be read: {path}") from exc

    env = data.get("env")
    if env is None:
        return None
    if not isinstance(env, dict):
        raise ConfigurationError(f"Claude settings contain an invalid env object: {path}")

    profile = env.get(AWS_PROFILE)
    if profile is None:
        return None
    if not isinstance(profile, str):
        raise ConfigurationError(f"Claude settings contain an invalid AWS_PROFILE: {path}")

    profile = profile.strip()
    return profile or None


def _settings_paths(cwd: Path, home: Path) -> list[Path]:
    paths: list[Path] = []
    current = cwd.resolve()

    for directory in (current, *current.parents):
        claude_dir = directory / ".claude"
        paths.extend(
            (
                claude_dir / "settings.local.json",
                claude_dir / "settings.json",
            )
        )

    paths.append(home / ".claude" / "settings.json")
    return paths


def resolve_profile(environ: Mapping[str, str], cwd: Path, home: Path) -> str:
    explicit = environ.get(AWS_PROFILE, "").strip()
    if explicit:
        return explicit

    for path in _settings_paths(cwd, home):
        profile = _profile_from_settings(path)
        if profile:
            return profile

    return "default"


def credentials_path(environ: Mapping[str, str], home: Path) -> Path:
    configured = environ.get(AWS_SHARED_CREDENTIALS_FILE, "").strip()
    if configured:
        return Path(configured).expanduser()
    return home / ".aws" / "credentials"


def read_bedrock_api_key(path: Path, profile: str) -> str | None:
    if not path.is_file():
        return None

    parser = configparser.ConfigParser(interpolation=None)
    try:
        with path.open(encoding="utf-8") as credentials:
            parser.read_file(credentials)
    except (OSError, UnicodeError, configparser.Error) as exc:
        # Do not include parser details: they can contain the secret line.
        raise ConfigurationError(f"AWS credentials could not be read: {path}") from exc

    if not parser.has_section(profile):
        return None

    token = parser.get(profile, BEDROCK_BEARER_TOKEN, fallback=None)
    if token is None:
        return None

    token = token.strip()
    if not token:
        return None
    if "\n" in token or "\r" in token:
        raise ConfigurationError(
            f"{BEDROCK_BEARER_TOKEN} must be a single line in AWS profile {profile}"
        )
    return token


def prepare_environment(
    environ: Mapping[str, str],
    cwd: Path,
    home: Path,
) -> dict[str, str]:
    prepared = dict(environ)
    profile = resolve_profile(prepared, cwd, home)
    prepared[AWS_PROFILE] = profile

    # An explicitly supplied environment variable follows normal AWS
    # precedence. Otherwise, bridge the repository-specific profile entry.
    if not prepared.get(BEDROCK_BEARER_TOKEN):
        token = read_bedrock_api_key(credentials_path(prepared, home), profile)
        if token:
            prepared[BEDROCK_BEARER_TOKEN] = token

    return prepared


def main() -> int:
    try:
        prepared = prepare_environment(
            os.environ,
            Path.cwd(),
            Path.home(),
        )
    except ConfigurationError as exc:
        print(f"claude-bedrock-profile: {exc}", file=sys.stderr)
        return 78

    if not REAL_CLAUDE.is_file():
        print(
            f"claude-bedrock-profile: Claude Code binary not found: {REAL_CLAUDE}",
            file=sys.stderr,
        )
        return 127

    os.execve(
        REAL_CLAUDE,
        (str(REAL_CLAUDE), *sys.argv[1:]),
        prepared,
    )
    return 127


if __name__ == "__main__":
    raise SystemExit(main())
