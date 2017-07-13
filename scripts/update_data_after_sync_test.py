import unittest
from mock import patch, call, Mock

import update_data_after_sync


class FakeCollection(object):
    def find(self):
        return [
            {'topic_id': 'UKGOVUK_1', '_id': 'https://www.gov.uk/feed?a=b&c=d', 'created': '2013-08-01T12:53:31Z'},
            {'topic_id': 'UKGOVUK_2', '_id': 'https://www.gov.uk/pubs?w=x&y=z', 'created': '2015-02-26T09:57:35Z', 'disabled': True},
        ]

    def insert(self, *args):
        return True

    def remove(self, topic_id):
        return True

    def count(self):
        return 2


@patch.dict(update_data_after_sync.os.environ, {'GOVUK_WEBSITE_ROOT': 'https://integration.gov.uk'})
class UpdateDataAfterSyncTestCase(unittest.TestCase):
    @patch.dict(update_data_after_sync.app.config, {'GOVDELIVERY_HOSTNAME': 'omg-production'})
    def test_will_not_run_in_production(self):
        with self.assertRaises(SystemExit):
            update_data_after_sync.update_all_records()

    @patch.object(update_data_after_sync, 'logging')
    @patch.object(update_data_after_sync.db, 'topics', new_callable=FakeCollection)
    @patch.object(FakeCollection, 'remove', return_value=True)
    @patch.object(FakeCollection, 'insert', return_value=True)
    @patch.dict(update_data_after_sync.os.environ, {'GOVDELIVERY_HOSTNAME': 'stage-api.govdelivery.com'})
    @patch.dict(update_data_after_sync.app.config, {'GOVDELIVERY_ACCOUNT_CODE': 'DUPDUPDUP'})
    def test_updating_all_records(self, mock_insert_record, mock_delete_record, mock_db, mock_logging):
        update_data_after_sync.update_all_records()

        mock_logging.info.assert_has_calls([
            call('Updating 2 topics with domain integration.gov.uk and account code DUPDUPDUP'),
            call('Done')
        ])
        mock_insert_record.assert_has_calls([
            call({
                '_id': 'https://integration.gov.uk/feed?a=b&c=d',
                'topic_id': 'DUPDUPDUP_1',
                'created': '2013-08-01T12:53:31Z',
            }),
            call({
                '_id': 'https://integration.gov.uk/pubs?w=x&y=z',
                'topic_id': 'DUPDUPDUP_2',
                'created' : '2015-02-26T09:57:35Z',
                'disabled': True
            }),
        ])
        mock_delete_record.assert_has_calls([
            call({'_id': 'https://www.gov.uk/feed?a=b&c=d'}),
            call({'_id': 'https://www.gov.uk/pubs?w=x&y=z'}),
        ])
