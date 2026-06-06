"""Tests for Sapling SCM integration (skipped when ``sl`` is unavailable)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from darker.vcs.sapling_backend import SaplingVcsBackend
from darkgraylib.git import WORKTREE, RevisionRange
from darkgraylib.utils import TextDocument

pytestmark = pytest.mark.skipif(
    shutil.which("sl") is None, reason="Sapling CLI (sl) not installed"
)


@pytest.fixture
def sapling_repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["sl", "init"], cwd=root, check=True, capture_output=True)
    (root / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["sl", "add", "a.py"], cwd=root, check=True, capture_output=True)
    subprocess.run(
        ["sl", "commit", "-m", "init"],
        cwd=root,
        check=True,
        capture_output=True,
    )
    (root / "a.py").write_text("x = 2\n", encoding="utf-8")
    return root


def test_sapling_is_repository(sapling_repo: Path) -> None:
    assert SaplingVcsBackend.is_repository(sapling_repo)
    assert SaplingVcsBackend().get_repository_root(sapling_repo) == sapling_repo


def test_sapling_modified_python_files(sapling_repo: Path) -> None:
    backend = SaplingVcsBackend()
    revrange = RevisionRange("HEAD", WORKTREE)
    changed = backend.get_modified_python_files(
        [Path("a.py")], revrange, sapling_repo
    )
    assert Path("a.py") in changed


def test_sapling_content_at_revision(sapling_repo: Path) -> None:
    backend = SaplingVcsBackend()
    worktree = backend.get_content_at_revision(
        Path("a.py"), WORKTREE, sapling_repo
    )
    assert "x = 2" in worktree.string
    at_head = backend.get_content_at_revision(
        Path("a.py"), "HEAD", sapling_repo
    )
    assert "x = 1" in at_head.string