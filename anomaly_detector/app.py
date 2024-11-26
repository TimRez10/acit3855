import connexion
from connexion import NoContent
import json
import yaml
import time
import sys
import logging
import logging.config
from pykafka import KafkaClient
from pykafka.common import OffsetType
import os
from datetime import datetime
import uuid
from connexion.middleware import MiddlewarePosition
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
with open(APP_CONF_FILE, 'r') as f:
    APP_CONFIG = yaml.safe_load(f.read())

# Logging Configuration
with open(LOG_CONF_FILE, 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

LOGGER = logging.getLogger('basicLogger')
LOGGER.info("App Conf File: %s" % APP_CONF_FILE)
LOGGER.info("Log Conf File: %s" % LOG_CONF_FILE)

### KAFKA CONNECTION ###
HOSTNAME = "%s:%d" % (APP_CONFIG["events"]["hostname"], APP_CONFIG["events"]["port"])
RETRIES = APP_CONFIG["events"]["retries"]
retry_count = 0
while retry_count < RETRIES:
    try:
        LOGGER.debug("Attempting to connect to Kafka at %s", HOSTNAME)
        client = KafkaClient(hosts=HOSTNAME)
        LOGGER.debug("Connected to Kafka at %s", HOSTNAME)
        topic = client.topics[str.encode(APP_CONFIG["events"]["topic"])]
        consumer = topic.get_simple_consumer(
            consumer_timeout_ms=1000,
            reset_offset_on_start=False,
            auto_offset_reset=OffsetType.LATEST
        )
        break
    except Exception as e:
        time.sleep(APP_CONFIG["events"]["sleep_time"])
        retry_count += 1
        LOGGER.error(f"{e}. {RETRIES-retry_count} out of {RETRIES} retries remaining.")
    if retry_count == RETRIES:
        LOGGER.info(f"Can't connect to Kafka. Exiting...")
        sys.exit()

# Read existing data
if not os.path.isfile(APP_CONFIG['datastore']['filename']):
    data = []
else:
    with open(APP_CONFIG['datastore']['filename'], "r") as events:
        data = json.load(events)


# Anomaly Detection Functions
def check_dispense_anomaly(event):
    """
    Check if a dispense event contains an anomaly based on amount paid.
    """
    return APP_CONFIG["anomalies"]["amount_paid_threshold"] < event['amount_paid'] # Too High


def check_refill_anomaly(event):
    """
    Check if a refill event contains an anomaly based on item quantity.
    """
    return APP_CONFIG["anomalies"]["item_quantity_threshold"] > event['item_quantity'] # Too Low

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
            LOGGER.debug(f"Processing event: {msg}")

            has_anomaly = ANOMALY_CHECKS[msg['type']](msg['payload'])
            if has_anomaly:
                anomaly_list.append(msg)
                LOGGER.info(f"Detected anomaly in {msg['type']} event")
    except Exception as e:
        LOGGER.error(f"Error processing Kafka messages: {e}")
        return NoContent, 404

    LOGGER.info(f"Detected {len(anomaly_list)} anomalies from Kafka consumer")

    try:
        LOGGER.info("Storing detected anomalies...")
        populate_anomalies(anomaly_list)
    except Exception as e:
        LOGGER.error(f"Failed to store anomalies: {e}")
        return e, 400

    LOGGER.info("Successfully completed anomaly detection process")


def populate_anomalies(anomaly_list):
    """
    Store detected anomalies in the JSON datastore.
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing_trace_ids = {item['trace_id'] for item in data}
    new_anomalies = 0

    for event in anomaly_list:
        if event['type'] == 'dispense':
            anomaly_item = {
                "event_id": str(uuid.uuid4()),
                "trace_id": event['payload']['trace_id'],
                "event_type": "Dispense",
                "anomaly_type": "TooHigh",
                "description": f"The value is too high (amount paid of {event['payload']['amount_paid']} is greater than threshold of {APP_CONFIG['anomalies']['amount_paid_threshold']})",
                "timestamp": current_time
            }
        elif event['type'] == 'refill':
            anomaly_item = {
                "event_id": str(uuid.uuid4()),
                "trace_id": event['payload']['trace_id'],
                "event_type": "Refill",
                "anomaly_type": "TooLow",
                "description": f"The value is too low (item quantity of {event['payload']['item_quantity']} is lower than threshold of {APP_CONFIG['anomalies']['item_quantity_threshold']})",
                "timestamp": current_time
            }
        else:
            LOGGER.error(f"Unknown event type: {event['type']}")
            continue

        if anomaly_item and anomaly_item['trace_id'] not in existing_trace_ids:
            data.append(anomaly_item)
            existing_trace_ids.add(anomaly_item['trace_id'])
            LOGGER.info(f"Added new {anomaly_item['anomaly_type']} anomaly with trace ID {anomaly_item['trace_id']}")
            new_anomalies+=1
        else:
            LOGGER.info(f"Skipped duplicate {anomaly_item['anomaly_type']} anomaly with trace ID {anomaly_item['anomaly_type']}")

    # Write updated data
    with open(APP_CONFIG['datastore']['filename'], "w") as events:
        LOGGER.info(f"Writing {new_anomalies} new anomalies to {APP_CONFIG['datastore']['filename']}")
        json.dump(data, events)


# Endpoint Function
def get_anomalies(anomaly_type):
    """
    Retrieve anomalies of a specific type from the datastore.
    """
    LOGGER.info(f"Processing GET /anomalies request for type: {anomaly_type}")
    find_anomalies()

    try:
        relevant_anomalies = [
            anomaly for anomaly in data if anomaly['anomaly_type'] == anomaly_type
        ]

        # Sort by newest to oldest
        relevant_anomalies.sort(
            key=lambda x: datetime.strptime(x['timestamp'], "%Y-%m-%d %H:%M:%S"),
            reverse=True
        )

        LOGGER.info(f"GET /anomalies response: found {len(relevant_anomalies)} {anomaly_type} anomalies")
        return relevant_anomalies, 200
    except Exception as e:
        LOGGER.error(f"Error retrieving anomalies: {e}")
        return e, 400


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

app.add_api("openapi.yaml", base_path="/anomaly_detector", strict_validation=True, validate_responses=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8120)