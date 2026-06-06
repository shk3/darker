"""Abstract interface for version control operations used by Darker."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Iterable, Set

from darkgraylib.git import RevisionRange
from darkgraylib.utils import TextDocument


class VcsBackend(ABC):
    """Operations Darker needs from a version control system."""

    @staticmethod
    @abstractmethod
    def is_repository(path: Path) -> bool:
        """Return whether ``path`` is inside a repository of this VCS."""

    @abstractmethod
    def get_repository_root(self, path: Path) -> Path | None:
        """Return the repository root containing ``path``."""

    @abstractmethod
    def get_content_at_revision(
        self, path: Path, revision: str, cwd: Path
    ) -> TextDocument:
        """Return file content at ``revision``, or the working tree if ``revision`` is ``:WORKTREE:``."""

    @abstractmethod
    def exists_at_revision(self, path: Path, revision: str, cwd: Path) -> bool:
        """Return whether ``path`` exists at ``revision`` (or on disk for ``:WORKTREE:``)."""

    @abstractmethod
    def get_modified_python_files(
        self, paths: Iterable[Path], revrange: RevisionRange, repo_root: Path
    ) -> Set[Path]:
        """Return repo-relative paths of modified ``*.py`` files in the revision range."""

    @abstractmethod
    def parse_revision_range(
        self, revision_range: str, cwd: Path, stdin_mode: bool
    ) -> RevisionRange:
        """Parse a revision range string for this VCS."""