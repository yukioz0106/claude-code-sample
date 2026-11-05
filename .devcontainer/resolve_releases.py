#!/usr/bin/env python3
"""Resolve AWS CLI and Claude Code releases with a minimum age of 14 days by default."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping


GITHUB_API_VERSION = "2022-11-28"
GITHUB_RELEASES_URL = "https://api.github.com/repos/{repository}/releases"
AWS_CHANGELOG_URL = "https://raw.githubusercontent.com/aws/aws-cli/v2/CHANGELOG.rst"
MAX_PAGES = 50
PAGE_SIZE = 100
SEMVER_PATTERN = re.compile(r"^v?(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$")


class ResolutionError(RuntimeError):
    """Raised when no trustworthy eligible release can be resolved."""


def parse_utc_timestamp(value: str) -> datetime:
    """Parse an ISO-8601 timestamp and normalize it to UTC."""
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ResolutionError(f"Invalid ISO-8601 timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        raise ResolutionError(f"Timestamp must include a UTC offset: {value!r}")
    return parsed.astimezone(timezone.utc)


def parse_http_timestamp(value: str) -> datetime:
    """Parse an HTTP Last-Modified timestamp and normalize it to UTC."""
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError) as error:
        raise ResolutionError(f"Invalid HTTP timestamp: {value!r}") from error
    if parsed.tzinfo is None:
        raise ResolutionError(f"HTTP timestamp must include a UTC offset: {value!r}")
    return parsed.astimezone(timezone.utc)


def format_utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_semver(tag_name: str) -> tuple[int, int, int] | None:
    match = SEMVER_PATTERN.fullmatch(tag_name)
    if match is None:
        return None
    return tuple(int(part) for part in match.groups())


def github_headers() -> dict[str, str]:
    return {
        "Accept": "application/vnd.github+json",
        "User-Agent": "claude-code-sample-devcontainer-release-resolver/1",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }


def retryable(error: BaseException) -> bool:
    return not isinstance(error, urllib.error.HTTPError) or error.code in {
        408,
        429,
        500,
        502,
        503,
        504,
    }


def request_json(url: str, *, attempts: int = 4) -> Any:
    for attempt in range(attempts):
        request = urllib.request.Request(url, headers=github_headers())
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return json.load(response)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            if not retryable(error) or attempt == attempts - 1:
                raise ResolutionError(f"Failed to retrieve release metadata from {url}: {error}") from error
            time.sleep(2**attempt)
    raise AssertionError("retry loop ended unexpectedly")


def request_text(url: str, *, attempts: int = 4) -> str:
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": github_headers()["User-Agent"]},
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except UnicodeDecodeError as error:
            raise ResolutionError(f"Release metadata from {url} is not valid UTF-8") from error
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as error:
            if not retryable(error) or attempt == attempts - 1:
                raise ResolutionError(f"Failed to retrieve release metadata from {url}: {error}") from error
            time.sleep(2**attempt)
    raise AssertionError("retry loop ended unexpectedly")


def request_headers(url: str, *, attempts: int = 4) -> Mapping[str, str]:
    for attempt in range(attempts):
        request = urllib.request.Request(
            url,
            headers={"User-Agent": github_headers()["User-Agent"]},
            method="HEAD",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.headers
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return {}
            if not retryable(error) or attempt == attempts - 1:
                raise ResolutionError(f"Failed to inspect installer metadata at {url}: {error}") from error
            time.sleep(2**attempt)
        except (urllib.error.URLError, TimeoutError) as error:
            if attempt == attempts - 1:
                raise ResolutionError(f"Failed to inspect installer metadata at {url}: {error}") from error
            time.sleep(2**attempt)
    raise AssertionError("retry loop ended unexpectedly")


def select_release(
    releases: Iterable[dict[str, Any]],
    cutoff: datetime,
    *,
    required_major: int | None = None,
) -> dict[str, Any] | None:
    """Select the numerically newest stable GitHub release published by cutoff."""
    candidates: list[tuple[tuple[int, int, int], datetime, dict[str, Any]]] = []
    for release in releases:
        if release.get("draft") is not False or release.get("prerelease") is not False:
            continue

        tag_name = release.get("tag_name")
        published_at = release.get("published_at")
        if not isinstance(tag_name, str) or not isinstance(published_at, str):
            continue

        version = parse_semver(tag_name)
        if version is None or (required_major is not None and version[0] != required_major):
            continue

        try:
            published = parse_utc_timestamp(published_at)
        except ResolutionError:
            continue
        if published <= cutoff:
            candidates.append((version, published, release))

    if not candidates:
        return None
    _, _, selected = max(candidates, key=lambda candidate: (candidate[0], candidate[1]))
    return selected


def resolve_repository(
    repository: str,
    cutoff: datetime,
    *,
    required_major: int | None = None,
    fetch_json: Callable[[str], Any] = request_json,
) -> dict[str, Any]:
    releases: list[dict[str, Any]] = []
    pagination_complete = False
    for page in range(1, MAX_PAGES + 1):
        url = f"{GITHUB_RELEASES_URL.format(repository=repository)}?per_page={PAGE_SIZE}&page={page}"
        response = fetch_json(url)
        if not isinstance(response, list) or not all(isinstance(item, dict) for item in response):
            raise ResolutionError(f"Unexpected GitHub release response for {repository}")
        releases.extend(response)

        if len(response) < PAGE_SIZE:
            pagination_complete = True
            break

    if not pagination_complete:
        raise ResolutionError(
            f"Cannot determine the newest release for {repository}: GitHub pagination "
            f"exceeded the {MAX_PAGES}-page safety limit"
        )

    selected = select_release(releases, cutoff, required_major=required_major)
    if selected is not None:
        return selected

    raise ResolutionError(
        f"No stable semantic-version release for {repository} was published on or before "
        f"{format_utc_timestamp(cutoff)}"
    )


def parse_aws_cli_versions(changelog: str) -> list[tuple[tuple[int, int, int], str]]:
    """Extract complete AWS CLI v2 release headings from the official changelog."""
    candidates: dict[tuple[int, int, int], str] = {}
    lines = changelog.splitlines()
    for index, line in enumerate(lines[:-1]):
        version_text = line.strip()
        version = parse_semver(version_text)
        underline = lines[index + 1].strip()
        if (
            version is not None
            and version[0] == 2
            and len(underline) >= len(version_text)
            and set(underline) == {"="}
        ):
            candidates[version] = version_text
    return sorted(candidates.items(), reverse=True)


def resolve_aws_cli(
    cutoff: datetime,
    architecture: str,
    *,
    fetch_text: Callable[[str], str] = request_text,
    fetch_headers: Callable[[str], Mapping[str, str]] = request_headers,
) -> dict[str, str]:
    """Resolve AWS CLI using its complete changelog and installer upload time."""
    aws_architecture = {"amd64": "x86_64", "arm64": "aarch64"}.get(architecture)
    if aws_architecture is None:
        raise ResolutionError(f"Unsupported architecture: {architecture}")

    candidates = parse_aws_cli_versions(fetch_text(AWS_CHANGELOG_URL))
    if not candidates:
        raise ResolutionError("No AWS CLI v2 releases found in the official changelog")

    for _, version_text in candidates:
        tag_name = version_text
        installer_url = (
            "https://awscli.amazonaws.com/"
            f"awscli-exe-linux-{aws_architecture}-{version_text}.zip"
        )
        headers = fetch_headers(installer_url)
        last_modified_text = headers.get("Last-Modified")
        if not last_modified_text:
            continue
        last_modified = parse_http_timestamp(last_modified_text)
        if last_modified <= cutoff:
            return {
                "repository": "aws/aws-cli",
                "version": version_text,
                "tag_name": tag_name,
                "installer_last_modified": format_utc_timestamp(last_modified),
                "release_url": f"https://github.com/aws/aws-cli/tree/{tag_name}",
                "download_url": installer_url,
                "signature_url": f"{installer_url}.sig",
            }

    raise ResolutionError(
        "No AWS CLI v2 installer was uploaded on or before "
        f"{format_utc_timestamp(cutoff)}"
    )


def release_record(repository: str, release: dict[str, Any]) -> dict[str, str]:
    tag_name = release["tag_name"]
    version = tag_name[1:] if tag_name.startswith("v") else tag_name
    return {
        "repository": repository,
        "version": version,
        "tag_name": tag_name,
        "published_at": format_utc_timestamp(parse_utc_timestamp(release["published_at"])),
        "release_url": f"https://github.com/{repository}/releases/tag/{tag_name}",
    }


def resolve(resolution_time: datetime, architecture: str, minimum_age_days: int) -> dict[str, Any]:
    if minimum_age_days < 1:
        raise ResolutionError("minimum age must be at least one day")
    if architecture not in {"amd64", "arm64"}:
        raise ResolutionError(f"Unsupported architecture: {architecture}")

    cutoff = resolution_time - timedelta(days=minimum_age_days)
    aws_release = resolve_aws_cli(cutoff, architecture)
    claude_release = resolve_repository("anthropics/claude-code", cutoff)

    return {
        "schema_version": 2,
        "resolution_time": format_utc_timestamp(resolution_time),
        "cutoff_time": format_utc_timestamp(cutoff),
        "minimum_age_seconds": minimum_age_days * 24 * 60 * 60,
        "minimum_age_applies_to": ["aws_cli", "claude_code"],
        "architecture": architecture,
        "aws_cli": aws_release,
        "claude_code": release_record("anthropics/claude-code", claude_release),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resolution-time", required=True, help="UTC build-start timestamp")
    parser.add_argument("--architecture", required=True, choices=("amd64", "arm64"))
    parser.add_argument("--minimum-age-days", type=int, default=14)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()

    try:
        result = resolve(
            parse_utc_timestamp(arguments.resolution_time),
            arguments.architecture,
            arguments.minimum_age_days,
        )
        arguments.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (OSError, ResolutionError) as error:
        print(f"release resolution failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
