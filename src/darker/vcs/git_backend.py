"""Git implementation of :class:`darker.vcs.base.VcsBackend`."""

from __future__ import annotations

import logging
from pathlib import Path
from subprocess import CalledProcessError
from typing import Iterable, Set

from darker.vcs.base import VcsBackend
from darkgraylib.git import (
    WORKTREE,
    RevisionRange,
    git_check_output_lines,
    git_get_content_at_revision,
    make_git_env,
)
from darkgraylib.utils import TextDocument

logger = logging.getLogger(__name__)


class GitVcsBackend(VcsBackend):
    """Git-backed VCS operations (delegates to :mod:`darker.git` and darkgraylib)."""

    @staticmethod
    def is_repository(path: Path) -> bool:
        try:
            lines = git_check_output_lines(
                ["rev-parse", "--is-inside-work-tree"], path, exit_on_error=False
            )
            return lines[:1] == ["true"]
        except CalledProcessError as exc_info:
            if exc_info.returncode != 128 or not exc_info.stderr.startswith(
                "fatal: not a git repository"
            ):
                raise
            return False

    def get_repository_root(self, path: Path) -> Path | None:
        from darkgraylib.git import git_get_root

        return git_get_root(path if path.is_dir() else path.parent)

    def get_content_at_revision(
        self, path: Path, revision: str, cwd: Path
    ) -> TextDocument:
        return git_get_content_at_revision(path, revision, cwd)

    def exists_at_revision(self, path: Path, revision: str, cwd: Path) -> bool:
        from darker import git as darker_git

        return darker_git._git_exists_in_revision(path, revision, cwd)

    def get_modified_python_files(
        self, paths: Iterable[Path], revrange: RevisionRange, repo_root: Path
    ) -> Set[Path]:
        from darker import git as darker_git

        return darker_git.git_get_modified_python_files(paths, revrange, repo_root)

    def parse_revision_range(
        self, revision_range: str, cwd: Path, stdin_mode: bool
    ) -> RevisionRange:
        return RevisionRange.parse_with_common_ancestor(revision_range, cwd, stdin_mode)


def _git_merge_base(rev1: str, rev2: str, cwd: Path) -> str:
    return git_check_output_lines(["merge-base", rev1, rev2], cwd)[0]