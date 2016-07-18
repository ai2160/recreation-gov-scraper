from datetime import datetime
from datetime import timedelta
import time
import json

start = datetime(2016, 7, 20)
end = datetime(2016, 10, 1)
delta = timedelta(days=1)
d = start

jobj = {}
jobj['park_ids'] = ['72393']
jobj['emails'] = ['abhilash.i@gmail.com']
jobj['trips'] = []

while d <= end:
  if d.weekday() != 5:
    d += delta
    continue
  trip = {}
  trip['start_date'] = d.strftime("%m/%d/%Y")
  trip['length'] = 1
  jobj['trips'].append(trip)
  d += delta

print(json.dumps(jobj, sort_keys=True, indent=4))
