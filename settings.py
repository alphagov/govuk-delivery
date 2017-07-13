# GovDelivery Service Settings

DEBUG = True

# API settings

GOVDELIVERY_USERNAME = 'username'
GOVDELIVERY_PASSWORD = 'password'
GOVDELIVERY_ACCOUNT_CODE = 'UKGOVUKDUP'
GOVDELIVERY_HOSTNAME = 'stage-api.govdelivery.com'
GOVDELIVERY_SIGNUP_FORM = 'https://stage-public.govdelivery.com/accounts/UKGOVUKDUP/subscriber/new?topic_id=%s'

NOTIFICATION_LOG_HOSTNAME = 'email-alert-api.dev.gov.uk'
NOTIFICATION_LOG_PROTOCOL = 'http'

REDIS_SETTINGS = {
    'host': 'localhost',
    'port': 6379,
    'db': 0
}

MONGODB_SETTINGS = {
    'host': 'localhost',
    'port': 27017
}

LIST_TITLE_FORMAT = '%s'

USE_BACKGROUND_WORKERS = False
