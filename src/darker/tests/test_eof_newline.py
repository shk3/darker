"""Integration tests for trailing newline on processed files."""

from pathlib import Path

import pytest

from darker import __main__ as darker_main
from darker.tests.helpers import black_present
from darkgraylib.testtools.git_repo_plugin import GitRepoFixture


@pytest.mark.usefixtures(black_present.__name__)
def test_eof_newline_added_on_edited_file(
    git_repo: GitRepoFixture, tmp_path: Path
) -> None:
    """A missing final newline is added when the file is processed."""
    paths = git_repo.add({"a.py": "x=1\n"}, commit="Initial commit")
    path = paths["a.py"]
    path.write_bytes(b"y=2")
    darker_main.main(["a.py"])
    assert path.read_bytes().endswith(b"\n")
    assert b"y=2\n" == path.read_bytes()
