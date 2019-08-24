#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen
from urllib.error import HTTPError

api_key = Path(__file__).with_name('metoffice_api_key').read_text().rstrip()

def fetch_uk_outlook():
    outlook_url = ('http://datapoint.metoffice.gov.uk/public/data/txt/'
                   'wxfcs/regionalforecast/json/515')
    params = {'key': api_key}

    try:
        request_url = outlook_url + '?' + urlencode(params)
        response = urlopen(outlook_url + '?' + urlencode(params))
        payload = json.loads(response.read().decode('utf-8'))
        periods = payload['RegionalFcst']['FcstPeriods']['Period']
        return periods
    except HTTPError as exc:
        print("ERROR: Problem with HTTP request to MetOffice API.")
        print(f"Request URL was: {request_url}")
        print("Exception was:")
        print(exc)


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


if __name__ == '__main__':
    outlook_text = fetch_uk_outlook()
    day2 = outlook_text[0]['Paragraph'][2]['$']
    outlook_obj = [p for p in outlook_text
                   if p['id'] == 'day3to5']
    day3to5 = outlook_obj[0]['Paragraph']['$']
    set_frame_contents('Weather-Today', day2)
    set_frame_contents('Weather-Outlook', day3to5)
