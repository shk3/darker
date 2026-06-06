"""Unit tests for :mod:`darker.utils`"""

# pylint: disable=comparison-with-callable,redefined-outer-name,use-dict-literal

import logging
from textwrap import dedent

from darker.utils import debug_dump, ensure_trailing_newline
from darkgraylib.utils import TextDocument


def test_ensure_trailing_newline_adds_when_missing():
    doc = TextDocument.from_str("x = 1", encoding="utf-8", override_newline="\n")
    result = ensure_trailing_newline(doc)
    assert result.string == "x = 1\n"


def test_ensure_trailing_newline_idempotent():
    doc = TextDocument.from_str("x = 1\n", encoding="utf-8")
    assert ensure_trailing_newline(doc) is doc


def test_ensure_trailing_newline_empty_unchanged():
    doc = TextDocument.from_str("", encoding="utf-8")
    assert ensure_trailing_newline(doc).string == ""


def test_debug_dump(caplog, capsys):
    """darker.utils.debug_dump()"""
    caplog.set_level(logging.DEBUG)
    debug_dump([(1, ("black",), ("chunks",))], [2, 3])
    assert capsys.readouterr().out == (
        dedent(
            """\
            --------------------------------------------------------------------------------
             -   1 black
             +     chunks
            --------------------------------------------------------------------------------
            """
        )
    )
