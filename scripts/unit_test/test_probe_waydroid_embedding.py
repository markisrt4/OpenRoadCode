# SPDX-FileCopyrightText: 2026 Mark G. Russell
# SPDX-License-Identifier: MIT
from scripts.probe_waydroid_embedding import parse_geometry, android_window_frames, activity_orientation, compatibility_overrides


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


def test_orientation_is_scoped_to_panera_activity():
    text = '''
    * Hist #0: ActivityRecord{abc u0 com.panera.bread/.MainActivity t1}
      overrideOrientation=SCREEN_ORIENTATION_NOSENSOR
      requestedOrientation=SCREEN_ORIENTATION_PORTRAIT
      mSizeCompatScale=0.5
      mCompatDisplayInsets=unused private data
  Other task:
    overrideOrientation=SCREEN_ORIENTATION_LANDSCAPE
    * Hist #1: ActivityRecord{def u0 com.other.app/.SecretActivity t2}
      requestedOrientation=SCREEN_ORIENTATION_LANDSCAPE
'''
    assert activity_orientation(text) == [{'overrideOrientation': 'SCREEN_ORIENTATION_NOSENSOR',
        'requestedOrientation': 'SCREEN_ORIENTATION_PORTRAIT', 'size_compat_scale': '0.5',
        'has_size_compat_insets': True}]


def test_compat_flags_distinguish_known_from_enabled_without_other_apps():
    text = '''ChangeId(265464455; name=OVERRIDE_ANY_ORIENTATION; disabled; packageOverrides={com.panera.bread=true, com.other.app=false}; overridable)
ChangeId(265451093; name=OVERRIDE_UNDEFINED_ORIENTATION_TO_NOSENSOR; disabled; overridable)
'''
    result = compatibility_overrides(text)
    assert result['OVERRIDE_ANY_ORIENTATION']['panera_override'] is True
    assert result['OVERRIDE_UNDEFINED_ORIENTATION_TO_NOSENSOR']['known']
    assert result['OVERRIDE_UNDEFINED_ORIENTATION_TO_NOSENSOR']['panera_override'] is None
    assert result['FORCE_RESIZE_APP'] == {'known': False}
