import unittest
from mock import patch, call, Mock

import topic_deleter

class FakeCollection(object):
    def find(self, query):
        return [
            {'topic_id': 1, '_id': 'url/one'},
            {'topic_id': 2, '_id': 'url/two'},
            {'topic_id': 3, '_id': 'url/three'},
            {'topic_id': 4, '_id': 'url/four'}
        ]

    def remove(self, topic_id):
        return True


@patch.object(topic_deleter, 'logging')
@patch.object(topic_deleter.db, 'topics', new_callable=FakeCollection)
class DeleteTopicsWithSubscribersTestCase(unittest.TestCase):
    @staticmethod
    def _get_topic_count(record):
        if record['topic_id'] == 1:
            return ('topic not found', record)
        else:
            return (record['topic_id'] % 2, record)

    def _delete_topic(self, record):
        self.deleted_topics.append(record['topic_id'])

    def setUp(self):
        self.deleted_topics = []


    @patch('__builtin__.raw_input', return_value='')
    def test_listing_topics_with_no_subscribers_and_missing_topics_without_deleting_them(self, mock_input, finder_mock, mock_logging):
        topic_deleter.delete_topics_without_subscribers(self._get_topic_count, self._delete_topic)
        mock_logging.warning.assert_has_calls([
            call('2 topics have no subscriptions'),
            call('2: url/two'),
            call('4: url/four'),
            call("1 topics don't exist in GovDelivery"),
            call('1: url/one'),
        ])
        self.assertEqual(self.deleted_topics, [])


    @patch('__builtin__.raw_input', return_value='delete')
    def test_listing_topics_with_no_subscribers_and_missing_topics_and_deleting_them(self, mock_input, finder_mock, mock_logging):
        topic_deleter.delete_topics_without_subscribers(self._get_topic_count, self._delete_topic)
        mock_logging.warning.assert_has_calls([
            call('2 topics have no subscriptions'),
            call('2: url/two'),
            call('4: url/four'),
            call("1 topics don't exist in GovDelivery"),
            call('1: url/one'),
            call('Successfully deleted 3 topics')
        ])
        self.assertEqual(self.deleted_topics, [2, 4, 1])

    @patch('__builtin__.raw_input', return_value='delete')
    def test_does_not_delete_topics_that_have_a_none_subscriber_count(self, mock_input, finder_mock, mock_logging):
        def _get_topic_count(record):
            if record['topic_id'] % 2:
                return (1, record)
            else:
                return (None, record)

        topic_deleter.delete_topics_without_subscribers(_get_topic_count, self._delete_topic)
        mock_logging.warning.assert_has_calls([
            call('0 topics have no subscriptions'),
            call('2 topics with errors - THESE ARE NOT BEING DELETED'),
            call('2: url/two'),
            call('4: url/four'),
            call('Successfully deleted 0 topics')
        ])
        self.assertEqual(self.deleted_topics, [])

class GetTopicCountTestCase(unittest.TestCase):
    @patch.object(topic_deleter.delivery_partner, 'read_topic', return_value={ 'topic': {'subscribers-count': {'#text': '3'} } })
    def test_returns_the_subscriber_count_from_the_delivery_partner(self, mock_read_topic):
        record = Mock(**{'get.return_value': 'TOPIC_ID'})
        self.assertEqual((3, record), topic_deleter.get_topic_count(record))
        mock_read_topic.assert_called_once_with('TOPIC_ID')


    @patch.object(topic_deleter.delivery_partner, 'read_topic', side_effect=Exception('fail'))
    def test_returns_a_none_count_when_an_error_is_raised_by_the_delivery_provider(self, mock_read_topic):
        record = Mock(**{'get.return_value': 'TOPIC_ID'})
        self.assertEqual((None, record), topic_deleter.get_topic_count(record))
        mock_read_topic.assert_called_once_with('TOPIC_ID')

@patch.object(topic_deleter, 'logging')
class DeleteTopicTestCase(unittest.TestCase):
    @patch.object(topic_deleter.delivery_partner, 'read_topic', return_value={ 'topic': {'subscribers-count': {'#text': '0'} } })
    @patch.object(topic_deleter.delivery_partner, 'delete_topic', return_value=True)
    @patch.object(topic_deleter.db, 'topics', new_callable=FakeCollection)
    @patch.object(FakeCollection, 'remove', return_value=True)
    def test_deletes_topics_that_have_no_subscribers_with_delivery_partner(self, mock_delete_record, fake_collection, mock_delete_topic, mock_read_topic, mock_logging):
        record = Mock(**{'get.return_value': 'TOPIC_ID'})
        topic_deleter.delete_topic(record)
        mock_delete_record.assert_called_once_with({'topic_id': 'TOPIC_ID'})
        mock_delete_topic.assert_called_once_with('TOPIC_ID')
        mock_logging.warning.assert_called_once_with('Deleting TOPIC_ID')

    @patch.object(topic_deleter.delivery_partner, 'read_topic', side_effect=Exception('HTTP status: 404\nGD-14002\nTopic not found'))
    @patch.object(topic_deleter.delivery_partner, 'delete_topic', return_value=True)
    @patch.object(topic_deleter.db, 'topics', new_callable=FakeCollection)
    @patch.object(FakeCollection, 'remove', return_value=True)
    def test_deletes_topics_that_do_not_exist_on_delivery_partner(self, mock_delete_record, fake_collection, mock_delete_topic, mock_read_topic, mock_logging):
        record = Mock(**{'get.return_value': 'TOPIC_ID'})
        topic_deleter.delete_topic(record)
        mock_delete_record.assert_called_once_with({'topic_id': 'TOPIC_ID'})
        self.assertEqual(0, mock_delete_topic.call_count)
        mock_logging.warning.assert_called_once_with('Deleting TOPIC_ID')

    @patch.object(topic_deleter.delivery_partner, 'read_topic', return_value={ 'topic': {'subscribers-count': {'#text': '3'} } })
    def test_do_not_delete_topics_with_subscribers_on_delivery_partner(self, mock_read_topic, mock_logging):
        record = Mock(**{'get.return_value': 'TOPIC_ID'})
        topic_deleter.delete_topic(record)
        mock_logging.warning.assert_called_once_with('Skipping TOPIC_ID as it now has 3 subscribers')

    @patch.object(topic_deleter.delivery_partner, 'read_topic', side_effect=Exception('fail'))
    def test_do_not_delete_topics_that_error_on_delivery_partner(self, mock_read_topic, mock_logging):
        record = Mock(**{'get.return_value': 'TOPIC_ID'})
        topic_deleter.delete_topic(record)
        mock_logging.warning.assert_called_once_with('Skipping TOPIC_ID as we got an error from GovDelivery')
