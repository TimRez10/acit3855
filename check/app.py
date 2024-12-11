"""
Final exam service
"""

import json
import os
import logging
import logging.config

import requests
from requests.exceptions import Timeout, ConnectionError
import yaml
import connexion
from connexion import NoContent
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler

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


RECEIVER_URL = APP_CONFIG['url']['receiver']
STORAGE_URL = APP_CONFIG['url']['storage']
PROCESSING_URL = APP_CONFIG['url']['processing']
ANALYZER_URL = APP_CONFIG['url']['analyzer']
TIMEOUT = APP_CONFIG['timeout']

# Processing functions
def check_services():
    """ Called periodically """
    receiver_status = "Unavailable"
    try:
        response = requests.get(RECEIVER_URL, timeout=TIMEOUT)
        if response.status_code == 200:
            receiver_status = "Healthy"
            LOGGER.info("Receiver is Healthly")
        else:
            LOGGER.info("Receiver returning non-200 response")
    except (Timeout, ConnectionError):
        LOGGER.info("Receiver is Not Available")

    storage_status = "Unavailable"
    try:
        response = requests.get(STORAGE_URL, timeout=TIMEOUT)
        if response.status_code == 200:
            response = response.json()
            storage_status = f"Storage has {response['num_dispense']} Dispenses and {response['num_refill']} Refill events"
            LOGGER.info("Storage is Healthy")
        else:
            LOGGER.info("Storage returning non-200 response")
    except (Timeout, ConnectionError):
        LOGGER.info("Storage is Not Available")

    analyzer_status = "Unavailable"
    try:
        response = requests.get(ANALYZER_URL, timeout=TIMEOUT)
        if response.status_code == 200:
            response = response.json()
            analyzer_status = f"Analyzer has {response['num_dispense']} Dispenses and {response['num_refill']} Refill events"
            LOGGER.info("Analyzer is Healthy")
        else:
            LOGGER.info("Analyzer returning non-200 response")
    except (Timeout, ConnectionError):
        LOGGER.info("Analyzer is Not Available")

    processing_status = "Unavailable"
    try:
        response = requests.get(PROCESSING_URL, timeout=TIMEOUT)
        if response.status_code == 200:
            response = response.json()
            processing_status = f"Processing has {response['num_dispense_records']} Dispenses and {response['num_refill_records']} Refill events"
            LOGGER.info("Processing is Healthy")
        else:
            LOGGER.info("Processing returning non-200 response")
    except (Timeout, ConnectionError):
        LOGGER.info("Processing is Not Available")

    data = {
        'receiver': receiver_status,
        'storage': storage_status,
        'processing': processing_status,
        'analyzer': analyzer_status
    }

    # Write updated data
    with open(APP_CONFIG['datastore']['filename'], "w", encoding='utf-8') as event_file:
        LOGGER.info("Updating file %s", APP_CONFIG['datastore']['filename'])
        json.dump(data, event_file)

# Endpoint functions
def get_checks():
    try:
        if os.path.isfile(APP_CONFIG['datastore']['filename']):
            with open(APP_CONFIG['datastore']['filename'], "r", encoding='utf-8') as event_file:
                return json.load(event_file)
    except:
        return "File not found", 404


# Application Setup
def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(check_services,'interval',seconds=APP_CONFIG['scheduler']['period_sec'])

    sched.start()

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
    base_path="/check",
    strict_validation=True,
    validate_responses=True
)
if __name__ == "__main__":
    init_scheduler()
    app.run(host="0.0.0.0", port=8130)
