#!/usr/bin/env python

import datetime
import os,sys
import logging
from multiprocessing.dummy import Pool

# Add the parent directory to the PYTHONPATH. This is to get the tests passing
# and script to run without having to restructure the entire application
parentdir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0,parentdir)

from service import flask_app as app

logging.basicConfig(level=logging.WARNING, format='(%(threadName)-10s) %(message)s')

gov_delivery_config = {
    'username': app.config['GOVDELIVERY_USERNAME'],
    'password': app.config['GOVDELIVERY_PASSWORD'],
    'account_code': app.config['GOVDELIVERY_ACCOUNT_CODE'],
    'hostname': app.config['GOVDELIVERY_HOSTNAME'],
}

delivery_partner = app.config['GOVDELIVERY_CLIENT_OBJECT'](**gov_delivery_config)
db = app.config['MONGO'].govuk_delivery


def get_topic_count(record):
    topic_id = record.get('topic_id')

    try:
        topic = delivery_partner.read_topic(topic_id)
        subscribers = int(topic['topic']['subscribers-count']['#text'])
        if subscribers:
            sys.stdout.write('-')
        else:
            sys.stdout.write('0')
    # as GovDelivery raises an `Exception` when the record can't be found
    # when an other error occurs we can't be 100% sure this is a missing record.
    # As a result error responses are logged, but not scheduled for deletion
    except Exception as e:
        if e.message == 'HTTP status: 404\nGD-14002\nTopic not found':
            sys.stdout.write('m')
            subscribers = 'topic not found'
        else:
            sys.stdout.write('e')
            subscribers = None

    sys.stdout.flush()
    return (subscribers, record)


def delete_topic(record):
    subscribers, _ = get_topic_count(record)
    topic_id = record.get('topic_id')

    if subscribers in (0, 'topic not found'):
        logging.warning('Deleting %s' % topic_id)

        db.topics.remove({'topic_id': topic_id})
        # Only try to delete GovDelivery topics with 0 subscribers - don't bother
        # trying to delete topics we know don't exist:
        if subscribers == 0:
            delivery_partner.delete_topic(topic_id)
    elif subscribers is None:
        logging.warning('Skipping %s as we got an error from GovDelivery' % topic_id)
    else:
        logging.warning('Skipping %s as it now has %s subscribers' % (topic_id, subscribers))


def delete_topics_without_subscribers(get_topic_count, delete_topic, thread_count=20):
    pool = Pool(thread_count)

    one_day_ago = datetime.datetime.utcnow() - datetime.timedelta(days=1)
    records_with_count = pool.map(get_topic_count, db.topics.find({'created': {'$lt': one_day_ago}}))
    topics_missing_subscribers = [record for (count, record) in records_with_count if count == 0]
    missing_topics = [record for (count, record) in records_with_count if count == 'topic not found']
    topics_with_errors = [record for (count, record) in records_with_count if count is None]

    print ''
    logging.warning('%s topics have no subscriptions' % len(topics_missing_subscribers))
    for topic in topics_missing_subscribers:
        logging.warning('%s: %s' % (topic.get('topic_id'), topic.get('_id')))

    if missing_topics:
        print ''
        logging.warning("%s topics don't exist in GovDelivery" % len(missing_topics))
        for topic in missing_topics:
            logging.warning('%s: %s' % (topic.get('topic_id'), topic.get('_id')))

    if topics_with_errors:
        print ''
        logging.warning('%s topics with errors - THESE ARE NOT BEING DELETED' % len(topics_with_errors))
        for topic in topics_with_errors:
            logging.warning('%s: %s' % (topic.get('topic_id'), topic.get('_id')))

    print ''
    command = raw_input("%s topics have no subscriptions and %s don't exist in GovDelivery, enter `delete` to delete from database and GovDelivery: " % (len(topics_missing_subscribers), len(missing_topics)))

    if command == 'delete':
        topics_to_delete = topics_missing_subscribers + missing_topics
        for topic in topics_to_delete:
            delete_topic(topic)
        logging.warning('Successfully deleted %s topics' % len(topics_to_delete))

if __name__ == '__main__':
    delete_topics_without_subscribers(get_topic_count, delete_topic, 40)
