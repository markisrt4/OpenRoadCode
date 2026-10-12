# SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
# SPDX-License-Identifier: MIT

import sqlite3
import tempfile
import unittest
from pathlib import Path
from controllers.navigation.sqlite_geocoder import SqliteGeocoder, _normalize_street, _parse_query


class MileRoadGeocodingTest(unittest.TestCase):
    def test_numbered_mile_aliases_keep_other_street_names_distinct(self):
        self.assertEqual(_normalize_street("E 11 Mile Rd"),
                         _normalize_street("East Eleven Mile Road"))
        self.assertNotEqual(_normalize_street("Eleven Oaks Road"),
                            _normalize_street("11 Oaks Road"))

    def test_street_lookup_fetches_spelled_out_mile_name(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "search.sqlite"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE street(id TEXT, name TEXT, city TEXT, state TEXT, postcode TEXT, latitude REAL, longitude REAL)")
            connection.execute("INSERT INTO street VALUES('s1','East Eleven Mile Road','Warren','MI',NULL,42.5,-83.0)")
            connection.commit()
            connection.close()
            geocoder = SqliteGeocoder(path)
            try:
                rows = geocoder._street_results(_parse_query("123 E 11 Mile Rd Warren MI"), 5)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].source, "street")
            finally:
                geocoder.close()

    def test_exact_address_accepts_numbered_mile_alias(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "search.sqlite"
            connection = sqlite3.connect(path)
            connection.execute("CREATE TABLE address(id TEXT, house_number TEXT, street TEXT, unit TEXT, city TEXT, state TEXT, postcode TEXT, country TEXT, latitude REAL, longitude REAL)")
            connection.execute("INSERT INTO address VALUES('a1','123','East Eleven Mile Road',NULL,'Warren','MI',NULL,'US',42.5,-83.0)")
            connection.execute("INSERT INTO address VALUES('a2','123','East Eleven Mile Road',NULL,'Roseville','MI',NULL,'US',42.5,-82.9)")
            connection.commit()
            connection.close()
            geocoder = SqliteGeocoder(path)
            try:
                rows = geocoder._address_results(_parse_query("123 E 11 Mile Rd Warren MI"), 5)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0].source, "address")
            finally:
                geocoder.close()
