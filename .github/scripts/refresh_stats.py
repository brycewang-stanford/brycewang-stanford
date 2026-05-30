#!/usr/bin/env python3
"""Bake live GitHub star/fork counts into README.md as static shields.io badges.

Why: the dynamic ``img.shields.io/github/stars/<owner>/<repo>`` endpoint makes
shields.io call the GitHub API at render time using a shared token pool. When that
pool is rate-limited the badge renders the text
"Unable to select next GitHub token from pool" instead of a number. Static
``img.shields.io/badge/stars-<n>-<color>`` badges are plain text-to-image and never
call the GitHub API, so they always render. This script refreshes the numbers.

Each badge is anchored to its own ``<a href=".../<owner>/<repo>...">`` wrapper, so
the three project cards never get cross-assigned each other's counts. Every
substitution must match exactly once or the script aborts without writing — a
mangled README is never committed.
"""

import json
import re
import subprocess
import sys

OWNER = "brycewang-stanford"

# (repo slug, stars badge color) — color must match the original card styling.
REPOS = [
    ("stata-code", "8C1515"),
    ("StatsPAI", "0EA5E9"),
    ("Auto-Empirical-Research-Skills", "F59E0B"),
]
FORKS_COLOR = "475569"

README = "README.md"


def gh_json(repo):
    out = subprocess.check_output(["gh", "api", f"repos/{OWNER}/{repo}"], text=True)
    return json.loads(out)


def fmt(n):
    """Format a count the way GitHub's native badge does (e.g. 1330 -> '1.3k')."""
    if n >= 1000:
        s = f"{n / 1000:.1f}".rstrip("0").rstrip(".")
        return f"{s}k"
    return str(n)


def bake(readme, repo, kind, href_suffix, value, color):
    """Replace the one badge whose <a> wrapper points at this repo + kind."""
    href = f"https://github.com/{OWNER}/{repo}{href_suffix}"
    badge = f"https://img.shields.io/badge/{kind}-{value}-{color}?style=for-the-badge&logo=github"
    pattern = (
        r'(<a href="' + re.escape(href) + r'"><img alt="[^"]*' + kind + r'" src=")'
        r'[^"]*'
        r'(">)'
    )
    readme, count = re.subn(pattern, lambda m: m.group(1) + badge + m.group(2), readme)
    if count != 1:
        sys.exit(
            f"ERROR: expected exactly 1 {kind} badge for {repo} "
            f"(href {href}), found {count}. Aborting without changes."
        )
    return readme


def main():
    with open(README, encoding="utf-8") as f:
        readme = f.read()
    original = readme

    for repo, color in REPOS:
        data = gh_json(repo)
        stars = fmt(data["stargazers_count"])
        forks = fmt(data["forks_count"])
        readme = bake(readme, repo, "stars", "", stars, color)
        readme = bake(readme, repo, "forks", "/forks", forks, FORKS_COLOR)
        print(f"{repo}: stars={stars} forks={forks}")

    if readme != original:
        with open(README, "w", encoding="utf-8") as f:
            f.write(readme)
        print("README.md updated")
    else:
        print("No changes")


if __name__ == "__main__":
    main()
