import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from collections import defaultdict
from secrets import MG_KEY, MG_DOMAIN
import HTMLParser
import sys

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
body = ''
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

found = 0
for trip in config['trips']:

    start_date = datetime.strptime(trip['start_date'], '%m/%d/%Y')
    days = [start_date + timedelta(days=i) for i in range(trip['length'])]
    day_strs = [day.strftime('%m/%d/%Y') for day in days]

    avail_camps = dict((day_str, defaultdict(list)) for day_str in day_strs)
    unavail_camps = dict((day_str, defaultdict(list)) for day_str in day_strs)

    for park_id in config['park_ids']:
        response = requests.get(REQUEST_URL, params={
            'page': 'matrix',
            'contractCode': 'NRSO',
            'calarvdate': trip['start_date'],
            'parkId': park_id
        })
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
            if site_number.startswith('HRS'):  # horse campsite
                continue

            status_tags = camp.select('.status')
            for day_str, status_tag in zip(day_strs, status_tags):
	        avail = True
                if status_tag.string in UNAVAILABLE_CODES:  # Unavailable
		    avail = False
		else:
		    url_in_mail = ""
		    avail = True
                    try:
		        url_in_mail = BASE_URL + status_tag.find('a')['href']
		    except Exception as e:
		        url_in_mail = site_url
			if status_tag.string != 'C': #Call only sites won't have URL
			    avail = False
	        if avail:
                    avail_camps[day_str][camp_name].append((site_number,
                                 url_in_mail,
                                 AVAILABLE_CODES[status_tag.string]))
                    found += 1
		else:
		    unavail_camps[day_str][camp_name].append(site_number)

    body += TRIP.format(trip['start_date'])
    for day_str, camps in iter(sorted(avail_camps.iteritems())):
        camps_html = '' if camps else 'None'
        for camp_name, sites in camps.iteritems():
            sites_html = '' if sites else 'None'
            for site_number, url, action in sites:
                sites_html += SITE.format(site_number, url, action)
            camps_html += CAMP.format(camp_name, sites_html)
        body += DAY.format(day_str, camps_html)

if not found:
    sys.exit()

with open('style.min.css') as css_file:
    html = HTML.format(css_file.read(), body)

response = requests.post(INLINER_URL, data={
    'returnraw': 'y',
    'source': html
})
h = HTMLParser.HTMLParser()
inlined_html = h.unescape(response.text)

requests.post(MG_URL, auth=('api', MG_KEY), data={
    'from': '"Yosemite Campsite Scraper" <yosemite@schlosser.io>',
    'to': ','.join(config['emails']),
    'subject': 'Found {} camp sites near Yosemite'.format(found),
    'html': inlined_html
})
