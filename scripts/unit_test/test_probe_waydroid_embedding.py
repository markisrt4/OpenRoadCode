# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from scripts.probe_waydroid_embedding import parse_geometry, android_window_frames


def test_geometry_retains_parent_relative_offsets_and_sizes():
    assert parse_geometry('''
  Absolute upper-left X: 700
  Absolute upper-left Y: 134
  Relative upper-left X: 0
  Relative upper-left Y: -32
  Width: 567
  Height: 585
''') == {'width': 567, 'height': 585, 'relative_x': 0, 'relative_y': -32,
          'absolute_x': 700, 'absolute_y': 134}


def test_only_panera_geometry_is_reported_without_window_contents():
    output = '''
  Window #0 Window{123 u0 com.other.app/PrivateTitle}:
    mFrame=[0,0][500,500]
  Window #1 Window{456 u0 com.panera.bread/MainActivity}:
    mFrame=[0,24][567,505]
    secret payment/user content
  Window #2 Window{789 u0 com.other.app/PrivateTitle}:
    mFrame=[0,0][123,456]
'''
    assert android_window_frames(output) == [['[0,24][567,505]']]
