# GOV.UK Delivery

This service provides a way to supply a GOV.UK feed URL and email address and
set up an alert with a delivery partner. It allows GOV.UK applications that provide
feeds and want subscription features to solely care about the email address and
the feed URL, rather than needing to know about the delivery partner who manage
the database of subscribers and alerts.

At present it's tailored to GovDelivery but it could in theory wrap other such
services. It holds a database mapping a GOV.UK feed URL to a 'partner_id' that is
the ID for that feed's matching newsletter in the partner system.

## Running the service

The service runs as a [Flask](http://flask.pocoo.org/) application written in Python.
It uses redis for queueing (with celery) and mongodb for persistence.

Installing redis is an exercise left to the reader (but please run it on port
6379).

## Development

Run `./startup.sh` to set up a [virtualenv](https://pypi.python.org/pypi/virtualenv),
install all dependencies and run the app. You can also use bowler to run the app
and celery workers:

    vagrant@development:/var/govuk/development$ bowl govuk-delivery govuk-delivery-worker

You can run the tests using the same virtualenv by running `./venv/bin/nosetests`.
