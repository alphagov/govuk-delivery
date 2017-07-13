import urlparse
import urllib
import datetime

from collections import OrderedDict, namedtuple

FindResponse = namedtuple('Response', ['topic_id', 'disabled'])

def sort_url_query(url):
    """Returns a copy of the passed in URL with the query string
    parameters sorted."""
    parsed_url = urlparse.urlparse(url)
    query_params = urlparse.parse_qs(parsed_url.query)
    query_params = OrderedDict(sorted(query_params.items()))
    return urlparse.urlunparse([parsed_url[0],
                                parsed_url[1],
                                parsed_url[2],
                                parsed_url[3],
                                urllib.urlencode(query_params, True),
                                parsed_url[5]])


class PartnerIdRepository(object):
    def __init__(self, db_collection):
        self.collection = db_collection

    def current_timestamp(self):
        return datetime.datetime.utcnow()

    def find_partner_id_for_url(self, feed_url):
        query = {'_id': sort_url_query(feed_url)}
        result = self.collection.find_one(query)
        if result:
            return FindResponse(result.get('topic_id'), True if result.get('disabled') else False)
        return FindResponse(None, None)

    def store_partner_id_for_url(self, feed_url, partner_id):
        return self.collection.insert({
            '_id'      : sort_url_query(feed_url),
            'topic_id' : partner_id,
            'created'  : self.current_timestamp()
        })

    def update(self, gov_delivery_id, disabled):
        query = {'topic_id': gov_delivery_id}
        self.collection.update(
            query,
            {"$set": {'disabled': disabled}}
        )
        return self.collection.find_one(query)
