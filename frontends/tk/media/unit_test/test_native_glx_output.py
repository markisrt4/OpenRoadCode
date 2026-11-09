# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT
"""Routine backend output is quiet without losing diagnostics or context errors."""
import logging
import sys

import pytest

from frontends.tk.media.native_music_visualizer import _create_glx_context


PROGRESS = '''GLX version: 1.4
Screen is  0
Number of FBconfigs 208
Got a matching visual: index 89 33 xid 0x21
Is Direct?:  1
Done making a first context'''


def test_context_progress_is_debug_only_and_return_value_is_preserved(capsys, caplog):
    caplog.set_level(logging.DEBUG)

    def create():
        print(PROGRESS)
        return 42

    assert _create_glx_context(create) == 42
    assert capsys.readouterr().out == ''
    assert len(caplog.records) == 6
    assert all(record.levelno == logging.DEBUG for record in caplog.records)
    assert 'FBconfigs 208' in caplog.text


def test_context_errors_propagate_and_stdout_is_restored(capsys):
    error = RuntimeError('GLX context creation failed')

    def create():
        print(PROGRESS)
        print('driver diagnostic', file=sys.stderr)
        raise error

    with pytest.raises(RuntimeError) as caught:
        _create_glx_context(create)
    assert caught.value is error
    print('application output')
    captured = capsys.readouterr()
    assert captured.out == 'application output\n'
    assert captured.err == 'driver diagnostic\n'


def test_unrecognized_backend_messages_remain_visible_as_warnings(caplog):
    _create_glx_context(lambda: print('oh dear - visual does not match'))
    assert 'visual does not match' in caplog.text
    assert caplog.records[0].levelno == logging.WARNING
