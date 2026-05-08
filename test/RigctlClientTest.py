import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("PROJECT_ROOT:", PROJECT_ROOT)
print("sys.path:", sys.path[:3])

from modules.sdr.radio_controller import RadioController
from modules.sdr.rigctl_client import RigctlClient
from modules.sdr.rigctl_backend import RigctlBackend
from modules.sdr.radio_controller import RadioController, RadioMode, Station


AM = RadioMode("AM", 8000, 1000)
NFM = RadioMode("FM", 12000, 5000)
WFM = RadioMode("WFM", 180000, 100000)

stations = [
    Station("NOAA WX 162.550", 162_550_000, NFM),
    Station("Airband Guard", 121_500_000, AM),
    Station("FM 101.1", 101_100_000, WFM),
]

client = RigctlClient(host="127.0.0.1", port=4532)
backend = RigctlBackend(client)

radio = RadioController(backend, stations)

radio.start()
radio.tune_current_station()
radio.frequency_up()