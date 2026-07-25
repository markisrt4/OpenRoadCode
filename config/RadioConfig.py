import json


class RadioConfig:
    datastore = None  # type: object

    # Reads the the user defined configuration file.  The configuration file provides frequency ranges and
    # demodulation modes for easy switching. The idea is to be able to switch between FM radio, police band,
    # ham bands, etc.

    def __init__(self):
        # Nothing to do here
        return

    def load(self, fileName):
        # Read JSON data into the datastore variable
        with open(fileName) as json_data:
            self.datastore = json.load(json_data)
        return self.datastore

    def numRecords(self):
        """Return the number of loaded radio records."""
        return len(self.datastore["radio_config"]["stations"])
