"""Version control backends for Darker (Git and Sapling)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from darker.vcs.base import VcsBackend
from darker.vcs.git_backend import GitVcsBackend
from darker.vcs.sapling_backend import SaplingVcsBackend

VcsName = Literal["auto", "git", "sapling"]

__all__ = [
    "GitVcsBackend",
    "SaplingVcsBackend",
    "VcsBackend",
    "VcsName",
    "detect_vcs",
    "find_repository_root",
    "get_vcs_backend",
]


def detect_vcs(path: Path) -> str | None:
    """Return ``'git'``, ``'sapling'``, or ``None`` if no supported VCS is found."""
    if GitVcsBackend.is_repository(path):
        return "git"
    if SaplingVcsBackend.is_repository(path):
        return "sapling"
    return None


def get_vcs_backend(path: Path, preference: VcsName = "auto") -> VcsBackend | None:
    """Return a VCS backend for ``path``, or ``None`` if none applies."""
    if preference == "git":
        return GitVcsBackend() if GitVcsBackend.is_repository(path) else None
    if preference == "sapling":
        return SaplingVcsBackend() if SaplingVcsBackend.is_repository(path) else None
    kind = detect_vcs(path)
    if kind == "git":
        return GitVcsBackend()
    if kind == "sapling":
        return SaplingVcsBackend()
    return None


def find_repository_root(path_search_start: tuple[str, ...] | Path, vcs: VcsName = "auto") -> Path:
    """Find the repository root for Git or Sapling."""
    if isinstance(path_search_start, Path):
        starts = (path_search_start,)
    else:
        starts = tuple(Path(p) for p in path_search_start)
    for start in starts:
        resolved = start.resolve()
        candidate = resolved if resolved.is_dir() else resolved.parent
        backend = get_vcs_backend(candidate, preference=vcs)
        if backend is not None:
            root = backend.get_repository_root(candidate)
            if root is not None:
                return root
    from darkgraylib.files import find_project_root

    return find_project_root(path_search_start if not isinstance(path_search_start, Path) else (str(path_search_start),))