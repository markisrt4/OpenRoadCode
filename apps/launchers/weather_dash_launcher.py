from pathlib import Path
from typing import Callable, Optional

from apps.launchers.streamlit_launcher import StreamlitLauncher


class WeatherDashLauncher(StreamlitLauncher):
    def __init__(
        self,
        project_root: Optional[Path] = None,
        port: int = 8501,
    ):
        if project_root is None:
            project_root = Path(__file__).resolve().parents[2]

        app_path = project_root / "apps" / "carUi" / "weather_dash.py"

        super().__init__(
            app_path=app_path,
            port=port,
            log_file="/tmp/carsdr-weather.log",
            browser_log_file="/tmp/carsdr-weather-browser.log",
        )

    def launch(
        self,
        remote_display: str = ":2",
        set_status: Optional[Callable[[str], None]] = None,
    ) -> None:
        if set_status:
            set_status("Launching weather dashboard...")

        super().launch(
            remote_display=remote_display,
            set_status=set_status,
        )
