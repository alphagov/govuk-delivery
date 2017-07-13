import os
import base64
import urllib

import requests
from requests.auth import HTTPBasicAuth
from jinja2 import Environment, FileSystemLoader
import xmltodict

__all__ = ['GovDeliveryClient']

class GovDeliveryAPIClientException(Exception):
    pass

with open(os.path.join(os.path.dirname(__file__), 'templates', 'default_footer.html'), 'r') as footer_file:
    default_footer = footer_file.read()

# Error codes:
# http://knowledge.govdelivery.com/display/API/Subscriber+Error+Codes

class GovDeliveryClient(object):
    def __init__(self, username, password, account_code, hostname='api.govdelivery.com'):
        self.auth = HTTPBasicAuth(username, password)
        self.hostname = hostname
        self.account_code = account_code
        self.env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(__file__), 'templates')))

    def _api_url(self, path):
        url = 'https://%s/api/account/%s/%s.xml' % (self.hostname, self.account_code, path)
        return url

    def _get(self, path):
        response = requests.get(self._api_url(path), auth=self.auth, headers={'content-type': 'application/xml'})
        return self._parse_response(response)

    def _post(self, path, params):
        response = requests.post(self._api_url(path), data=params, auth=self.auth, headers={'content-type': 'application/xml'})
        return self._parse_response(response)

    def _put(self, path, params):
        response = requests.put(self._api_url(path), data=params, auth=self.auth, headers={'content-type': 'application/xml'})
        # TODO: are there any PUTs we won't want to do this?
        return response.status_code

    def _delete(self, path):
        response = requests.delete(self._api_url(path), auth=self.auth, headers={'content-type': 'application/xml'})
        return response

    def _parse_response(self, response):
        response_text = response.text
        if 'application/xml' in response.headers.get('content-type'):
            response_text = self.parse_xml_content(response_text)
            if response_text.get('errors'):
                errors = response_text['errors']['error']
                if isinstance(errors, basestring):
                    errors = [errors]
                raise Exception("\n".join(['HTTP status: %s' % response.status_code, response_text['errors']['code']] + errors))
        response.raise_for_status()
        return response_text

    def parse_xml_content(self, content):
        return xmltodict.parse(content)

    def _template(self, template_name, context):
        template = self.env.get_template('%s.jinja' % template_name)
        return template.render(**context).encode('utf-8')

    # These are the public API bits
    def read_topic(self, topic_id):
        """Read an individual topic.

        Usage: client.read_topic('TOPIC_ID')

        http://knowledge.govdelivery.com/display/API/Read+Topic"""
        return self._get('topics/%s' % urllib.quote(topic_id))

    def create_topic(self, params):
        """Create a topic.

        Usage: client.create_topic({arg1: val1,...})

        http://knowledge.govdelivery.com/display/API/Create+Topic"""
        post_data = self._template('create_topic', params)
        return self._post('topics', post_data)

    def update_topic_categories(self, topic_id, categories):
        """Replace topic categories.

        Usage: client.update_topic_categories('TOPIC_ID', ['CATEGORY_ID'])

        http://knowledge.govdelivery.com/display/API/Update+Topic+Categories"""
        post_data = self._template('update_topic_categories', {'categories': categories})
        return self._put('topics/%s/categories' % urllib.quote(topic_id), post_data)

    def update_topic(self, topic_id, params):
        """Update topic data.

        Usage: client.update_topic('TOPIC_ID', {'name': 'Blah',
                                                'short_name': 'Blah',
                                                'visibility': 'Unlisted'})

        http://knowledge.govdelivery.com/display/API/Update+Topic"""
        params.update({'topic_code': topic_id})
        post_data = self._template('update_topic', params)
        return self._put('topics/%s' % urllib.quote(topic_id), post_data)

    def delete_topic(self, topic_id):
        """Deletes a topic.

        Usage: client.delete_topic('TOPIC_ID')

        http://knowledge.govdelivery.com/display/API/Delete+Topic"""
        response = self._delete('topics/%s' % urllib.quote(topic_id))
        return response.status_code == 200

    def read_subscriber(self, email):
        """Read a subscriber's details.

        Usage: client.read_subscriber('me@example.com')

        http://knowledge.govdelivery.com/display/API/Read+Subscriber"""
        try:
            subscriber = self._get('subscribers/%s' % urllib.quote(base64.b64encode(email)))
        except Exception as errors:
            if 'GD-15002' not in str(errors):
                raise
            subscriber = None
        return subscriber

    def create_subscriber(self, email, frequency='daily'):
        """Create a new subscriber.

        Usage: client.create_subscriber('me@example.com')

        http://knowledge.govdelivery.com/display/API/Create+Subscriber"""
        if frequency not in ['daily', 'weekly', 'instant']:
            raise GovDeliveryAPIClientException("Invalid frequency value: %s" % frequency)
        post_data = self._template('create_subscriber', {'email': email, 'frequency': frequency})
        try:
            subscriber = self._post('subscribers', post_data)
        except Exception as errors:
            if 'GD-15004' not in str(errors):
                raise
            subscriber = None
        return subscriber

    def list_subscriber_topics(self, email):
        """Read subscriber topics.

        Usage: client.list_subscriber_topics('name@example.com')

        http://knowledge.govdelivery.com/display/API/List+Subscriber+Topics"""
        response = self._get('subscribers/%s/topics' % urllib.quote(base64.b64encode(email)))
        if response['topics'].get('topic'):
            if not isinstance(response['topics']['topic'], list):
                topics = [response['topics']['topic']]
            else:
                topics = response['topics']['topic']
            return [element['to-param'] for element in topics]
        return []

    def merge_subscriber_topics(self, email, new_topics):
        """Merges two topic lists together.

        Usage: client.merge_subscriber_topics('me@example.com', ['NEW_TOPIC'])"""
        current_topics = self.list_subscriber_topics(email)
        if sorted(new_topics) != sorted(current_topics):
            new_topics = list(set(new_topics + current_topics))
            return self.update_subscriber_topics(email, new_topics)
        return True

    def update_subscriber_frequency(self, email, frequency='daily'):
        """Update an existing subscriber frequency.

        Usage: client.update_subscriber_frequency('me@example.com')

        http://knowledge.govdelivery.com/display/API/Create+Subscriber"""
        if frequency not in ['daily', 'weekly', 'instant']:
            raise GovDeliveryAPIClientException("Invalid frequency value: %s" % frequency)
        post_data = self._template('update_subscriber_frequency', {'frequency': frequency, 'email': email})
        return self._put('subscribers/%s' % urllib.quote(base64.b64encode(email)), post_data)

    def update_subscriber_topics(self, email, topic_ids):
        """Update subscriber topics.

        Usage: client.update_subscriber_topics('name@example.com', ['TOPIC1', 'TOPIC2'])

        http://knowledge.govdelivery.com/display/API/Update+Subscriber+Topics"""
        # XXX: this is currently destructive, we probably want to
        # perform some kind of merge over existing topics.

        post_data = self._template('update_subscriber_topics', {'topic_ids': topic_ids})
        return self._put('subscribers/%s/topics' % urllib.quote(base64.b64encode(email)), post_data) == 200

    def create_subscriber_and_add_subscriptions(self, email, topic_ids):
        """Creates a user and subscribes them to topic_ids in a single request.

        Usage: client.create_subscriber_and_add_subscriptions('name@example.com', ['TOPIC1', 'TOPIC2'])

        http://knowledge.govdelivery.com/display/API/Add+Subscriptions"""

        post_data = self._template('create_subscriber_and_add_subscriptions', {'email': email, 'topic_ids': topic_ids})
        return self._post('subscribers/add_subscriptions', post_data)

    def create_and_send_bulletin(self, topic_ids, subject, body):
        """Create and send a bulletin to TOPICS.

        Usage: client.create_and_send_bulletin([123, 456], 'My subject', '<p>This is HTML text</p>')

        http://knowledge.govdelivery.com/display/API/Create+and+Send+Bulletin"""
        post_data = self._template('create_and_send_bulletin', {'topic_ids': topic_ids, 'subject': subject, 'body': body, 'footer': default_footer})
        return self._post('bulletins/send_now', post_data)
