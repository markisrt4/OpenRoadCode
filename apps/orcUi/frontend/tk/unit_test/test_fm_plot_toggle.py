"""FM plot visibility changes presentation without restarting the receiver."""

from unittest.mock import Mock

from apps.orcUi.frontend.tk.radio_panel_layout_mixin import RadioPanelLayoutMixin


def test_hiding_plots_pauses_polling_without_touching_receiver_session():
    panel = Mock()
    panel._plots_visible = True
    panel._sdrforge_after_id = "poll"

    RadioPanelLayoutMixin._set_fm_plots_visible(panel, False)

    assert not panel._plots_visible
    assert panel._sdrforge_after_id is None
    panel.after_cancel.assert_called_once_with("poll")
    panel._layout_fm_plots.assert_called_once_with()
    panel._poll_sdrforge_spectrum.assert_not_called()
    assert panel._session.mock_calls == []

    RadioPanelLayoutMixin._set_fm_plots_visible(panel, True)

    assert panel._plots_visible
    panel._poll_sdrforge_spectrum.assert_called_once_with()
    assert panel._session.mock_calls == []
