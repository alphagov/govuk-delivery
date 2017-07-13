#!/usr/bin/env python

import logging
import os
import sys
import urlparse
from pymongo.errors import DuplicateKeyError

# Add the parent directory to the PYTHONPATH. This is to get the tests passing
# and script to run without having to restructure the entire application
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from service import flask_app as app

logging.basicConfig(level=logging.INFO)

db = app.config['MONGO'].govuk_delivery


def build_new_url(old_url, new_domain):
    parsed = urlparse.urlparse(old_url)
    new_params = (parsed.scheme, new_domain, parsed.path, parsed.params, parsed.query, parsed.fragment)
    return urlparse.urlunparse(new_params)


def build_new_topic_id(topic_id, account_code):
    return topic_id.replace('UKGOVUK_', account_code + '_')


def update_record(record, new_domain, account_code):
    old_record_id = record['_id']
    new_url = build_new_url(old_record_id, new_domain)
    new_topic_id = build_new_topic_id(record['topic_id'], account_code)

    # We can't modify the _id, so delete the old record and create a new one
    db.topics.remove({'_id': old_record_id})
    try:
        data = {
            '_id'      : new_url,
            'topic_id' : new_topic_id,
            'created'  : record['created']
        }
        if record.has_key('disabled'):
            data['disabled'] = record['disabled']
        db.topics.insert(data)
    except DuplicateKeyError:
        # I got this consistently for 82 records out of 11403 in dev, even
        # though there were no actual duplicates being created. Moving the
        # remove to before the insert appears to have stopped that. Oh, mongo.
        logging.warning(
            'DuplicateKeyError: Could not create new record for topic_id %s with _id %s' % (record['topic_id'], new_url)
        )


def update_all_records():
    new_domain = urlparse.urlparse(os.environ['GOVUK_WEBSITE_ROOT']).netloc
    account_code = app.config['GOVDELIVERY_ACCOUNT_CODE']

    if app.config['GOVDELIVERY_HOSTNAME'] != 'stage-api.govdelivery.com':
        logging.warning('This script must not be run in production')
        sys.exit(1)
    else:
        logging.info('Updating %s topics with domain %s and account code %s' % (db.topics.count(), new_domain, account_code))
        for topic in db.topics.find():
            update_record(topic, new_domain, account_code)
        logging.info('Done')


if __name__ == '__main__':
    update_all_records()
