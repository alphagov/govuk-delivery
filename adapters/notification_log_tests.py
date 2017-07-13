import unittest

from httpretty import HTTPretty

from notification_log import NotificationLog
import requests
import json

class NotificationLogTests(unittest.TestCase):
    def setUp(self):
        HTTPretty.enable()
        self.client = NotificationLog(hostname='test.example.com', protocol='http')

    def tearDown(self):
        HTTPretty.disable()

    def _api_url(self):
        return 'http://test.example.com/notification_logs.json'


    def test_create_notification_log_makes_a_post_request(self):
        HTTPretty.register_uri(
            HTTPretty.POST,
            self._api_url(),
            body='{"status": "Success"}',
            content_type="application/json"
        )
        self.client.create_notification_log(['ENABLED_TOPIC_ID'], ['DISABLED_TOPIC_ID'], 'content_id', 'updated_at', 'request_id')
        assert HTTPretty.last_request.method == 'POST'
        self.assertEqual(json.loads(HTTPretty.last_request.body),
            {
                "gov_delivery_ids": ["ENABLED_TOPIC_ID", "DISABLED_TOPIC_ID"],
                "enabled_gov_delivery_ids": ["ENABLED_TOPIC_ID"],
                "disabled_gov_delivery_ids": ["DISABLED_TOPIC_ID"],
                "publishing_app": "whitehall",
                "emailing_app": "gov_uk_delivery",
                "govuk_request_id": "request_id",
                "public_updated_at": "updated_at",
                "content_id": "content_id"
            }
        )

    def test_create_notification_log_makes_a_post_request_with_multiple_matching_topics(self):
        HTTPretty.register_uri(
            HTTPretty.POST,
            self._api_url(),
            body='{"status": "Success"}',
            content_type="application/json"
        )
        self.client.create_notification_log(['TOPIC_1', 'TOPIC_2'], [], 'content_id', 'updated_at', 'request_id')
        assert HTTPretty.last_request.method == 'POST'
        self.assertEqual(json.loads(HTTPretty.last_request.body),
            {
                "gov_delivery_ids": ["TOPIC_1", "TOPIC_2"],
                "emailing_app": "gov_uk_delivery",
                "enabled_gov_delivery_ids": ["TOPIC_1", "TOPIC_2"],
                "disabled_gov_delivery_ids": [],
                "publishing_app": "whitehall",
                "govuk_request_id": "request_id",
                "public_updated_at": "updated_at",
                "content_id": "content_id"
            }
        )

    def test_raise_error_on_non_2XX_status_code(self):
        HTTPretty.register_uri(
            HTTPretty.POST,
            self._api_url(),
            status=404
        )
        self.assertRaises(requests.HTTPError, self.client.create_notification_log, ['ENABLED_TOPIC_ID'], ['DISABLED_TOPIC_ID'], 'content_id', 'updated_at', 'request_id')


if __name__ == '__main__':
    unittest.main()
