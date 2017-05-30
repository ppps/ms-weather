#!/usr/bin/env python3

import subprocess
from datetime import date, timedelta
from multiprocessing.dummy import Pool
import sys
import getpass


from bs4 import BeautifulSoup
import keyring
import pendulum
import requests


locations_lat_lon = {
    'Aberdeen':     (57.1526,   -2.11),
    'Birmingham':   (52.483056, -1.893611),
    'Cardiff':      (51.483333, -3.183333),
    'Edinburgh':    (55.953056, -3.188889),
    'Glasgow':      (55.858,    -4.259),
    'Inverness':    (57.4718,   -4.2254),
    'Liverpool':    (53.4,      -2.983333),
    'London':       (51.507222, -0.1275),
    'Manchester':   (53.466667, -2.233333),
    'Newcastle':    (54.972222, -1.608333),
    'Norwich':      (52.6,       1.3),
    'Plymouth':     (50.371389, -4.142222),
    'Sheffield':    (53.383611, -1.466944),
    'Southampton':  (50.9,      -1.4),
    }


def get_api_key(*, service, username='ppps'):
    """Get the Dark Sky API key from the system keychain

    Expects the key to be saved for the 'darksky' service
    with the username 'ppps'.

    If the key does not exist in the keychain, it prompts
    the user to enter it and saves it in the keychain.
    """
    key = keyring.get_password(service, username)
    if key is None:
        print(
            (f'{service} API key is not saved in the keychain, '
             'please enter it.'),
            file=sys.stderr)
        try:
            key = getpass.getpass(prompt='API key: ')
            keyring.set_password(service, username, key)
        except KeyboardInterrupt:
            sys.exit(1)
    return key


def parse_lastmodified(date_string):
    """Parse dates matching the Last-Modified HTTP header format

    Example:
        Mon, 29 May 2017 19:00:29 GMT
    Is parsed as:
        2017-05-29T19:00:29+0000
    """
    # Replace GMT with UTC as dateutil misinterprets GMT as Europe/London
    # if you’re in that timezone. See:
    # https://github.com/dateutil/dateutil/issues/370
    date_string = date_string.replace('GMT', 'UTC')
    return pendulum.parse(date_string)


def make_dark_sky_request(*, api_key, latitude, longitude):
    """Fetch the Dark Sky forecast

    The requested forecast includes only the daily forecasts,
    alerts and flags. It is requested in English using UK units.
    """
    ds_url = 'https://api.darksky.net/forecast/{key}/{lat},{lon}'
    query_params = {
        'exclude': ','.join(['currently', 'minutely', 'hourly']),
        'lang': 'en',
        'units': 'uk2'
        }
    response = requests.get(
        url=ds_url.format(key=api_key, lat=latitude, lon=longitude),
        params=query_params
        )
    if response.ok:
        return response.json()
    else:
        return None


def next_days(forecast_data, date, num_days=1):
    """Extract daily forecasts starting from date for `num_days`"""
    dailies = forecast_data['daily']['data']
    # Ensure daily forecasts sorted in chronological order
    dailies.sort(key=lambda d: d['time'])

    # Ensure date is at midnight (to match Dark Sky daily timestamps)
    date = date.at(0, 0, 0)
    date_range = pendulum.period(date, date.add(days=num_days - 1))
    selected_forecasts = [
        f for f in dailies
        if pendulum.from_timestamp(f['time']) in date_range
        ]
    return selected_forecasts


def create_weather_string(forecast):
    """Parse forecast dictionary into a human-readable string

    Returned string is the forecast’s human-readable summary following
    the maximum temperature for that day.
    """
    temp = round(forecast['temperatureMax'])
    summary = forecast['summary']
    return f'{summary} Max {temp}°C.'


def wind_direction(origin_degrees):
    """Produce human-readable compass direction from degrees

    This produces a rough human-readable approxmiation of the
    wind direction, such as N or NE, but not (eg) ENE.
    """
    deg = origin_degrees % 360
    if (337.5 <= deg <= 360 or
            0 <= deg < 22.5):
        return 'N'
    elif 22.5 <= deg < 67.5:
        return 'NE'
    elif 67.5 <= deg < 112.5:
        return 'E'
    elif 112.5 <= deg < 157.5:
        return 'SE'
    elif 157.5 <= deg < 202.5:
        return 'S'
    elif 202.5 <= deg < 247.5:
        return 'SW'
    elif 247.5 <= deg < 292.5:
        return 'W'
    elif 292.5 <= deg < 337.5:
        return 'NW'


def build_weather_string(parsed_dict):
    weather_template = '''\
{Weather type}
{temp}
Wind {Wind speed} {Wind direction}{precip}'''
    temp_string = parsed_dict['Max temp'] + ' max'
    if parsed_dict['Feels like'] != parsed_dict['Max temp']:
        temp_string += ', feels like {}'.format(parsed_dict['Feels like'])

    precip_chance = parsed_dict['Precipitation probability']
    if int(precip_chance.replace('%', '')) < 20:
        precip_string = ''
    else:
        precip_string = '\n{} chance of rain'.format(precip_chance)

    weather_string = weather_template.format(temp=temp_string,
                                             precip=precip_string,
                                             **parsed_dict)
    return weather_string


def add_daily_forecast_to_dict(location, forecast_date):
    raw_forecast = fetch_forecast(location['code'], forecast_date)
    parsed = parse_forecast(raw_forecast)
    location[forecast_date] = build_weather_string(parsed)


def met_office_fetch_uk_outlook(api_key):
    url = ('http://datapoint.metoffice.gov.uk/public/data/'
           'txt/wxfcs/regionalforecast/xml/{location}'
           ).format(location=515)
    response = requests.get(url, params={'key': api_key})
    soup = BeautifulSoup(response.content, 'xml')
    return(soup.find(id='day3to5').string)


def asrun(ascript):
    "Run the given AppleScript and return the standard output and error."
    osa = subprocess.Popen(['osascript', '-'],
                           stdin=subprocess.PIPE,
                           stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL)
    return osa.communicate(ascript)[0]


def set_frame_contents(frame_name, text):
    script = '''\
tell application "Adobe InDesign CS4"
\ttell the front document
\t\tset the contents of text frame "{frame}" to "{contents}"
\tend tell
end tell
'''
    asrun(script.format(frame=frame_name, contents=text).encode())


def most_common_condition():
    conditions = [loc[dt].split('\n')[0]
                  for loc in location_dicts
                  for dt in date_list]
    counted = set((conditions.count(c), c) for c in conditions)
    return max(counted)[1]


if __name__ == '__main__':
    outlook_text = fetch_uk_outlook()

    today = date.today()
    date_list = [date_string(today + timedelta(1))]
    if today.weekday() == 4:    # today is Friday
        date_list.append(date_string(today + timedelta(2)))

#     for dt in date_list:
#         for loc in location_dicts:
#             parsed = parse_forecast(fetch_forecast(loc['code'], dt))
#             loc[dt] = build_weather_string(parsed)

    with Pool() as pool:
        pool.starmap(
            add_daily_forecast_to_dict,
            [(loc, dt) for loc in location_dicts for dt in date_list]
            )

    for loc in location_dicts:
        set_frame_contents(loc['name'], loc[date_list[0]])
        if len(date_list) == 2:
            set_frame_contents(loc['name'] + '_Sun', loc[date_list[1]])

    set_frame_contents('Outlook', outlook_text)
