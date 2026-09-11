from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import resolve_releases as resolver


def release(
    tag_name: str,
    published_at: str,
    *,
    draft: bool = False,
    prerelease: bool = False,
) -> dict[str, object]:
    return {
        "tag_name": tag_name,
        "published_at": published_at,
        "draft": draft,
        "prerelease": prerelease,
    }


class TimestampTests(unittest.TestCase):
    def test_requires_timezone(self) -> None:
        with self.assertRaisesRegex(resolver.ResolutionError, "UTC offset"):
            resolver.parse_utc_timestamp("2026-09-11T00:00:00")

    def test_normalizes_offset_to_utc(self) -> None:
        parsed = resolver.parse_utc_timestamp("2026-09-11T09:00:00+09:00")
        self.assertEqual(resolver.format_utc_timestamp(parsed), "2026-09-11T00:00:00Z")

    def test_parses_http_timestamp(self) -> None:
        parsed = resolver.parse_http_timestamp("Fri, 28 Aug 2026 00:00:00 GMT")
        self.assertEqual(resolver.format_utc_timestamp(parsed), "2026-08-28T00:00:00Z")


class SelectionTests(unittest.TestCase):
    cutoff = datetime(2026, 8, 28, 0, 0, 0, tzinfo=timezone.utc)

    def test_exact_cutoff_is_eligible_but_one_second_newer_is_not(self) -> None:
        selected = resolver.select_release(
            [
                release("2.0.1", "2026-08-28T00:00:01Z"),
                release("2.0.0", "2026-08-28T00:00:00Z"),
            ],
            self.cutoff,
        )
        self.assertEqual(selected["tag_name"], "2.0.0")

    def test_selects_newest_semantic_version(self) -> None:
        selected = resolver.select_release(
            [
                release("v2.9.9", "2026-08-27T00:00:00Z"),
                release("v2.10.0", "2026-08-26T00:00:00Z"),
            ],
            self.cutoff,
        )
        self.assertEqual(selected["tag_name"], "v2.10.0")

    def test_skips_drafts_prereleases_and_non_semver_tags(self) -> None:
        selected = resolver.select_release(
            [
                release("9.0.0", "2026-08-20T00:00:00Z", draft=True),
                release("8.0.0", "2026-08-20T00:00:00Z", prerelease=True),
                release("7.0.0-beta.1", "2026-08-20T00:00:00Z"),
                release("2.4.0", "2026-08-20T00:00:00Z"),
            ],
            self.cutoff,
            required_major=2,
        )
        self.assertEqual(selected["tag_name"], "2.4.0")

    def test_required_major_is_enforced(self) -> None:
        selected = resolver.select_release(
            [
                release("3.0.0", "2026-08-20T00:00:00Z"),
                release("2.99.0", "2026-08-20T00:00:00Z"),
            ],
            self.cutoff,
            required_major=2,
        )
        self.assertEqual(selected["tag_name"], "2.99.0")


class RepositoryTests(unittest.TestCase):
    def test_paginates_until_an_eligible_release_exists(self) -> None:
        first_page = [
            release(f"2.0.{index}", "2026-09-01T00:00:00Z")
            for index in range(resolver.PAGE_SIZE)
        ]
        second_page = [release("2.0.0", "2026-08-01T00:00:00Z")]
        responses = iter((first_page, second_page))
        requested_urls: list[str] = []

        def fetch(url: str) -> object:
            requested_urls.append(url)
            return next(responses)

        selected = resolver.resolve_repository(
            "example/tool",
            datetime(2026, 8, 28, tzinfo=timezone.utc),
            required_major=2,
            fetch_json=fetch,
        )
        self.assertEqual(selected["tag_name"], "2.0.0")
        self.assertEqual(len(requested_urls), 2)
        self.assertIn("page=2", requested_urls[1])

    def test_rejects_unexpected_response_shape(self) -> None:
        with self.assertRaisesRegex(resolver.ResolutionError, "Unexpected"):
            resolver.resolve_repository(
                "example/tool",
                datetime(2026, 8, 28, tzinfo=timezone.utc),
                fetch_json=lambda _url: {"message": "rate limited"},
            )


class AwsCliTests(unittest.TestCase):
    cutoff = datetime(2026, 8, 28, 0, 0, 0, tzinfo=timezone.utc)

    def test_uses_target_installer_last_modified_at_exact_boundary(self) -> None:
        inspected_urls: list[str] = []

        def fetch_headers(url: str) -> dict[str, str]:
            inspected_urls.append(url)
            if "-2.10.0.zip" in url:
                return {"Last-Modified": "Fri, 28 Aug 2026 00:00:01 GMT"}
            return {"Last-Modified": "Fri, 28 Aug 2026 00:00:00 GMT"}

        selected = resolver.resolve_aws_cli(
            self.cutoff,
            "amd64",
            fetch_json=lambda _url: [
                {"name": "2.9.0"},
                {"name": "preview"},
                {"name": "2.10.0"},
            ],
            fetch_headers=fetch_headers,
        )

        self.assertEqual(selected["version"], "2.9.0")
        self.assertEqual(
            selected["installer_last_modified"],
            "2026-08-28T00:00:00Z",
        )
        self.assertEqual(len(inspected_urls), 2)
        self.assertIn("linux-x86_64", inspected_urls[0])

    def test_skips_missing_installer_and_supports_arm64(self) -> None:
        def fetch_headers(url: str) -> dict[str, str]:
            if "-2.10.0.zip" in url:
                return {}
            return {"Last-Modified": "Thu, 27 Aug 2026 23:59:59 GMT"}

        selected = resolver.resolve_aws_cli(
            self.cutoff,
            "arm64",
            fetch_json=lambda _url: [{"name": "2.10.0"}, {"name": "2.9.0"}],
            fetch_headers=fetch_headers,
        )

        self.assertEqual(selected["version"], "2.9.0")
        self.assertIn("linux-aarch64", selected["download_url"])


class ResultTests(unittest.TestCase):
    def test_cutoff_is_exactly_fourteen_days(self) -> None:
        fake_aws = {
            "repository": "aws/aws-cli",
            "version": "2.3.4",
            "tag_name": "2.3.4",
            "installer_last_modified": "2026-08-01T00:00:00Z",
            "release_url": "https://github.com/aws/aws-cli/tree/2.3.4",
            "download_url": "https://awscli.amazonaws.com/example.zip",
            "signature_url": "https://awscli.amazonaws.com/example.zip.sig",
        }
        fake_claude = release("v5.6.7", "2026-08-02T00:00:00Z")

        with (
            patch.object(resolver, "resolve_aws_cli", return_value=fake_aws) as resolve_aws,
            patch.object(
                resolver,
                "resolve_repository",
                return_value=fake_claude,
            ) as resolve_repository,
        ):
            result = resolver.resolve(
                datetime(2026, 9, 11, 0, 0, 1, tzinfo=timezone.utc),
                "amd64",
                14,
            )

        self.assertEqual(result["cutoff_time"], "2026-08-28T00:00:01Z")
        self.assertEqual(
            result["debian_snapshot"]["requested_timestamp"],
            "20260828T000001Z",
        )
        self.assertEqual(result["aws_cli"]["version"], "2.3.4")
        self.assertEqual(result["claude_code"]["version"], "5.6.7")
        resolve_aws.assert_called_once()
        resolve_repository.assert_called_once()


if __name__ == "__main__":
    unittest.main()
