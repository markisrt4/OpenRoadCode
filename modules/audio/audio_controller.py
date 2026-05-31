from modules.audio.audio_controller_if import AudioControllerIf


class AudioController:
    def __init__(self, backend: AudioControllerIf) -> None:
        self.backend = backend

    def volume_up(self) -> int:
        return self.backend.volume_up()

    def volume_down(self) -> int:
        return self.backend.volume_down()

    def get_volume_level(self) -> int:
        return self.backend.get_volume_level()

    def set_volume_level(self, level: int) -> int:
        return self.backend.set_volume_level(level)
