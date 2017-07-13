#!/usr/bin/env python

# Add the parent directory to the PYTHONPATH. Relative imports won't
# work as this isn't a module.
import os,sys
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from service import flask_app as app

mongo = app.config['MONGO'].govuk_delivery
redis = app.config['REDIS']
repository = app.config['PARTNER_ID_REPOSITORY'](mongo.topics)

for key in redis.keys('https://*.uk/government/*'):
    if not repository.find_partner_id_for_url(key):
        repository.store_partner_id_for_url(key, redis.get(key))
        print('Stored %s' % key)
    else:
        print('Already exists: %s' % key)
