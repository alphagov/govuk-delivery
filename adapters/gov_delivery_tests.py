import unittest

from httpretty import HTTPretty
from mock import Mock

from gov_delivery import GovDeliveryClient


class GovDeliveryClientHTTPTests(unittest.TestCase):
    def setUp(self):
        HTTPretty.enable()
        self.client = GovDeliveryClient('test', 'test', 'TESTCODE', hostname='test.example.com')

    def tearDown(self):
        HTTPretty.disable()

    def _api_url(self, path):
        return 'https://test.example.com/api/account/TESTCODE/%s.xml' % path


class GovDeliveryClientTopicTests(GovDeliveryClientHTTPTests):
    def test_read_topic_makes_get_request(self):
        HTTPretty.register_uri(
            HTTPretty.GET,
            self._api_url('topics/TOPIC_ID')
        )
        self.client.read_topic('TOPIC_ID')
        assert HTTPretty.last_request.method == 'GET'

    def test_read_topic_passes_through_body(self):
        HTTPretty.register_uri(
            HTTPretty.GET,
            self._api_url('topics/TOPIC_ID'),
            body="TEST THINGS"
        )
        body = self.client.read_topic('TOPIC_ID')
        assert "TEST THINGS" == body

    def test_read_topic_parses_xml(self):
        HTTPretty.register_uri(
            HTTPretty.GET,
            self._api_url('topics/TOPIC_ID'),
            content_type='application/xml'
        )
        self.client.parse_xml_content = Mock(return_value={})
        body = self.client.read_topic('TOPIC_ID')
        assert {} == body

    def test_update_topic_categories_makes_put_request(self):
        HTTPretty.register_uri(
            HTTPretty.PUT,
            self._api_url('topics/TOPIC_ID/categories'),
            content_type='application/xml'
        )
        self.client.update_topic_categories('TOPIC_ID', ['CATEGORY_ID'])
        assert HTTPretty.last_request.method == 'PUT'


class GovDeliveryClientSubscriberTests(GovDeliveryClientHTTPTests):
    def test_read_subcriber_makes_get_request(self):
        HTTPretty.register_uri(
            HTTPretty.GET,
            self._api_url('subscribers/bWVAZXhhbXBsZS5jb20%3D')
        )
        self.client.read_subscriber('me@example.com')
        assert HTTPretty.last_request.method == 'GET'

    def test_create_subscriber_makes_post_request(self):
        HTTPretty.register_uri(
            HTTPretty.POST,
            self._api_url('subscribers')
        )
        self.client.create_subscriber('me@example.com')
        assert HTTPretty.last_request.method == 'POST'


if __name__ == '__main__':
    unittest.main()
