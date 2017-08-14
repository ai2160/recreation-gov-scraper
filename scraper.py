#!/usr/bin/python
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from collections import defaultdict
from secrets import MG_KEY, MG_DOMAIN
import HTMLParser
import sys
import time
import logging

global body

found_sites = []
FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logger = logging.getLogger(__name__)

BASE_URL = 'http://www.recreation.gov'
REQUEST_URL = BASE_URL + '/campsiteCalendar.do'
MG_URL = 'https://api.mailgun.net/v3/{}/messages'.format(MG_DOMAIN)
INLINER_URL = 'https://inlinestyler.torchbox.com/styler/convert/'
UNAVAILABLE_CODES = set(['X', 'R', 'N', 'a'])
AVAILABLE_CODES = {'A' : 'Reserve', 'W' : 'Walk-up', 'C' : 'Call', 'L' : 'In Lottery'}

config = None
with open('config.json') as config_file:
    config = json.loads(config_file.read())

HTML = '''
<style>{}</style>{}
'''
TRIP = '''<h2>Trip on {}</h2>
'''
DAY = '''<h4>{}</h4>
<ul>
{}
</ul>
'''
CAMP = '''<li>
<h5>{}</h5>
<ul>
{}
</ul>
</li>
'''
SITE = '<li>{} (<a href="{}">{}</a>)</li>'

def valid_site(name):
    name = name.upper()
    if name.startswith('HRS'):
       return False
    if name.startswith('RV'):
       return False
    if name.startswith('BOAT'):
       return False
    if name.find('GROUP') != -1:
       return False
    if name.find('LG') != -1:
       return False
    return True

def scrape_info():
    found = 0
    for trip in config['trips']:
        start_date = datetime.strptime(trip['start_date'], '%m/%d/%Y')
        days = [start_date + timedelta(days=i) for i in range(trip['length'])]
        day_strs = [day.strftime('%m/%d/%Y') for day in days]

        avail_camps = dict((day_str, defaultdict(list)) for day_str in day_strs)
        unavail_camps = dict((day_str, defaultdict(list)) for day_str in day_strs)

        for park_id in config['park_ids']:
	    payload = {
                'page': 'matrix',
                'contractCode': 'NRSO',
                'calarvdate': trip['start_date'],
                'parkId': park_id
	    }
            payload_str = '&'.join("%s=%s" % (k,v) for k,v in payload.items())
            response = requests.get(REQUEST_URL, params=payload_str)

            if not response.ok:
                print "Request failed for park {} on {}".format(park_id,
                                                                trip['start_date'])
                continue

            soup = BeautifulSoup(response.text, 'html.parser')
            camp_name = soup.find(id='cgroundName').string
            calendar_body = soup.select('#calendar tbody')[0]
            camps = calendar_body.find_all('tr', attrs={'class': None})

            for camp in camps:
                site_number_tag = camp.select('.siteListLabel a')[0]
                site_number = site_number_tag.string
                site_url = BASE_URL + site_number_tag['href']
    	        site_loop = camp.find('div', attrs={'class': 'loopName'}).text

    	        if not valid_site(site_number):
    	            continue

                if not valid_site(site_loop):
    	            continue

                status_tags = camp.select('.status')
                for day_str, status_tag in zip(day_strs, status_tags):
        	    avail = False
                    if (park_id, site_number, day_str) in found_sites:
                        print "\n\n\nAlready notified for this site ({}, {}, {})!!\n\n\n".format(park_id, site_number, day_str)
                        continue

        	    if status_tag.text[0] in AVAILABLE_CODES:
    		        url_in_mail = ""
			avail = True
                        try:
    		            url_in_mail = BASE_URL + status_tag.find('a')['href']
    		        except Exception as e:
    		            url_in_mail = site_url
    			    if status_tag.text[0] != 'C': #Call only sites won't have URL
    			        avail = False
    	            if avail:
                        avail_camps[day_str][camp_name].append((site_number,
                                     url_in_mail,
                                     AVAILABLE_CODES[status_tag.text[0]]))
                        found += 1
                        found_sites.append((park_id, site_number, day_str))
    		    else:
    		        unavail_camps[day_str][camp_name].append(site_number)

	global body
        body += TRIP.format(trip['start_date'])
        for day_str, camps in iter(sorted(avail_camps.iteritems())):
            camps_html = '' if camps else 'None'
            for camp_name, sites in camps.iteritems():
                sites_html = '' if sites else 'None'
                for site_number, url, action in sites:
                    sites_html += SITE.format(site_number, url, action)
                camps_html += CAMP.format(camp_name, sites_html)
            body += DAY.format(day_str, camps_html)

    return found

def send_email():
    with open('style.min.css') as css_file:
        html = HTML.format(css_file.read(), body)

    response = requests.post(INLINER_URL, data={
        'returnraw': 'y',
        'source': html
    })
    h = HTMLParser.HTMLParser()
    inlined_html = h.unescape(response.text)
    requests.post(MG_URL, auth=('api', MG_KEY), data={
        'from': '"Campsite Scraper" <camper@westerncamperphoto.com>',
        'to': ','.join(config['emails']),
        'subject': 'Found {} camp sites!'.format(found),
        'html': inlined_html
    })

if __name__ == '__main__':
    while 1:
       global body
       body = ''
       found = None

       try:
          found = scrape_info()
       except Exception as e:
          logger.error("Exception occured:\n%s" % e.args)

       if found:
          logger.info('Found some campsites')
          send_email()
       else:
          logger.info('No campsites found')
       time.sleep(300)
