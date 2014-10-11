#!/usr/local/bin/python3

import requests
from datetime import date, timedelta

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

location_tuples = (('Aberdeen', 310170),
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

metoffice_urls = {'base': 'http://datapoint.metoffice.gov.uk/public/data/',
                  'forecast': 'val/wxfcs/all/json/{location}',
                  'summary': 'txt/wxfcs/regionalforecast/json/{location}',
                  }

with open('metoffice_api_key') as keyfile:
    api_key = keyfile.read()

capabilities_URL = ('http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/'
                    'all/json/capabilities?res=3hourly&key=' + api_key)

# print(requests.get(capabilities_URL).text)
print(LOCATION_TUPLES)
