#!/bin/bash
set -e

DIRECTORY='venv'
if [ ! -d "$DIRECTORY" ]; then
  virtualenv --no-site-packages "$DIRECTORY"
fi

$DIRECTORY/bin/pip install -qr requirements.txt
$DIRECTORY/bin/pip install -qr requirements-test.txt

$DIRECTORY/bin/python service.py
