import unittest

import pendulum
import keyring

import weather


class TestConvertLastModifiedDate(unittest.TestCase):
    """Test utility that parses a HTTP last-modified date"""

    def test_basic(self):
        dt = pendulum.create(2017, 5, 29, 20, 51, tz='UTC')
        string = 'Mon, 29 May 2017 20:51:00 GMT'
        self.assertEqual(
            dt,
            weather.parse_lastmodified(string)
            )


class TestGetAPIKey(unittest.TestCase):
    """get_api_key should return the API key

    This test requires that ppps:darksky be set in the
    system keychain (to any value).
    """
    def setUp(self):
        key = keyring.get_password('darksky', 'ppps')
        if key is None:
            raise unittest.SkipTest('API key is not set in keychain')
        else:
            self.api_key = key

    def test_matches_keychain(self):
        """API key returned from weather module matches keychain"""
        self.assertEqual(
            weather.get_api_key(),
            self.api_key
            )


class TestLocationsDict(unittest.TestCase):
    """Test the locations_lat_lon dictionary"""

    def test_expected_format(self):
        """The dict items are tuples containing two floats"""
        for lat, lon in weather.locations_lat_lon.values():
            self.assertIsInstance(lat, float)
            self.assertIsInstance(lon, float)
