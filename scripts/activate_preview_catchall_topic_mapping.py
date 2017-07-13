#!/usr/bin/env python

# Add the parent directory to the PYTHONPATH. Relative imports won't
# work as this isn't a module.
import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from service import flask_app as app
import datetime

mongo = app.config["MONGO"]
db = mongo.govuk_delivery

db.topics.insert({
  '_id': 'https://www.preview.alphagov.co.uk/government/feed',
  'topic_id': 'UKGOVUK_521',
  'created': datetime.datetime.utcnow()
})
