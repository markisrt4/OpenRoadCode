from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class PositionFix:
    """
    Holds a receiver's geographic position fix in SI units.

    @param latitude_rad  Latitude measured in radians (rad).
    @param longitude_rad Longitude measured in radians (rad).
    @param altitude_m    Altitude measured in metres (m) above sea level.
    @param pfom_m        Position figure of merit (PFOM) measured in metres (m).
    """
    latitude_rad: float
    longitude_rad: float
    altitude_m: float | None
    pfom_m: float | None


@dataclass(frozen=True, slots=True)
class SatelliteInfo:
    """!
    @brief Represents real-time tracking metrics for a single GNSS satellite.
    @details Stores identity, spatial positioning, signal strength, and
             active solution engagement status for an individual tracked satellite.
    @param sat_id        Unique Satellite Identifier (PRN).
    @param constellation Constellation type, e.g., 'GPS', 'GLONASS
    @param elevation_rad Angle from local horizon in radians [0 to pi/2].
    @param azimuth_rad   Bearing from true north in radians [0 to 2*pi).
    @param snr_db_hz     Signal-to-noise ratio in dB-Hz, or None without lock.
    @param is_used_in_fix Flags whether this satellite is actively
    """

    ## Unique Satellite Identifier (PRN)
    sat_id: int

    ## Constellation type, e.g., 'GPS', 'GLONASS', 'Galileo', 'BeiDou'
    constellation: str

    ## Angle from local horizon in radians [0 to pi/2]
    elevation_rad: float | None

    ## Bearing from true north in radians [0 to 2*pi)
    azimuth_rad: float | None

    ## Signal-to-Noise Ratio in dB-Hz. Set to None if tracked but not locked.
    snr_db_hz: float | None

    ## Flags whether this satellite is actively used in the current PVT fix.
    is_used_in_fix: bool = False


class PositionUiIf(ABC):
    """Display receiver position and the current complete satellite snapshot.

    ``None`` passed to set_position() means no position fix is available.
    An empty satellite sequence means no satellites are currently visible.
    """

    @abstractmethod
    def set_position(self, position_fix: PositionFix | None) -> None:
        """Replace the current receiver position fix.

        @param position_fix Current position fix, or None when unavailable.
        """
        ...

    @abstractmethod
    def set_satellites(
        self,
        satellites: Sequence[SatelliteInfo],
    ) -> None:
        """Replace all currently displayed satellite information.

        @param satellites Complete current satellite collection.
        """
        ...
