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

    def test_nonmidnight_date(self):
        """next_days should handle `date` that is not midnight

        Midnight is important because all of the Dark Sky timestamps
        are at midnight (0000) of the day for which the forecast
        data is for.

        `date` with a non-midnight time should be properly reduced
        to midnight.
        """
        dirty_date = pendulum.create(2017, 5, 30, 1, 2, 3,
                                     tz='Europe/London')
        self.assertTrue(
            weather.next_days(forecast_data=self.test_json,
                                  date=dirty_date)
            )


class TestWindDirection(unittest.TestCase):
    """Test the wind_direction utility function

    wind_direction(origin_degrees) should return a human-readable
    approximate direction string such as N or NE (but not ENE).
    """

    def test_north(self):
        result_set = (
            {weather.wind_direction(x) for x in range(338, 361)} |
            {weather.wind_direction(x) for x in range(0, 23)}
            )
        self.assertEqual(len(result_set), 1)
        self.assertIn('N', result_set)

    def test_north_east(self):
        result_set = {weather.wind_direction(x) for x in range(23, 68)}
        self.assertEqual(len(result_set), 1)
        self.assertIn('NE', result_set)

    def test_east(self):
        result_set = {weather.wind_direction(x) for x in range(68, 113)}
        self.assertEqual(len(result_set), 1)
        self.assertIn('E', result_set)

    def test_south_east(self):
        result_set = {weather.wind_direction(x) for x in range(113, 158)}
        self.assertEqual(len(result_set), 1)
        self.assertIn('SE', result_set)

    def test_south(self):
        result_set = {weather.wind_direction(x) for x in range(158, 203)}
        self.assertEqual(len(result_set), 1)
        self.assertIn('S', result_set)

    def test_south_west(self):
        result_set = {weather.wind_direction(x) for x in range(203, 248)}
        self.assertEqual(len(result_set), 1)
        self.assertIn('SW', result_set)

    def test_west(self):
        result_set = {weather.wind_direction(x) for x in range(248, 293)}
        self.assertEqual(len(result_set), 1)
        self.assertIn('W', result_set)

    def test_north_west(self):
        result_set = {weather.wind_direction(x) for x in range(293, 338)}
        self.assertEqual(len(result_set), 1)
        self.assertIn('NW', result_set)
