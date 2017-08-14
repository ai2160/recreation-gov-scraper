#!/usr/bin/python
import json
import requests
import re
from pprint import pprint
import urllib
from mechanize import Browser
import xml.etree.ElementTree as ET
import HTMLParser
from bs4 import BeautifulSoup
import urlparse

import sys
import time
import logging

config = None
with open('campsite_names.json') as config_file:
    config = json.loads(config_file.read())

def scrape_info():
	browser = Browser()
	browser.set_handle_robots(False)
	browser.addheaders = [('User-agent', 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.1) Gecko/2008071615 Fedora/3.0.1-1.fc9 Firefox/3.0.1')]

	parkIds = []
	for name in config['names']:
		browser.open("https://www.recreation.gov")
		browser.select_form(nr=0)
		browser['locationCriteria'] = name

		response = browser.submit()
		content = response.read()

		soup = BeautifulSoup(content, 'html.parser')
		scripts = soup.select('script')
		for script in scripts:
			if 'SuggestedPlaces' in str(script):
				jsonStr = str(script).strip('<script>var SuggestedPlaces = ').strip(';</script>')
				places = json.loads(jsonStr)
				query = urlparse.parse_qs(places[0]['value'])
				if 'parkId' in query:
					print('FOUND!: ' + unicode(query['parkId'][0]))
					parkIds.append(unicode(query['parkId'][0]))
				else:
					print('No results for ' + name + ': ' + places[0]['value'])

	pprint(parkIds)

if __name__ == '__main__':
	scrape_info()
