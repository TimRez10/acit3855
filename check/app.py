"""
Final exam service
"""

import json
import os
import sys
import time
import uuid
from datetime import datetime
import logging
import logging.config

import yaml
import connexion
from connexion import NoContent
from connexion.middleware import MiddlewarePosition
from pykafka import KafkaClient
from pykafka.common import OffsetType
from pykafka.exceptions import UnknownTopicOrPartition
from starlette.middleware.cors import CORSMiddleware

if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    APP_CONF_FILE = "/config/app_conf.yaml"
    LOG_CONF_FILE = "/config/log_conf.yaml"
else:
    print("In Dev Environment")
    APP_CONF_FILE = "app_conf.yaml"
    LOG_CONF_FILE = "log_conf.yaml"

# App Configuration
with open(APP_CONF_FILE, 'r', encoding='utf-8') as f:
    APP_CONFIG = yaml.safe_load(f.read())

# Logging Configuration
with open(LOG_CONF_FILE, 'r', encoding='utf-8') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

LOGGER = logging.getLogger('basicLogger')
LOGGER.info(f"App Conf File: {APP_CONF_FILE}")
LOGGER.info(f"Log Conf File: {LOG_CONF_FILE}")

### KAFKA CONNECTION ###
HOSTNAME = f"{APP_CONFIG['events']['hostname']}:{APP_CONFIG['events']['port']}"
RETRIES = APP_CONFIG["events"]["retries"]
retry_count = 0
while retry_count < RETRIES:
    try:
        LOGGER.debug(f"Attempting to connect to Kafka at {HOSTNAME}")
        client = KafkaClient(hosts=HOSTNAME)
        LOGGER.debug(f"Connected to Kafka at {HOSTNAME}")
        topic = client.topics[str.encode(APP_CONFIG["events"]["topic"])]
        consumer = topic.get_simple_consumer(
            consumer_timeout_ms=1000,
            reset_offset_on_start=False,
            auto_offset_reset=OffsetType.LATEST
        )
        break
    except (ConnectionError, TimeoutError, UnknownTopicOrPartition) as e:
        time.sleep(APP_CONFIG["events"]["sleep_time"])
        retry_count += 1
        LOGGER.error(f"{e}. {RETRIES-retry_count} out of {RETRIES} retries remaining.")
    if retry_count == RETRIES:
        LOGGER.info("Can't connect to Kafka. Exiting...")
        sys.exit()

# Read datastore and store it in a global variable.
# This is so I don't have to re-read the file every time the populate_anomalies function is run.
if not os.path.isfile(APP_CONFIG['datastore']['filename']):
    data = []
else:
    with open(APP_CONFIG['datastore']['filename'], "r", encoding='utf-8') as event_file:
        data = json.load(event_file)

# Endpoint functions here

# Application Setup
app = connexion.FlaskApp(__name__, specification_dir='')
app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_api(
    "openapi.yaml",
    base_path="/final",
    strict_validation=True,
    validate_responses=True
)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8130)
