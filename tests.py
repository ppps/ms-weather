import json
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

    These tests requires that ppps:darksky and ppps:metoffice
    be set in the system keychain (to any value).
    """
    def setUp(self):
        ds_key = keyring.get_password('darksky', 'ppps')
        if ds_key is None:
            raise unittest.SkipTest(
                'Dark Sky API key is not set in keychain')
        else:
            self.ds_api_key = ds_key

        met_key = keyring.get_password('metoffice', 'ppps')
        if met_key is None:
            raise unittest.SkipTest(
                'Met Office API key is not set in keychain')
        else:
            self.met_api_key = met_key

    def test_darksky_matches_keychain(self):
        """Dark Sky key returned from weather module matches keychain"""
        self.assertEqual(
            weather.get_api_key(service='darksky'),
            self.ds_api_key
            )

    def test_metoffice_matches_keychain(self):
        """Met Office key returned from weather module matches keychain"""
        self.assertEqual(
            weather.get_api_key(service='metoffice'),
            self.met_api_key
            )


class TestLocationsDict(unittest.TestCase):
    """Test the locations_lat_lon dictionary"""

    def test_expected_format(self):
        """The dict items are tuples containing two floats"""
        for lat, lon in weather.locations_lat_lon.values():
            self.assertIsInstance(lat, float)
            self.assertIsInstance(lon, float)


class TestNextDaysForecasts(unittest.TestCase):
    """Test next_days_forecasts function

    next_days(forecast_json: dict, date: datetime, num_days: int)
    should return the next `num_days` number of forecasts, starting
    with tomorrow.

    For example, given next_days(days=2):
        [
            <data for tomorow>,
            <data for tomorrow + 1>
        ]
    """
    def setUp(self):
        # test_forecasts.json has a set of daily forecasts
        # starting from 2017-05-30
        self.pretend_tomorrow = pendulum.create(2017, 5, 30,
                                                tz='Europe/London')
        with open('test_forecasts.json') as json_file:
            self.test_json = json.load(json_file)

    def test_default_one(self):
        """By default next_days returns one forecast"""
        self.assertEqual(
            len(weather.next_days(forecast_data=self.test_json,
                                  date=self.pretend_tomorrow)),
            1
            )

    def test_two(self):
        """next_days returns two forecasts when num_days=2"""
        self.assertEqual(
            len(weather.next_days(forecast_data=self.test_json,
                                  date=self.pretend_tomorrow,
                                  num_days=2)),
            2
            )

    def test_default_tomorrow(self):
        """By default next_days returns one forecast, for date + 1 day"""
        result_data = weather.next_days(forecast_data=self.test_json,
                                        date=self.pretend_tomorrow)[0]
        parsed_result_date = pendulum.from_timestamp(result_data['time'])
        self.assertEqual(self.pretend_tomorrow, parsed_result_date)

    def test_tomorrow_and_next_day(self):
        """next_days returns date + 1 and date + 2 when num_days = 2"""
        result_data = weather.next_days(forecast_data=self.test_json,
                                        date=self.pretend_tomorrow,
                                        num_days=2)
        for adjust, data in enumerate(result_data):
            self.assertEqual(
                self.pretend_tomorrow.add(days=adjust),
                pendulum.from_timestamp(data['time']))
