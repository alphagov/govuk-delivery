import unittest

from mock import patch

from partner_id_repository import PartnerIdRepository, sort_url_query


class FakeMongoCollection(object):
    def find_one(self, *args):
        pass

    def insert(self, document):
        pass

    def update(self, *args):
        pass


class PartnerIdRepositoryTestCase(unittest.TestCase):
    def setUp(self):
        self.instance = PartnerIdRepository(FakeMongoCollection())

    @patch.object(FakeMongoCollection, 'insert')
    @patch.object(PartnerIdRepository, 'current_timestamp', return_value='1234')
    def test_can_store_an_id(self, fake_datetime, fake_write):
        self.instance.store_partner_id_for_url('http://test1.com/', 'i_am_an_id')
        fake_write.assert_called_once_with({'_id': 'http://test1.com/', 'topic_id': 'i_am_an_id', 'created':'1234'})

    @patch.object(FakeMongoCollection, 'find_one', return_value={'topic_id': 'i_am_an_id'})
    def test_when_disabled_is_not_set(self, fake_read):
        response = self.instance.find_partner_id_for_url('http://test.com/')
        fake_read.assert_called_once_with({'_id': 'http://test.com/'})
        self.assertEqual(response.topic_id, 'i_am_an_id')
        self.assertFalse(response.disabled)

    @patch.object(FakeMongoCollection, 'find_one', return_value={'topic_id': 'i_am_an_id', 'disabled': False})
    def test_when_disabled_is_false(self, fake_read):
        response = self.instance.find_partner_id_for_url('http://test.com/')
        fake_read.assert_called_once_with({'_id': 'http://test.com/'})
        self.assertEqual(response.topic_id, 'i_am_an_id')
        self.assertFalse(response.disabled)

    @patch.object(FakeMongoCollection, 'find_one', return_value={'topic_id': 'i_am_an_id', 'disabled': True})
    def test_when_disabled_is_true(self, fake_read):
        response = self.instance.find_partner_id_for_url('http://test.com/')
        fake_read.assert_called_once_with({'_id': 'http://test.com/'})
        self.assertEqual(response.topic_id, 'i_am_an_id')
        self.assertTrue(response.disabled)

    @patch.object(FakeMongoCollection, 'find_one', return_value=None)
    def test_returns_none_if_url_not_found(self, fake_read):
        response = self.instance.find_partner_id_for_url('http://test.com/')
        self.assertEqual(response.topic_id, None)
        self.assertFalse(response.disabled)

    def test_url_sorting(self):
        original_url = 'http://example.com/?b=1&c=2&a=3'
        sorted_url = 'http://example.com/?a=3&b=1&c=2'
        assert sort_url_query(original_url) == sorted_url

    @patch.object(FakeMongoCollection, 'find_one', return_value=None)
    @patch.object(FakeMongoCollection, 'update', return_value=None)
    def test_update_when_disable_is_true(self, fake_update, fake_read):
        self.instance.update('TOPIC_111', disabled=True)
        fake_update.assert_called_once_with({'topic_id': 'TOPIC_111'}, {'$set': {'disabled': True}})
        fake_read.assert_called_once_with({'topic_id': 'TOPIC_111'})


    @patch.object(FakeMongoCollection, 'find_one', return_value=None)
    @patch.object(FakeMongoCollection, 'update', return_value=None)
    def test_update_when_disable_is_none(self, fake_update, fake_read):
        self.instance.update('TOPIC_111', disabled=None)
        fake_update.assert_called_once_with({'topic_id': 'TOPIC_111'}, {'$set': {'disabled': None}})
        fake_read.assert_called_once_with({'topic_id': 'TOPIC_111'})

if __name__ == '__main__':
    unittest.main()
