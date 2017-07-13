import requests
import json

class NotificationLog(object):
    def __init__(self, hostname='email-alert-api.dev.gov.uk', protocol='http'):
        self.hostname = hostname
        self.protocol = protocol

    def _api_url(self):
        url = '%s://%s/notification_logs.json' % (self.protocol, self.hostname)
        return url

    def _post(self, params):
        response = requests.post(self._api_url(), data=json.dumps(params), headers={'content-type': 'application/json'})
        return self._parse_response(response)

    def _parse_response(self, response):
        response.raise_for_status()
        return response.json()

    def create_notification_log(self, enabled_gov_delivery_ids, disabled_gov_delivery_ids, content_id, public_updated_at, govuk_request_id):
        post_data = {
            'gov_delivery_ids': enabled_gov_delivery_ids + disabled_gov_delivery_ids, # kept for backwards compatibility with EmailAlertApi
            'enabled_gov_delivery_ids': enabled_gov_delivery_ids,
            'disabled_gov_delivery_ids': disabled_gov_delivery_ids,
            'content_id': content_id,
            'public_updated_at': public_updated_at,
            'govuk_request_id': govuk_request_id,
            'emailing_app': 'gov_uk_delivery',
            'publishing_app': 'whitehall'
        }
        return self._post(post_data)
