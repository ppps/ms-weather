#!/usr/bin/env python3

import subprocess
from datetime import date, timedelta
from multiprocessing.dummy import Pool
import sys

import keyring
import requests
import pendulum

weather_types = {'NA': 'Not available',
                 0: 'Clear night',
                 1: 'Sunny day',
                 2: 'Partly cloudy',        # night
                 3: 'Partly cloudy',        # day
                 4: 'Not used',
                 5: 'Mist',
                 6: 'Fog',
                 7: 'Cloudy',
                 8: 'Overcast',
                 9: 'Light rain shower',    # night
                 10: 'Light rain shower',   # day
                 11: 'Drizzle',
                 12: 'Light rain',
                 13: 'Heavy rain shower',   # night
                 14: 'Heavy rain shower',   # day
                 15: 'Heavy rain',
                 16: 'Sleet shower',        # night
                 17: 'Sleet shower',        # day
                 18: 'Sleet',
                 19: 'Hail shower',         # night
                 20: 'Hail shower',         # day
                 21: 'Hail',
                 22: 'Light snow shower',   # night
                 23: 'Light snow shower',   # day
                 24: 'Light snow',
                 25: 'Heavy snow shower',   # night
                 26: 'Heavy snow shower',   # day
                 27: 'Heavy snow',
                 28: 'Thunder shower',      # night
                 29: 'Thunder shower',      # day
                 30: 'Thunder'}

forecast_codes = {
    'FDm': {'name': 'Feels like',
            'units': '°C'},
    'Dm': {'name': 'Max temp',
           'units': '°C'},
    'Gn': {'name': 'Wind gusts',
           'units': 'mph'},
    'Hn': {'name': 'Humidity',
           'units': '%'},
    'V': {'name': 'Visibility',
          'units': ''},
    'D': {'name': 'Wind direction',
          'units': ''},
    'S': {'name': 'Wind speed',
          'units': 'mph'},
    'U': {'name': 'UV',
          'units': ''},
    'W': {'name': 'Weather type',
          'units': ''},
    'PPd': {'name': 'Precipitation probability',
            'units': '%'},
}

urls = {
    'base': 'http://datapoint.metoffice.gov.uk/public/data/',
    'forecast': 'val/wxfcs/all/json/{location}',
    'summary': 'txt/wxfcs/regionalforecast/json/{location}',
    }

location_tuples = (
    ('Aberdeen', 310170),
    ('Birmingham', 310002),
    ('Cardiff', 350758),
    ('Edinburgh', 351351),
    ('Glasgow', 310009),
    ('Inverness', 320002),
    ('Liverpool', 310012),
    ('London', 352409),
    ('Manchester', 310013),
    ('Newcastle', 352793),
    ('Norwich', 310115),
    ('Plymouth', 310016),
    ('Sheffield', 353467),
    ('Southampton', 353595),
    )

location_dicts = [{'name': a, 'code': b} for a, b in location_tuples]


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


def get_api_key(*, service='darksky', username='ppps'):
    """Get the Dark Sky API key from the system keychain

    Expects the key to be saved for the 'darksky' service
    with the username 'ppps'.

    If the key does not exist in the keychain, it prompts
    the user to enter it and saves it in the keychain.
    """
    key = keyring.get_password(service, username)
    if key is None:
        print(
            'API key is not saved in the keychain, please enter it.',
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
    return response.json()


def fetch_forecast(location_code, target_date):
    url = urls['base'] + urls['forecast'].format(location=location_code)
    params = {'key': api_key,
              'res': 'daily',
              'time': target_date}
    response = requests.request('GET', url, params=params)
    conditions = response.json()['SiteRep']['DV']['Location']['Period']['Rep']
    day_forecast = next(f for f in conditions if f['$'] == 'Day')
    return day_forecast


def parse_forecast(forecast):
    working_dict = {}
    for k, v in forecast.items():
        if k == '$':
            continue
        name = forecast_codes[k]['name']
        units = forecast_codes[k]['units']
        if name == 'Weather type':
            working_dict[name] = weather_types[int(v)]
        else:
            working_dict[name] = v + units
    return working_dict


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


def date_string(d):
    return d.isoformat() + 'T00:00:00Z'


def fetch_uk_outlook():
    url = urls['base'] + urls['summary'].format(location=515)
    params = {'key': api_key}
    response = requests.request('GET', url, params=params)
    periods = response.json()['RegionalFcst']['FcstPeriods']['Period']
    summary_dict = next(p for p in periods if p['id'] == 'day3to5')
    outlook = summary_dict['Paragraph']['$']
    return outlook


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
