import unittest
import logging
import urllib
from collections import namedtuple

from flask import json
from mock import patch

import service
from adapters.partner_id_repository import FindResponse

class FakeGovDeliveryClient(object):
    def __init__(self, *args, **kwargs):
        return

    def subscribe(self, *args, **kwargs):
        return

    def create_topic(self, *args, **kwargs):
        return

    def create_and_send_bulletin(self, *args, **kwargs):
        return


class FakeSubscription(object):
    def __init__(self, *args):
        return

    def subscribe(self, *args):
        return

    def partner_id(self, *args):
        return

    def parse_topics(slef, *args):
        return

    def send_notification(self, *args):
        return

    def log_notification(self, *args):
        return

    def partner_signup_url(self, feed_url):
        return None


class FakePartnerIdRepository(object):
    def __init__(self, *args):
        return

    def find_partner_id_for_url(self, *args, **kwargs):
        return FindResponse(None, None)

    def store_partner_id_for_url(self, feed_url, list_id):
        return None

class FakeNotificationLog(object):
    def __init__(self, *args,  **kwargs):
        return

    def create_notification_log(self, * args):
        return

class GenericFlaskTestCase(unittest.TestCase):
    def setUp(self):
        service.flask_app.config['TESTING'] = True
        service.flask_app.config['USE_BACKGROUND_WORKERS'] = False
        # Clobber all logging
        logger = logging.getLogger(service.flask_app.logger_name)
        logger.disabled = True
        self.flask_app = service.flask_app
        self.app = service.flask_app.test_client()

    def post_json_to_app(self, route, data, headers={}):
        data = json.dumps(data)
        return self.app.post(route,
                             content_type='application/json',
                             data=data,
                             headers=headers)

    def get_app(self, route, data, **other):
        path_and_query = '%s?%s' % (route, urllib.urlencode(data))
        return self.app.get(path_and_query, **other)


class BasicServiceTestCase(GenericFlaskTestCase):
    def test_hearbeat_is_reachable(self):
        response = self.app.get('/_status')
        assert response.status_code == 200


class SubscriptionServiceTestCase(GenericFlaskTestCase):
    def test_rejects_non_json_requests(self):
        response = self.app.post('/subscriptions')
        assert response.status_code == 415

    def test_returns_bad_request_if_no_params(self):
        response = self.app.post('/subscriptions', content_type='application/json')
        assert response.status_code == 400

    def test_returns_bad_request_if_no_email(self):
        data = json.dumps({'feed_urls': ['http://example.com']})
        response = self.app.post('/subscriptions',
                           content_type='application/json',
                           data=data)
        assert response.status_code == 400

    def test_returns_bad_request_if_no_feed_url(self):
        data = json.dumps({'email': 'me@example.com'})
        response = self.app.post('/subscriptions',
                           content_type='application/json',
                           data=data)
        assert response.status_code == 400

    @patch.dict(service.flask_app.config, {'SUBSCRIPTION_OBJECT': FakeSubscription})
    @patch.object(FakeSubscription, 'subscribe', return_value=True)
    def test_returns_created_if_subscription_successful(self, mock_subscribe):
        data = json.dumps({'email': 'me@example.com',
                           'feed_urls': ['http://example.com']})
        response = self.app.post('/subscriptions',
                           content_type='application/json',
                           data=data)
        assert response.status_code == 201

    @patch.dict(service.flask_app.config, {'SUBSCRIPTION_OBJECT': FakeSubscription})
    @patch.object(FakeSubscription, 'subscribe', return_value=False)
    def test_returns_server_error_if_subscription_fails(self, mock_subscribe):
        data = json.dumps({'email': 'me@example.com',
                           'feed_urls': ['http://example.com']})
        response = self.app.post('/subscriptions',
                           content_type='application/json',
                           data=data)
        assert response.status_code == 500

    @patch.dict(service.flask_app.config, {'SUBSCRIPTION_OBJECT': FakeSubscription})
    @patch.object(FakeSubscription, 'subscribe')
    def test_tries_to_subscribe(self, mock_subscription):
        data = json.dumps({'email': 'me@example.com',
                           'feed_urls': ['http://example.com']})
        response = self.app.post('/subscriptions',
                                 content_type='application/json',
                                 data=data)

        mock_subscription.assert_called_once_with('me@example.com',
                                                  ['http://example.com'])

class ListServiceTestCase(GenericFlaskTestCase):
    def test_rejects_non_json_requests(self):
        response = self.app.post('/lists')
        assert response.status_code == 415

    def test_returns_bad_request_if_no_params(self):
        response = self.app.post('/lists', content_type='application/json')
        assert response.status_code == 400

    def test_returns_bad_request_if_no_feed_title(self):
        data = json.dumps({'feed_url': 'http://example.com'})
        response = self.app.post('/lists',
                           content_type='application/json',
                           data=data)
        assert response.status_code == 400

    def test_returns_bad_request_if_no_feed_url(self):
        data = json.dumps({'title': 'A title'})
        response = self.app.post('/lists',
                           content_type='application/json',
                           data=data)
        assert response.status_code == 400

    @patch.dict(service.flask_app.config, {'SUBSCRIPTION_OBJECT': FakeSubscription})
    @patch.object(FakeSubscription, 'partner_id', return_value="TOPIC_123")
    def test_tries_to_map_partner_id(self, mock_subscription):
        data = json.dumps({'title': 'A title',
                           'feed_url': 'http://example.com'})
        response = self.app.post('/lists',
                                 content_type='application/json',
                                 data=data)

        mock_subscription.assert_called_once_with('http://example.com',
                                                  'A title',
                                                  None)

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse("TOPIC_123", False))
    def test_tries_to_find_partner_by_url(self, mock_repository):
        data = json.dumps({'title': 'A title',
                           'feed_url': 'http://example.com/?b=1&a=2&c=2'})
        response = self.app.post('/lists',
                                 content_type='application/json',
                                 data=data)

        assert mock_repository.called

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                     'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakeGovDeliveryClient, 'create_topic', return_value={'topic': {'to-param': "TOPIC_123"}})
    def test_tries_to_create_topic_if_not_found(self, mock_client):
        data = json.dumps({'title': 'A title',
                           'feed_url': 'http://example.com/?b=1&a=2&c=2'})
        response = self.app.post('/lists',
                                 content_type='application/json',
                                 data=data)

        assert mock_client.called

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                     'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'store_partner_id_for_url')
    @patch.object(FakeGovDeliveryClient, 'create_topic', return_value={'topic': {'to-param': 12345}})
    def test_tries_to_store_partner_id_by_url(self, mock_client, mock_storage):
        data = json.dumps({'title': 'A title',
                           'feed_url': 'http://example.com/feed'})
        response = self.app.post('/lists',
                                 content_type='application/json',
                                 data=data)

        mock_storage.assert_called_once_with('http://example.com/feed', 12345)
        self.assertEqual(response.status_code, 201)

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                     'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'store_partner_id_for_url')
    @patch.object(FakeGovDeliveryClient, 'create_topic', return_value={'topic': {'to-param': 'TOPIC_12345'}})
    def test_returns_the_partner_id(self, mock_client, mock_storage):
        data = json.dumps({'title': 'A title',
                           'feed_url': 'http://example.com/feed'})
        response = self.app.post('/lists',
                                 content_type='application/json',
                                 data=data)

        body = json.loads(response.data)
        self.assertEqual(body, {'success': True, 'partner_id': 'TOPIC_12345'})

# stop logging being posted to running server during tests - without this the errors are
# swallowed silently when the service isn't running.
@patch.dict(service.flask_app.config, {'NOTIFICATION_LOG_CLIENT_OBJECT': FakeNotificationLog})
class NotificationTestCase(GenericFlaskTestCase):
    @patch.dict(service.flask_app.config, {'SUBSCRIPTION_OBJECT': FakeSubscription})
    @patch.object(FakeSubscription, 'parse_topics', return_value=service.TopicIds(['TOPIC_ABC'], []))
    @patch.object(FakeSubscription, 'send_notification')
    @patch.object(FakeSubscription, 'log_notification')
    def test_tries_to_send_notification(self, mock_logger, mock_notification, mock_parser):
        data = json.dumps({'feed_urls': ['http://example.com/feed'],
                           'subject': "My subject",
                           'body': '<p>Body</p>'})

        response = self.app.post('/notifications',
                                 content_type='application/json',
                                 data=data)
        mock_parser.assert_called_once_with(['http://example.com/feed'])
        mock_notification.assert_called_once_with(['TOPIC_ABC'],
                                                  'My subject',
                                                  '<p>Body</p>')


    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                     'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url')
    def test_tries_to_verify_feed_urls_before_notifying(self, mock_repository):
        data = {'feed_urls': ['http://example.com/feed'],
                'subject': 'My subject',
                'body': 'body',
                'logging_params': {}}
        response = self.post_json_to_app('/notifications', data)
        mock_repository.called_once_with('http://example.com/feed')

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                     'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse(None, False))
    @patch.object(FakeGovDeliveryClient, 'create_and_send_bulletin')
    def test_will_not_send_email_to_nonexistent_topics(self, mock_notification, mock_repository):
        data = {'feed_urls': ['http://example.com/nonexistent'],
                'subject': 'My subject',
                'body': 'body'}
        response = self.post_json_to_app('/notifications', data)
        assert not mock_notification.called

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                     'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url')
    @patch.object(FakeGovDeliveryClient, 'create_and_send_bulletin')
    def test_will_only_send_to_existing_topics(self, mock_notification, mock_repository):
        def return_values(feed_url, *args, **kwargs):
            if feed_url == 'http://example.com/disabled':
                return FindResponse('54321', True)
            elif feed_url == 'http://example.com/exists':
                return FindResponse('12345', False)
            return FindResponse(None, False)
        mock_repository.side_effect = return_values
        data = {'feed_urls': ['http://example.com/disabled', 'http://example.com/nonexistent', 'http://example.com/exists'],
                'subject': 'My subject',
                'body': 'body'}
        response = self.post_json_to_app('/notifications', data)
        mock_notification.assert_called_once_with(['12345'], 'My subject', 'body')

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                     'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', side_effect=[FindResponse(None, False), FindResponse('12345', False)])
    @patch.object(FakeGovDeliveryClient, 'create_and_send_bulletin')
    def test_will_not_send_to_disabled_topics(self, mock_notification, mock_repository):
        data = {'feed_urls': ['http://example.com/disabled'],
                'subject': 'My subject',
                'body': 'body'}
        response = self.post_json_to_app('/notifications', data)
        self.assertItemsEqual(mock_notification.call_args_list, [])

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                     'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse('12345', False))
    @patch.object(FakeGovDeliveryClient, 'create_and_send_bulletin', side_effect=Exception('Error code: GD-12004'))
    def test_send_notification_ignores_topics_with_no_subscribers(self, mock_notification, mock_repository):
        data = {'feed_urls': ['http://example.com/exists'],
                'subject': 'My subject',
                'body': 'body'}
        response = self.post_json_to_app('/notifications', data)
        assert response.status_code == 400
        body = json.loads(response.data)
        assert 'No subscribers for topics' in body['message']

    @patch.dict(service.flask_app.config, {'DISABLE_NOTIFICATIONS': True,
                                     'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                     'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse('12345', False))
    @patch.object(FakeGovDeliveryClient, 'create_and_send_bulletin')
    def test_notification_sending_can_be_disabled(self, mock_notification, mock_repository):
        data = {'feed_urls': ['http://example.com/exists'],
                'subject': 'My subject',
                'body': 'body'}
        response = self.post_json_to_app('/notifications', data)
        assert not mock_notification.called

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                           'NOTIFICATION_LOG_CLIENT_OBJECT': FakeNotificationLog,
                                           'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse('12345', False))
    @patch.object(FakeNotificationLog, 'create_notification_log')
    def test_sending_log_notification_with_enabled_topics(self, mock_notification_log, mock_repository):
        data = {'feed_urls': ['http://example.com/exists'],
                'subject': 'My subject',
                'body': 'body',
                'logging_params': {
                  'content_id': 'aaaaa-111111',
                  'public_updated_at': '2017-02-28'
                }}
        response = self.post_json_to_app('/notifications', data, {'Govuk-Request-Id': '111111'})
        mock_notification_log.assert_called_once_with(['12345'], [], 'aaaaa-111111', '2017-02-28', '111111')

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                           'NOTIFICATION_LOG_CLIENT_OBJECT': FakeNotificationLog,
                                           'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse('12345', True))
    @patch.object(FakeNotificationLog, 'create_notification_log')
    def test_sending_log_notification_with_disabled_topics(self, mock_notification_log, mock_repository):
        data = {'feed_urls': ['http://example.com/exists'],
                'subject': 'My subject',
                'body': 'body',
                'logging_params': {
                  'content_id': 'aaaaa-111111',
                  'public_updated_at': '2017-02-28'
                }}
        response = self.post_json_to_app('/notifications', data, {'Govuk-Request-Id': '111111'})
        mock_notification_log.assert_called_once_with([], ['12345'], 'aaaaa-111111', '2017-02-28', '111111')


    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                           'NOTIFICATION_LOG_CLIENT_OBJECT': FakeNotificationLog,
                                           'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse('12345', False))
    @patch.object(FakeNotificationLog, 'create_notification_log', side_effect=Exception('Broken notification log'))
    @patch.object(FakeGovDeliveryClient, 'create_and_send_bulletin')
    def test_ignores_errors_from_log_notification(self, mock_notification, mock_notification_log, mock_repository):
        data = {'feed_urls': ['http://example.com/exists'],
                'subject': 'My subject',
                'body': 'body',
                'logging_params': {
                  'content_id': 'aaaaa-111111',
                  'public_updated_at': '2017-02-28'
                }}
        response = self.post_json_to_app('/notifications', data, {'Govuk-Request-Id': '111111'})
        mock_notification.assert_called_once_with(['12345'], 'My subject', 'body')
        assert response.status_code == 201

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                           'NOTIFICATION_LOG_CLIENT_OBJECT': FakeNotificationLog,
                                           'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse('12345', False))
    @patch.object(FakeNotificationLog, 'create_notification_log')
    def test_logging_params_hash_is_optional(self, mock_notification_log, mock_repository):
        data = {'feed_urls': ['http://example.com/exists'],
                'subject': 'My subject',
                'body': 'body'}
        response = self.post_json_to_app('/notifications', data, {'Govuk-Request-Id': '111111'})
        mock_notification_log.assert_called_once_with(['12345'], [], None, None, '111111')

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository,
                                           'NOTIFICATION_LOG_CLIENT_OBJECT': FakeNotificationLog,
                                           'GOVDELIVERY_CLIENT_OBJECT': FakeGovDeliveryClient})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse('12345', False))
    @patch.object(FakeNotificationLog, 'create_notification_log')
    def test_logging_params_hash_values_are_optional(self, mock_notification_log, mock_repository):
        data = {'feed_urls': ['http://example.com/exists'],
                'subject': 'My subject',
                'body': 'body',
                'logging_params': {}}
        response = self.post_json_to_app('/notifications', data, {'Govuk-Request-Id': '111111'})
        mock_notification_log.assert_called_once_with(['12345'], [], None, None, '111111')

class ListUrlTestCase(GenericFlaskTestCase):
    def test_partner_signup_url_validates_arguments(self):
        args = {}
        response = self.get_app('/list-url', args)
        assert response.status_code == 400

    @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse(None, None))
    def test_partner_signup_url_looks_for_partner_id(self, mock_subscription):
        args = {'feed_url': 'http://example.com/feed'}
        response = self.get_app('/list-url', args)
        mock_subscription.called_once_with('http://example.com/feed')

    # @patch.dict(service.flask_app.config, {'PARTNER_ID_REPOSITORY': FakePartnerIdRepository})
    # @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse(None, False))

    @patch.dict(service.flask_app.config, {'SUBSCRIPTION_OBJECT': FakeSubscription})
    @patch.object(FakeSubscription, 'partner_signup_url', return_value='http://partner.example.com/signup')
    def test_partner_signup_url_returns_url(self, mock_subscription):
        args = {'feed_url': 'http://example.com/feed'}
        response = self.get_app('/list-url', args)
        data = json.loads(response.data)

        assert data['success']
        assert data['list_url'] == 'http://partner.example.com/signup'

    @patch.dict(service.flask_app.config, {'GOVDELIVERY_SIGNUP_FORM': 'https://example.com/%s',
                                     'PARTNER_ID_REPOSITORY': FakePartnerIdRepository})
    @patch.object(FakePartnerIdRepository, 'find_partner_id_for_url', return_value=FindResponse('12345', False))
    def test_signup_url_comes_from_configuration(self, *args):
        args = {'feed_url': 'http://example.com/feed'}
        response = self.get_app('/list-url', args)
        data = json.loads(response.data)

        assert data['list_url'] == 'https://example.com/12345'

    @patch.dict(service.flask_app.config, {'LIST_TITLE_FORMAT': 'TEST: %s',
                                     'SUBSCRIPTION_OBJECT': FakeSubscription})
    @patch.object(FakeSubscription, 'partner_id', return_value="TOPIC_123")
    def test_list_titles_can_be_formatted(self, mock_subscription):
        data = {'title': 'A title',
                'feed_url': 'http://example.com'}
        response = self.post_json_to_app('/lists', data)

        mock_subscription.assert_called_once_with('http://example.com',
                                                  'TEST: A title',
                                                  None)


class DelayedSubscriptionServiceTestCase(GenericFlaskTestCase):
    @patch.dict(service.flask_app.config, {'USE_BACKGROUND_WORKERS': True})
    @patch.object(service.send_notification, 'delay')
    def test_background_worker_used_to_notify(self, notifier):
        data = json.dumps({'feed_urls': ['http://example.com/feed'],
                           'subject': "My subject",
                           'body': '<p>Body</p>',
                           'logging_params': {}})

        response = self.app.post('/notifications',
                                 content_type='application/json',
                                 data=data)
        notifier.assert_called_once_with(['http://example.com/feed'],
                                         'My subject',
                                         '<p>Body</p>',
                                         {},
                                         '')

    @patch.dict(service.flask_app.config, {'USE_BACKGROUND_WORKERS': True})
    @patch.object(service, 'send_notification')
    def test_regular_notifier_not_used(self, notifier):
        data = json.dumps({'feed_urls': ['http://example.com/feed'],
                           'subject': "My subject",
                           'body': '<p>Body</p>',
                           'logging_params': {}})

        response = self.app.post('/notifications',
                                 content_type='application/json',
                                 data=data)

        assert not notifier.called

class DisableListTestCase(GenericFlaskTestCase):
    def setUp(self):
        super(DisableListTestCase, self).setUp()
        self.db = self.flask_app.config['MONGO'].govuk_delivery.topics
        self.db.remove({'_id': 'http://www.test.com/'})

    def test_disable_gov_delivery_id_for_exisiting_subscriber_list(self):
        self.db.insert({
            '_id': 'http://www.test.com/',
            'topic_id': 'TOPIC_6666666',
            'created': '2017-03-27'
        })
        data = json.dumps({ 'gov_delivery_id': 'TOPIC_6666666' })

        response = self.app.post('/lists/disable',
                                 content_type='application/json',
                                 data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {
          'url': 'http://www.test.com/',
          'topic_id': 'TOPIC_6666666',
          'disabled': True,
          'success': True
        })

    def test_disable_gov_delivery_id_for_disabled_subscriber_list(self):
        self.db.insert({
            '_id': 'http://www.test.com/',
            'topic_id': 'TOPIC_6666666',
            'created': '2017-03-27',
            'disabled': True
        })
        data = json.dumps({ 'gov_delivery_id': 'TOPIC_6666666' })

        response = self.app.post('/lists/disable',
                                 content_type='application/json',
                                 data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {
          'url': 'http://www.test.com/',
          'topic_id': 'TOPIC_6666666',
          'disabled': True,
          'success': True
        })

    def test_disable_gov_delivery_id_that_does_not_have_a_subscriber_list(self):
        data = json.dumps({ 'gov_delivery_id': 'TOPIC_6666666' })

        response = self.app.post('/lists/disable',
                                 content_type='application/json',
                                 data=data)

        self.assertEqual(response.status_code, 404)

class EnableListTestCase(GenericFlaskTestCase):
    def setUp(self):
        super(EnableListTestCase, self).setUp()
        self.db = self.flask_app.config['MONGO'].govuk_delivery.topics
        self.db.remove({'_id': 'http://www.test.com/'})

    def test_enable_gov_delivery_id_for_exisiting_subscriber_list(self):
        self.db.insert({
            '_id': 'http://www.test.com/',
            'topic_id': 'TOPIC_6666666',
            'created': '2017-03-27',
            'disabled': True
        })
        data = json.dumps({ 'gov_delivery_id': 'TOPIC_6666666' })

        response = self.app.post('/lists/enable',
                                 content_type='application/json',
                                 data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {
          'url': 'http://www.test.com/',
          'topic_id': 'TOPIC_6666666',
          'disabled': None,
          'success': True
        })

    def test_enable_gov_delivery_id_for_enabled_subscriber_list(self):
        self.db.insert({
            '_id': 'http://www.test.com/',
            'topic_id': 'TOPIC_6666666',
            'created': '2017-03-27',
            'disabled': None
        })
        data = json.dumps({ 'gov_delivery_id': 'TOPIC_6666666' })

        response = self.app.post('/lists/enable',
                                 content_type='application/json',
                                 data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.data), {
          'url': 'http://www.test.com/',
          'topic_id': 'TOPIC_6666666',
          'disabled': None,
          'success': True
        })

    def test_enable_gov_delivery_id_that_does_not_have_a_subscriber_list(self):
        data = json.dumps({ 'gov_delivery_id': 'TOPIC_6666666' })

        response = self.app.post('/lists/enable',
                                 content_type='application/json',
                                 data=data)

        self.assertEqual(response.status_code, 404)


if __name__ == '__main__':
    unittest.main()
