# SPDX-License-Identifier: MIT

from frontends.tk.media.metadata_text import fit_metadata_text


def test_title_wraps_without_losing_short_song_name():
    assert fit_metadata_text("Peter Gunn Theme", 10, len, lines=2) == "Peter Gunn\nTheme"


def test_long_title_and_artist_fit_with_readable_ellipsis():
    title = fit_metadata_text("A very long track name that will not fit", 12, len, lines=2)
    assert title.endswith("…")
    assert all(len(line) <= 12 for line in title.splitlines())
    assert fit_metadata_text("The Blues Brothers", 12, len, lines=1) == "The Blues B…"


def test_narrow_allocations_and_non_ascii_metadata():
    assert fit_metadata_text("你好音乐", 3, len, lines=1) == "你好…"
    assert fit_metadata_text("Title", 0, len, lines=2) == ""
    assert fit_metadata_text("", 20, len, lines=1) == ""
