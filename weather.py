#!/usr/local/bin/python3

import requests
from datetime import date, timedelta

with open('metoffice_api_key') as keyfile:
    api_key = keyfile.read()

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
forecast_time = (date.today() + timedelta(1)).isoformat() + 'T00:00:00Z'

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


response = requests.get(
    urls['base'] + urls['forecast'].format(location=location_dicts[0]['code']),
    params={'key': api_key, 'res': 'daily', 'time': forecast_time}
    )
conditions = response.json()['SiteRep']['DV']['Location']['Period']['Rep']
day_forecast = next(f for f in conditions if f['$'] == 'Day')

working_dict = {}
for k, v in day_forecast.items():
    if k == '$':
        continue
    name = forecast_codes[k]['name']
    units = forecast_codes[k]['units']
    if name == 'Weather type':
        working_dict[name] = weather_types[int(v)]
    else:
        working_dict[name] = v + units

weather_template = '''\
{Weather type}
{temp}
Wind {Wind speed} {Wind direction}{precip}'''

temp_string = working_dict['Max temp'] + ' max'
if working_dict['Feels like'] != working_dict['Max temp']:
    temp_string += ', feels like {}'.format(working_dict['Feels like'])

precip_chance = working_dict['Precipitation probability']
if int(precip_chance.replace('%', '')) < 20:
    precip_string = ''
else:
    precip_string = '\n{} chance of rain'.format(precip_chance)

weather_string = weather_template.format(temp=temp_string,
                                         precip=precip_string,
                                         **working_dict)
print(weather_string, '\n')
