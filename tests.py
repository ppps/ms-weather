import json
import unittest
from unittest import mock

import pendulum
import keyring

import weather


with open('test_forecasts.json') as json_file:
    TEST_JSON = json.load(json_file)


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

    def test_default_one(self):
        """By default next_days returns one forecast"""
        self.assertEqual(
            len(weather.next_days(forecast_data=TEST_JSON,
                                  date=self.pretend_tomorrow)),
            1
            )

    def test_two(self):
        """next_days returns two forecasts when num_days=2"""
        self.assertEqual(
            len(weather.next_days(forecast_data=TEST_JSON,
                                  date=self.pretend_tomorrow,
                                  num_days=2)),
            2
            )

    def test_default_tomorrow(self):
        """By default next_days returns one forecast, for date + 1 day"""
        result_data = weather.next_days(forecast_data=TEST_JSON,
                                        date=self.pretend_tomorrow)[0]
        parsed_result_date = pendulum.from_timestamp(result_data['time'])
        self.assertEqual(self.pretend_tomorrow, parsed_result_date)

    def test_tomorrow_and_next_day(self):
        """next_days returns date + 1 and date + 2 when num_days = 2"""
        result_data = weather.next_days(forecast_data=TEST_JSON,
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
            weather.next_days(forecast_data=TEST_JSON,
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


class TestMakeDarkSkyRequest(unittest.TestCase):
    """Test the make_dark_sky_request function

    This function makes the call to the Dark Sky API, and should
    appropriately set the API key, lat, lon and other options.

    It should return the JSON of the API response, or None if for
    whatever reason the server is not available or retrieving the
    JSON from the response fails for whatever reason.
    """
    def setUp(self):
        self.get_args = dict(api_key='fake-api-key',
                             latitude=1,
                             longitude=2)

    def test_url_and_params(self):
        """Function uses correct API URL with correct args and params"""
        with mock.patch('weather.requests.get') as mock_get:
            weather.make_dark_sky_request(**self.get_args)

        mock_get.assert_called_with(
            url='https://api.darksky.net/forecast/fake-api-key/1,2',
            params={
                'exclude': 'currently,minutely,hourly',
                'lang': 'en',
                'units': 'uk2'
                }
            )

    def test_returns_expected_json_ok(self):
        """Function returns expected json when the call proceeds OK"""
        with mock.patch('weather.requests.get') as mock_get:
            mock_get.return_value.json.return_value = TEST_JSON
            result = weather.make_dark_sky_request(**self.get_args)
        self.assertEqual(result, TEST_JSON)

    def test_returns_None_on_HTTP_failure(self):
        """If the HTTP response is not OK return None"""
        with mock.patch('weather.requests.get') as mock_get:
            mock_get.return_value.ok = False
            result = weather.make_dark_sky_request(**self.get_args)
        self.assertIsNone(result)

    def test_resturns_None_on_json_parse_failure(self):
        """Function returns None when it fails to parse JSON"""
        with mock.patch('weather.requests.get') as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.json.side_effect = (
                json.decoder.JSONDecodeError(
                    'Expecting value', '<html></html>', 0))
            result = weather.make_dark_sky_request(**self.get_args)
        self.assertIsNone(result)


class TestWeatherString(unittest.TestCase):
    """Test the create_weather_string function"""

    def test_summary_max(self):
        """Returns forecast summary followed by maximum temperature

        Maximum temperature should be rounded to the nearest integer.
        """
        expected = 'Drizzle starting in the afternoon. Max 22°C.'
        result = weather.create_weather_string(TEST_JSON['daily']['data'][0])
        self.assertEqual(expected, result)


class TestMetOfficeSummary(unittest.TestCase):
    """Test the function that retrieves the Met Office UK text summary"""
    def setUp(self):
        self.api_key = 'fake-api-key'
        with open('test_summary.xml', 'rb') as xml_file:
            self.test_xml_bytes = xml_file.read()

    def test_url_and_params(self):
        """Function uses correct API URL with correct args and params"""
        with mock.patch('weather.requests.get') as mock_get:
            mock_get.return_value.content = self.test_xml_bytes
            weather.met_office_fetch_uk_outlook(self.api_key)

        mock_get.assert_called_with(
            url=('http://datapoint.metoffice.gov.uk/public/data/'
                 'txt/wxfcs/regionalforecast/xml/515'),
            params={
                'key': self.api_key
                }
            )

    def test_returns_expected_summary_ok(self):
        """Function returns expected summary text when call proceeds OK"""
        with mock.patch('weather.requests.get') as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.content = self.test_xml_bytes
            result = weather.met_office_fetch_uk_outlook(self.api_key)
        self.assertEqual(
            result,
            ('Fine start, but rain in the NW moving slowly SE across the UK. '
             'Becoming very warm ahead of this, with risk of thunderstorms. '
             'Clearing to sunshine and showers by Saturday.')
            )

    def test_resturns_None_on_HTTP_failure(self):
        """Function returns None when HTTP response is not OK"""
        with mock.patch('weather.requests.get') as mock_get:
            mock_get.return_value.ok = False
            result = weather.met_office_fetch_uk_outlook(self.api_key)
        self.assertIsNone(result)

    def test_resturns_None_on_xml_parse_failure(self):
        """Function returns None when it fails to parse XML"""
        with mock.patch('weather.requests.get') as mock_get:
            mock_get.return_value.ok = True
            mock_get.return_value.content = b''
            result = weather.met_office_fetch_uk_outlook(self.api_key)
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main(verbosity=2)
