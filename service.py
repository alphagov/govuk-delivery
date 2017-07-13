import os
import logging
import urllib

from flask import Flask, request, g, jsonify, json, current_app
import redis
import pymongo
from logstash_formatter import LogstashFormatter

from adapters.gov_delivery import GovDeliveryClient
from adapters.notification_log import NotificationLog
from adapters.partner_id_repository import PartnerIdRepository
from tasks import make_celery
from collections import namedtuple

TopicIds = namedtuple('TopicIds', ['enabled', 'disabled'])
flask_app = Flask('govuk_delivery')
flask_app.config.from_pyfile('settings.py')
flask_app.config.from_pyfile('production-settings.py', silent=True)

# Redis is threadsafe, so instantiate it in the main run
flask_app.config.update(
    REDIS=redis.StrictRedis(**flask_app.config['REDIS_SETTINGS']),
    MONGO=pymongo.MongoClient(**flask_app.config['MONGODB_SETTINGS']),
    CELERY_BROKER_URL='redis://%(host)s:%(port)i/%(db)i' % flask_app.config['REDIS_SETTINGS']
)

celery = make_celery(flask_app)

def environment():
    return os.getenv("GOVUK_ENV", "development")

handler = logging.FileHandler("log/%s.json.log" % environment())
logging.worker_hijack_root_logger = False

formatter = LogstashFormatter()
handler.setFormatter(formatter)
handler.setLevel(logging.INFO)
flask_app.logger.addHandler(handler)

flask_app.logger.setLevel(logging.INFO)

if flask_app.debug:
    handler = logging.FileHandler("log/development.log")
    handler.setLevel(logging.DEBUG)
    flask_app.logger.addHandler(handler)
    flask_app.logger.setLevel(logging.DEBUG)

def logstasher_request(request):
    """Returns the REQUEST line for logstasher"""
    path = request.path
    if request.args:
        path = "%s?%s" % (path, request.environ['QUERY_STRING'])
    return "%s %s %s" % (request.method, path, request.environ.get('SERVER_PROTOCOL', 'HTTP/1.0'))

def logstasher_request_params(request, status):
    """
    Returns a dictionary of request params that we expect to exist for each log line
    """
    values = {
        'request': logstasher_request(request),
        'request_method': request.method,
        'status': status,
        'govuk_request_id': request.headers.get('Govuk-Request-Id', ''),
    }

    if request.values:
        values['params'] = urllib.urlencode(request.values)

    if request.method != 'GET' and request.get_json():
        values['json'] = json.dumps(request.get_json())

    return values

class Subscription(object):
    def __init__(self, mongo, gov_delivery_client, notification_log_client):
        # TODO: make DB name configurable
        mongo_db = mongo.govuk_delivery
        self.repository = current_app.config['PARTNER_ID_REPOSITORY'](mongo_db.topics)
        gov_delivery_client_args = {
            'username': current_app.config['GOVDELIVERY_USERNAME'],
            'password': current_app.config['GOVDELIVERY_PASSWORD'],
            'account_code': current_app.config['GOVDELIVERY_ACCOUNT_CODE'],
            'hostname': current_app.config['GOVDELIVERY_HOSTNAME'],
        }
        self.delivery_partner = gov_delivery_client(**gov_delivery_client_args)

        notification_log_client_args = {
            'hostname': current_app.config['NOTIFICATION_LOG_HOSTNAME'],
            'protocol': current_app.config['NOTIFICATION_LOG_PROTOCOL']
        }
        self.notification_log = notification_log_client(**notification_log_client_args)

    # TODO: Test what happens if subscription fails
    def subscribe(self, email, feed_urls, frequency='daily'):
        # Try and get them first
        subscriber = self.delivery_partner.read_subscriber(email)
        if not subscriber:
            subscriber = self.delivery_partner.create_subscriber(email, frequency)
        if subscriber:
            topics = [self.repository.find_partner_id_for_url(url) for url in feed_urls]
            topic_ids = [response.topic_id for response in topics if response.topic_id is not None]
            result = self.delivery_partner.update_subscriber_topics(email, topic_ids)
        return True

    # TODO: Test what happens when creating a list fails
    def partner_id(self, feed_url, title, description=None):
        """Fetches a partner ID from the key/value store, mapped by URL.

        If the URL isn't in the key/value store we create a new list."""
        topic_id = self.repository.find_partner_id_for_url(feed_url).topic_id
        if not topic_id:
            response = self.delivery_partner.create_topic({'name': title,
                                                           'short_name': description,
                                                           'visibility': 'Unlisted'})
            topic_id = response.get('topic', {}).get('to-param')
            self.repository.store_partner_id_for_url(feed_url, topic_id)
        return topic_id


    def parse_topics(self, feed_urls):
        topics = [self.repository.find_partner_id_for_url(url) for url in feed_urls]
        enabled_topic_ids = [v.topic_id for v in topics if v.topic_id is not None and not v.disabled]
        disabled_topic_ids = [v.topic_id for v in topics if v.topic_id is not None and v.disabled]

        return TopicIds(enabled_topic_ids, disabled_topic_ids)

    def send_notification(self, topic_ids, subject, body):
        if not current_app.config.get('DISABLE_NOTIFICATIONS'):
            return self.delivery_partner.create_and_send_bulletin(topic_ids, subject, body)
        else:
            current_app.logger.info('Would send email: %r' % {
                'topic_ids': topic_ids,
                'subject': subject,
                'body': body})
            return True

    def log_notification(self, enabled_gov_delivery_ids, disabled_gov_delivery_ids, logging_params, govuk_request_id):
        try:
            log_response = self.notification_log.create_notification_log(
                enabled_gov_delivery_ids,
                disabled_gov_delivery_ids,
                logging_params.get('content_id', None),
                logging_params.get('public_updated_at', None),
                govuk_request_id
            )
        except Exception as error:
            current_app.logger.warn(error)
            current_app.logger.warn(
                'Error creating notification log for request id: %s, content id: %s, matching gov delivery IDs: %s',
                govuk_request_id,
                logging_params.get('content_id', 'missing-content-id'),
                enabled_gov_delivery_ids
            )


    def partner_signup_url(self, feed_url):
        response = self.repository.find_partner_id_for_url(feed_url)
        if response.topic_id:
            return current_app.config['GOVDELIVERY_SIGNUP_FORM'] % urllib.quote(response.topic_id)
        return None

    def disable(self, gov_delivery_id):
        return self.repository.update(gov_delivery_id, disabled=True)

    def enable(self, gov_delivery_id):
        return self.repository.update(gov_delivery_id, disabled=None)

flask_app.config['SUBSCRIPTION_OBJECT'] = Subscription
flask_app.config['GOVDELIVERY_CLIENT_OBJECT'] = GovDeliveryClient
flask_app.config['NOTIFICATION_LOG_CLIENT_OBJECT'] = NotificationLog
flask_app.config['PARTNER_ID_REPOSITORY'] = PartnerIdRepository

@celery.task(name="send-notification")
def send_notification(feed_urls, subject, body, logging_params, govuk_request_id):
    "Send an email notification"
    subscription = current_app.config['SUBSCRIPTION_OBJECT'](current_app.config['MONGO'],
                                                             current_app.config['GOVDELIVERY_CLIENT_OBJECT'],
                                                             current_app.config['NOTIFICATION_LOG_CLIENT_OBJECT'])

    topic_ids = subscription.parse_topics(feed_urls)
    subscription.log_notification(topic_ids.enabled, topic_ids.disabled, logging_params, govuk_request_id)
    if topic_ids.enabled:
        return subscription.send_notification(topic_ids.enabled, subject, body)

    return None

# Set up client subscription
@flask_app.before_request
def before_request():
    # We set up a global subscription object which means we only make
    # our database connection once
    g.subscription = flask_app.config['SUBSCRIPTION_OBJECT'](flask_app.config['MONGO'],
                                                             flask_app.config['GOVDELIVERY_CLIENT_OBJECT'],
                                                             current_app.config['NOTIFICATION_LOG_CLIENT_OBJECT'])

    if not request.method == 'GET' and not request.get_json():
        if request.headers.get('Content-Type') != 'application/json':
            return '', 415
        return '', 400

@flask_app.route('/notifications', methods=['POST'])
def create_notification():
    """Allows creation of a new alert

    Takes a JSON payload like:

    {
        "feed_urls": [
            "http://feed.com/feed.xml"
        ],
        "subject": "This is an email subject",
        "body" : "<p>Some HTML here</p>"
    }
    """
    # TODO: Should be able to take HTML over multipart
    # TODO: This should take more than one feed
    flask_app.logger.debug('create_notification: %r' % request.get_json())

    if not (request.get_json().get('feed_urls') and request.get_json().get('subject') and request.get_json().get('body')):
        flask_app.logger.debug('Invalid data: %r' % request.get_json())
        flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 400))
        return 'You must provide feed URL(s), a subject, and a body.', 400

    govuk_request_id = request.headers.get('Govuk-Request-Id', '')
    logging_params = request.get_json().get('logging_params', {})
    if flask_app.config.get('USE_BACKGROUND_WORKERS'):
        send_notification.delay(request.get_json()['feed_urls'], request.get_json()['subject'], request.get_json()['body'], logging_params, govuk_request_id)
        flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 201))
    else:
        try:
            send_notification(request.get_json()['feed_urls'], request.get_json()['subject'], request.get_json()['body'], logging_params, govuk_request_id)
        except Exception as error:
            if 'Error code: GD-12004' in str(error):
                flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 400), exc_info=True)
                return jsonify(success=False, message='No subscribers for topics %r' % json.dumps(request.get_json()['feed_urls'])), 400
            flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 201), exc_info=True)
            raise error

    return jsonify(success=True), 201

@flask_app.route('/lists', methods=['POST'])
def create_list():
    """Allows creation of a feed mapping

    Takes a JSON payload like:

    {
        "feed_url": "http://feed.com/feed.xml",
        "title": "This is the name of my feed",
        "description": "An optional description of the feed."
    }
    """
    flask_app.logger.debug('create_list: %r' % request.get_json())

    if not (request.get_json().get('feed_url') and request.get_json().get('title')):
        flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 400))
        return jsonify(message='You must provide a valid feed URL and title', success=False), 400

    title = flask_app.config['LIST_TITLE_FORMAT'] % request.get_json()['title']

    try:
        partner_id = g.subscription.partner_id(request.get_json()['feed_url'], title, request.get_json().get('description'))
    except Exception as error:
        flask_app.logger.error(logstasher_request(request), extra=logstasher_request_params(request, 400), exc_info=True)
        return jsonify(success=False), 400

    flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 201))
    return jsonify(success=True, partner_id=partner_id), 201

@flask_app.route('/list-url', methods=['GET'])
def list_url():
    """Gets a public signup page for a specific topic

    Takes a feed URL as a query string param:

    ?feed_url=djghdkjfghjf"""
    flask_app.logger.debug('list_url: %s' % request.args)
    if not request.args.get('feed_url'):
        flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 400))
        return jsonify(success=False, message='You must provide a feed_url'), 400

    signup_url = g.subscription.partner_signup_url(request.args['feed_url'])
    if not signup_url:
        flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 404))
        return jsonify(success=False), 404

    flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 200))
    return jsonify(success=True, list_url=signup_url), 200

@flask_app.route('/subscriptions', methods=['POST'])
def create_subscription():
    """Allows creation and subscription to topics for an email address

    Takes a JSON payload like:

    {
        "email": "me@example.com",
        "feed_urls": [
            "http://feed.com/feed.xml"
        ]
    }
    """
    # TODO: Validate email and URL
    # TODO: This should take more than one feed
    flask_app.logger.debug('create_subscription: %r' % request.get_json())
    if not (request.get_json().get('email') and request.get_json().get('feed_urls')):
        return '', 400

    if g.subscription.subscribe(request.get_json()['email'], request.get_json()['feed_urls']):
        return jsonify(success=True), 201
    else:
        return '', 500


def update_list(update_method, update_type):
    flask_app.logger.debug('%s_list: %r' % (update_type, request.get_json()))

    if not (request.get_json().get('gov_delivery_id')):
        flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 400))
        return jsonify(message='You must provide a valid GovDelievry ID', success=False), 400
    try:
        list = update_method(request.get_json()['gov_delivery_id'])
    except Exception as error:
        flask_app.logger.error(logstasher_request(request), extra=logstasher_request_params(request, 400), exc_info=True)
        return jsonify(success=False), 400

    if not list:
        flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 404))
        return jsonify(success=False), 404

    flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 201))
    return jsonify(
        success=True,
        topic_id=list.get('topic_id'),
        url=list.get('_id'),
        disabled=list.get('disabled')
    ), 200

@flask_app.route('/lists/disable', methods=['POST'])
def disable_list():
    """Allows disabling of a feed URL

    Takes a JSON payload like:

    {
        "gov_delivery_id": "TOPIC_12",
    }
    """
    return update_list(g.subscription.disable, 'disable')

@flask_app.route('/lists/enable', methods=['POST'])
def enable_list():
    """Allows enabling of a feed URL

    Takes a JSON payload like:

    {
        "gov_delivery_id": "TOPIC_12",
    }
    """
    return update_list(g.subscription.enable, 'enable')

@flask_app.route('/_status')
def health_check():
    flask_app.logger.info(logstasher_request(request), extra=logstasher_request_params(request, 200))
    return jsonify(status='ok', message='workers available')

if __name__ == '__main__':
    flask_app.run(port=3042, debug=True)
