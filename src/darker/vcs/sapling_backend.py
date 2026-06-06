"""Sapling (``sl``) implementation of :class:`darker.vcs.base.VcsBackend`."""

from __future__ import annotations

import logging
import os
import re
import shlex
import sys
from functools import lru_cache
from pathlib import Path
from subprocess import DEVNULL, PIPE, CalledProcessError, check_output  # nosec
from typing import Iterable, List, Set

from darker.vcs.base import VcsBackend
from darkgraylib.command_line import EXIT_CODE_UNKNOWN
from darkgraylib.git import PRE_COMMIT_FROM_TO_REFS, STDIN, WORKTREE, RevisionRange
from darkgraylib.utils import TextDocument

logger = logging.getLogger(__name__)

_DIFF_STAT_FILE_RE = re.compile(r"^\s*(\S.*?)\s+\|\s+")


def _sl_rev(revision: str) -> str:
    if revision in {WORKTREE, STDIN}:
        return "."
    if revision in {"", "HEAD"}:
        return "."
    return revision


@lru_cache(maxsize=1)
def _make_sl_env() -> dict[str, str]:
    return {"LC_ALL": "C.UTF-8", **os.environ}


def _sl_check_output(
    cmd: List[str],
    cwd: Path,
    *,
    exit_on_error: bool = True,
    encoding: str | None = "utf-8",
) -> str | bytes:
    logger.debug("[%s]$ sl %s", cwd, shlex.join(cmd))
    try:
        return check_output(  # nosec
            ["sl"] + cmd,
            cwd=str(cwd),
            encoding=encoding,
            stderr=PIPE,
            env=_make_sl_env(),
        )
    except CalledProcessError as exc_info:
        if not exit_on_error:
            raise
        if encoding and exc_info.stderr:
            sys.stderr.write(exc_info.stderr)
        sys.exit(EXIT_CODE_UNKNOWN)


def _sl_check_output_lines(
    cmd: List[str], cwd: Path, exit_on_error: bool = True
) -> List[str]:
    return _sl_check_output(cmd, cwd, exit_on_error=exit_on_error).splitlines()


class SaplingVcsBackend(VcsBackend):
    """Sapling SCM backend using the ``sl`` command-line tool."""

    @staticmethod
    def is_repository(path: Path) -> bool:
        try:
            lines = _sl_check_output_lines(
                ["root"], path if path.is_dir() else path.parent, exit_on_error=False
            )
            return bool(lines)
        except CalledProcessError:
            return False

    def get_repository_root(self, path: Path) -> Path | None:
        try:
            lines = _sl_check_output_lines(
                ["root"], path if path.is_dir() else path.parent, exit_on_error=False
            )
            return Path(lines[0]) if lines else None
        except CalledProcessError:
            return None

    def get_content_at_revision(
        self, path: Path, revision: str, cwd: Path
    ) -> TextDocument:
        if path.is_absolute():
            raise ValueError(
                f"the 'path' parameter must receive a relative path, got {path!r} instead"
            )
        if revision == WORKTREE:
            return TextDocument.from_file(cwd / path)
        sl_rev = _sl_rev(revision)
        try:
            content = _sl_check_output(
                ["cat", "-r", sl_rev, path.as_posix()],
                cwd,
                exit_on_error=False,
                encoding=None,
            )
            return TextDocument.from_bytes(content)
        except CalledProcessError as exc_info:
            if exc_info.returncode != 1:
                raise
            return TextDocument()

    def exists_at_revision(self, path: Path, revision: str, cwd: Path) -> bool:
        if revision == WORKTREE:
            return path.exists()
        sl_rev = _sl_rev(revision)
        result = run(  # nosec
            ["sl", "cat", "-r", sl_rev, path.as_posix()],
            cwd=str(cwd),
            check=False,
            stdout=DEVNULL,
            stderr=DEVNULL,
            env=_make_sl_env(),
        )
        return result.returncode == 0

    def get_modified_python_files(
        self, paths: Iterable[Path], revrange: RevisionRange, repo_root: Path
    ) -> Set[Path]:
        repo_paths = [path.resolve().relative_to(repo_root) for path in paths]
        changed_paths = self._diff_name_only(
            revrange.rev1, revrange.rev2, repo_paths, repo_root
        )
        if revrange.rev2 == WORKTREE:
            changed_paths.update(self._status_untracked(repo_paths, repo_root))
        from darker.git import should_reformat_file

        return {
            path
            for path in changed_paths
            if should_reformat_file(repo_root / path)
        }

    def parse_revision_range(
        self, revision_range: str, cwd: Path, stdin_mode: bool
    ) -> RevisionRange:
        rev1, rev2, use_common_ancestor = RevisionRange._parse(revision_range, stdin_mode)
        if use_common_ancestor:
            rev2_for_ancestor = "HEAD" if rev2 in {WORKTREE, STDIN} else rev2
            rev1 = self._common_ancestor(rev1, rev2_for_ancestor, cwd)
        return RevisionRange(rev1, rev2)

    def _common_ancestor(self, rev1: str, rev2: str, cwd: Path) -> str:
        rev1_sl = _sl_rev(rev1) if rev1 not in {"", "HEAD"} else rev1 or "."
        rev2_sl = _sl_rev(rev2)
        query = f"ancestor({rev1_sl}, {rev2_sl})"
        lines = _sl_check_output_lines(["log", "-r", query, "-T", "{node}"], cwd)
        if not lines:
            return rev1
        return lines[0]

    def _diff_name_only(
        self,
        rev1: str,
        rev2: str,
        relative_paths: Iterable[Path],
        repo_root: Path,
    ) -> Set[Path]:
        path_args = [path.as_posix() for path in relative_paths]
        if rev2 == WORKTREE:
            cmd = ["diff", "-r", _sl_rev(rev1), "--stat", "--", *path_args]
        else:
            cmd = [
                "diff",
                "-r",
                _sl_rev(rev1),
                "-r",
                _sl_rev(rev2),
                "--stat",
                "--",
                *path_args,
            ]
        lines = _sl_check_output_lines(cmd, repo_root, exit_on_error=False)
        names: Set[Path] = set()
        for line in lines:
            match = _DIFF_STAT_FILE_RE.match(line)
            if match:
                names.add(Path(match.group(1).strip()))
        return names

    def _status_untracked(
        self, relative_paths: Iterable[Path], repo_root: Path
    ) -> Set[Path]:
        cmd = ["status", "-mardu", "--", *[p.as_posix() for p in relative_paths]]
        lines = _sl_check_output_lines(cmd, repo_root, exit_on_error=False)
        untracked: Set[Path] = set()
        for line in lines:
            if line.startswith("? "):
                untracked.add(Path(line[2:].strip()))
        return untracked