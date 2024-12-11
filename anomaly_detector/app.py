"""
Anomaly Detection Service for Processing Kafka Events

- Consumes Kafka events
- Detects anomalies based on predefined thresholds
- Stores anomalies in a JSON datastore
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


# Anomaly Detection Functions
def check_dispense_anomaly(event):
    """
    Check if a dispense event contains an anomaly based on amount paid.
    """
    return APP_CONFIG["anomalies"]["amount_paid_threshold"] < event['amount_paid']  # Too High

def check_refill_anomaly(event):
    """
    Check if a refill event contains an anomaly based on item quantity.
    """
    return APP_CONFIG["anomalies"]["item_quantity_threshold"] > event['item_quantity']  # Too Low

ANOMALY_CHECKS = {
    'dispense': check_dispense_anomaly,
    'refill': check_refill_anomaly
}


# Data Processing Functions
def find_anomalies():
    """
    Consume events from Kafka and detect anomalies.
    """
    LOGGER.info("Starting anomaly detection process")
    anomaly_list = []

    try:
        for msg in consumer:
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            LOGGER.debug("Processing event: %s", msg)

            has_anomaly = ANOMALY_CHECKS[msg['type']](msg['payload'])
            if has_anomaly:
                anomaly_list.append(msg)
                LOGGER.info("Detected anomaly in %s event", msg['type'])

        if anomaly_list:
            populate_anomalies(anomaly_list)

        return NoContent, 200
    except (json.JSONDecodeError, KeyError, Exception) as e:
        LOGGER.error("Error processing Kafka messages: %s", e)
        return NoContent, 404


def populate_anomalies(anomaly_list):
    """
    Store detected anomalies in the JSON datastore.
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing_trace_ids = {item['trace_id'] for item in data}
    new_anomalies = 0

    for event in anomaly_list:
        try:
            if event['type'] == 'dispense':
                anomaly_item = {
                    "event_id": str(
                        uuid.uuid4()),
                    "trace_id": event['payload']['trace_id'],
                    "event_type": "Dispense",
                    "anomaly_type": "TooHigh",
                    "description": f"The value is too high (amount paid of {event['payload']['amount_paid']} is greater than threshold of {APP_CONFIG['anomalies']['amount_paid_threshold']})",
                    "timestamp": current_time}
            elif event['type'] == 'refill':
                anomaly_item = {
                    "event_id": str(
                        uuid.uuid4()),
                    "trace_id": event['payload']['trace_id'],
                    "event_type": "Refill",
                    "anomaly_type": "TooLow",
                    "description": f"The value is too low (item quantity of {event['payload']['item_quantity']} is lower than threshold of {APP_CONFIG['anomalies']['item_quantity_threshold']})",
                    "timestamp": current_time}
            else:
                LOGGER.error("Unknown event type: %s", event['type'])
                continue

            if anomaly_item and anomaly_item['trace_id'] not in existing_trace_ids:
                data.append(anomaly_item)
                existing_trace_ids.add(anomaly_item['trace_id'])
                LOGGER.info("Added new %s anomaly with trace ID %s",
                            anomaly_item['anomaly_type'],
                            anomaly_item['trace_id'])
                new_anomalies += 1
            else:
                LOGGER.info("Skipped duplicate %s anomaly with trace ID %s",
                            anomaly_item['anomaly_type'],
                            anomaly_item['trace_id'])
        except KeyError as e:
            LOGGER.error("Missing key in event: %s", e)

    # Write updated data
    with open(APP_CONFIG['datastore']['filename'], "w", encoding='utf-8') as event_file:
        LOGGER.info("Writing %s new anomalies to %s",
                    new_anomalies,
                    APP_CONFIG['datastore']['filename'])
        json.dump(data, event_file)


# GET Endpoint function
def get_anomalies(anomaly_type):
    """
    Retrieve anomalies of a specific type from the datastore.
    """
    LOGGER.info("Processing GET /anomalies request for type: %s", anomaly_type)
    find_anomalies()

    try:
        relevant_anomalies = [
            anomaly for anomaly in data if anomaly['anomaly_type'] == anomaly_type]

        # Sort by newest to oldest
        relevant_anomalies.sort(
            key=lambda x: datetime.strptime(
                x['timestamp'],
                "%Y-%m-%d %H:%M:%S"),
            reverse=True)

        LOGGER.info("GET /anomalies response: found %s %s anomalies",
                    len(relevant_anomalies),
                    anomaly_type)
        return relevant_anomalies, 200
    except Exception as e:
        LOGGER.error("Error retrieving anomalies: %s", e)
        return [], 400


LOGGER.info(f"Dispense amount_paid anomaly threshold: {APP_CONFIG['anomalies']['amount_paid_threshold']}")
LOGGER.info(f"Refill item_quantity anomaly threshold: {APP_CONFIG['anomalies']['item_quantity_threshold']}")


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
    base_path="/anomaly_detector",
    strict_validation=True,
    validate_responses=True
)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8120)
