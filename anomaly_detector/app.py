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
    app_conf_file = "/config/app_conf.yaml"
    log_conf_file = "/config/log_conf.yaml"
else:
    print("In Dev Environment")
    app_conf_file = "app_conf.yaml"
    log_conf_file = "log_conf.yaml"

with open(app_conf_file, 'r') as f:
    app_config = yaml.safe_load(f.read())

# External Logging Configuration
with open(log_conf_file, 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

logger.info("App Conf File: %s" % app_conf_file)
logger.info("Log Conf File: %s" % log_conf_file)

### KAFKA CONNECTION ###
hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])
retries = app_config["events"]["retries"]
retry_count = 0
while retry_count < retries:
    try:
        logger.debug("Attempting to connect to Kafka at %s", hostname)
        client = KafkaClient(hosts=hostname)
        logger.debug("Connected to Kafka at %s", hostname)
        topic = client.topics[str.encode(app_config["events"]["topic"])]
        consumer = topic.get_simple_consumer(
            consumer_group=b'event_group',
            reset_offset_on_start=False,
            auto_offset_reset=OffsetType.LATEST
        )
        break
    except Exception as e:
        time.sleep(app_config["events"]["sleep_time"])
        retry_count += 1
        logger.error(f"{e}. {retries-retry_count} out of {retries} retries remaining.")
    if retry_count == retries:
        logger.info(f"Can't connect to Kafka. Exiting...")
        sys.exit()

# Read existing data
if not os.path.isfile(app_config['datastore']['filename']):
    data = []
else:
    with open(app_config['datastore']['filename'], "r") as events:
        data = json.load(events)

hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])


# Anomaly Detection Functions
def check_dispense_anomaly(event):
    """
    Check if a dispense event contains an anomaly based on amount paid.
    """
    return app_config["anomalies"]["amount_paid_threshold"] < event['amount_paid']


def check_refill_anomaly(event):
    """
    Check if a refill event contains an anomaly based on item quantity.
    """
    return app_config["anomalies"]["item_quantity_threshold"] > event['item_quantity']

anomaly_checks = {
    'dispense': check_dispense_anomaly,
    'refill': check_refill_anomaly
}


# Data Processing Functions
def populate_anomalies(anomaly_list):
    """
    Store detected anomalies in the JSON datastore.
    """
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    existing_trace_ids = {item['trace_id'] for item in data}
    new_anomalies = 0

    for event in anomaly_list:
        anomaly_item = None
        if event['type'] == 'dispense':
            anomaly_item = {
                "event_id": str(uuid.uuid4()),
                "trace_id": event['payload']['trace_id'],
                "event_type": "Dispense",
                "anomaly_type": "TooHigh",
                "description": f"The value is too high (amount paid of {event['payload']['amount_paid']} is greater than threshold of {app_config['anomalies']['amount_paid_threshold']})",
                "timestamp": current_time
            }
        elif event['type'] == 'refill':
            anomaly_item = {
                "event_id": str(uuid.uuid4()),
                "trace_id": event['payload']['trace_id'],
                "event_type": "Refill",
                "anomaly_type": "TooLow",
                "description": f"The value is too low (item quantity of {event['payload']['item_quantity']} is lower than threshold of {app_config['anomalies']['item_quantity_threshold']})",
                "timestamp": current_time
            }
        else:
            logger.error(f"Unknown event type: {event['type']}")
            continue

        if anomaly_item and anomaly_item['trace_id'] not in existing_trace_ids:
            data.append(anomaly_item)
            existing_trace_ids.add(anomaly_item['trace_id'])
            logger.info(f"Added new anomaly with trace ID {event['payload']['trace_id']}")
            new_anomalies+=1
        else:
            logger.info(f"Skipped duplicate anomaly with trace ID {event['payload']['trace_id']}")

    # Write updated data
    with open(app_config['datastore']['filename'], "w") as events:
        logger.info(f"Writing {new_anomalies} new anomalies to {app_config['datastore']['filename']}")
        json.dump(data, events)


def find_anomalies():
    """
    Consume events from Kafka and detect anomalies.
    """
    logger.info("Starting anomaly detection process")
    anomaly_list = []

    try:
        for msg in consumer:
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            logger.debug(f"Processing event: {msg}")

            has_anomaly = anomaly_checks[msg['type']](msg['payload'])
            if has_anomaly:
                anomaly_list.append(msg)
                logger.info(f"Detected anomaly in {msg['type']} event")
    except Exception as e:
        logger.error(f"Error processing Kafka messages: {e}")
        return NoContent, 404

    logger.info(f"Detected {len(anomaly_list)} anomalies in total")

    try:
        logger.info("Storing detected anomalies...")
        populate_anomalies(anomaly_list)
    except Exception as e:
        logger.error(f"Failed to store anomalies: {e}")
        return e, 400

    logger.info("Successfully completed anomaly detection process")


# Endpoint Function
def get_anomalies(anomaly_type):
    """
    Retrieve anomalies of a specific type from the datastore.
    """
    logger.info(f"Processing GET /anomalies request for type: {anomaly_type}")

    if len(consumer) > 0:
        find_anomalies()

    try:
        with open(app_config['datastore']['filename'], "r") as anomalies:
            data = json.load(anomalies)

        relevant_anomalies = [
            anomaly for anomaly in data if anomaly['anomaly_type'] == anomaly_type
        ]

        # Sort by newest to oldest
        relevant_anomalies.sort(
            key=lambda x: datetime.strptime(x['timestamp'], "%Y-%m-%d %H:%M:%S"),
            reverse=True
        )

        logger.info(f"Found {len(relevant_anomalies)} matching anomalies")
        return relevant_anomalies, 200

    except Exception as e:
        logger.error(f"Error retrieving anomalies: {e}")
        return e, 400


logger.info(f"Dispense amount_paid anomaly threshold: {app_config['anomalies']['amount_paid_threshold']}")
logger.info(f"Refill item_quantity anomaly threshold: {app_config['anomalies']['item_quantity_threshold']}")


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
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8120)