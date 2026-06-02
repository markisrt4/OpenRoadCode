import subprocess

from modules.audio.audio_controller_if import AudioControllerIf


class PipewireAudioController(AudioControllerIf):
    def __init__(
        self,
        steps: int = 8,
        step_percent: int = 5,
    ) -> None:
        self.steps = steps
        self.step_percent = step_percent

    def volume_up(self) -> int:
        self._run_wpctl(["set-volume", "@DEFAULT_AUDIO_SINK@", f"{self.step_percent}%+"])
        return self.get_volume_level()

    def volume_down(self) -> int:
        self._run_wpctl(["set-volume", "@DEFAULT_AUDIO_SINK@", f"{self.step_percent}%-"])
        return self.get_volume_level()
    
    def get_volume_level(self) -> int:
        try:
            result = self._run_wpctl(
                ["get-volume", "@DEFAULT_AUDIO_SINK@"],
                capture=True,
            )

            # Example: Volume: 0.62
            parts = result.strip().split()
            if len(parts) >= 2:
                volume = float(parts[1])
                return self._clamp_level(round(volume * self.steps))

        except Exception:
            pass

        return self.steps // 2

    def set_volume_level(self, level: int) -> int:
        level = self._clamp_level(level)
        volume = level / self.steps

        self._run_wpctl(["set-volume", "@DEFAULT_AUDIO_SINK@", str(volume)])
        return self.get_volume_level()

    def _clamp_level(self, level: int) -> int:
        return max(0, min(level, self.steps))

    @staticmethod
    def _run_wpctl(args: list[str], capture: bool = False) -> str:
        result = subprocess.run(
            ["wpctl", *args],
            capture_output=capture,
            text=True,
            check=False,
        )

        if capture:
            return result.stdout

        return ""
