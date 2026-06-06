"""Per-run VCS backend selection for Darker."""

from __future__ import annotations

from contextvars import ContextVar
from pathlib import Path

from typing import Literal

from darker.vcs.base import VcsBackend
from darker.vcs.git_backend import GitVcsBackend

VcsName = Literal["auto", "git", "sapling"]

_active_backend: ContextVar[VcsBackend | None] = ContextVar(
    "darker_vcs_backend", default=None
)
_active_vcs_name: ContextVar[VcsName] = ContextVar("darker_vcs_name", default="auto")


def _resolve_backend(path: Path, preference: VcsName) -> VcsBackend | None:
    if preference == "git":
        return GitVcsBackend() if GitVcsBackend.is_repository(path) else None
    from darker.vcs.sapling_backend import SaplingVcsBackend

    if preference == "sapling":
        return SaplingVcsBackend() if SaplingVcsBackend.is_repository(path) else None
    if GitVcsBackend.is_repository(path):
        return GitVcsBackend()
    if SaplingVcsBackend.is_repository(path):
        return SaplingVcsBackend()
    return None


def set_active_vcs(path: Path, preference: VcsName = "auto") -> VcsBackend | None:
    """Select and store the VCS backend for the current Darker run."""
    _active_vcs_name.set(preference)
    backend = _resolve_backend(path, preference)
    _active_backend.set(backend)
    return backend


def get_active_vcs() -> VcsBackend | None:
    return _active_backend.get()


def get_active_vcs_preference() -> VcsName:
    return _active_vcs_name.get()