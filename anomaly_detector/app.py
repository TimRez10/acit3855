import connexion
from connexion import NoContent
import json
import yaml
import logging
import logging.config
from pykafka import KafkaClient
import os
import datetime
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

hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])

def check_dispense_anomaly(event):
    if app_config["anomalies"]["amount_paid_threshold"] > event['amount_paid']:
        return True
    return False

def check_refill_anomaly(event):
    if app_config["anomalies"]["item_quantity_threshold"] < event['item_quantity']:
        return True
    return False

anomaly_checks = {'dispense': check_dispense_anomaly, 'refill': check_refill_anomaly}

logger.info("Dispense amount_paid anomaly threshold: %s" % app_config["anomalies"]["amount_paid_threshold"])
logger.info("Refill item_quantity anomaly threshold: %s" % app_config["anomalies"]["item_quantity_threshold"])



def get_anomalies(event_type):
    logger.info(f"GET /anomalies request is received for type {event_type}")

    find_anomalies()

    with open(app_config['datastore']['filename'], "r") as anomalies:
        data = json.load(anomalies)

    relevant_anomalies = []
    for anomaly in data:
        if anomaly['anomaly_type'] == event_type:
            relevant_anomalies.append(anomaly)

    # Sort the list by timestamp in descending order
    relevant_anomalies.sort(key=lambda x: datetime.strptime(x['timestamp'], "%Y-%m-%d %H:%M:%S"), reverse=True)

    logger.info(f"GET /anomalies request has been responded to for type {event_type}")

    return relevant_anomalies, 200

def find_anomalies():
    """ Get anomalies """
    try:
        logger.debug("Attempting to connect to Kafka at %s", hostname)
        client = KafkaClient(hosts=hostname)
    except Exception as e:
        logger.error(f"{e}")
        return e, 400
    topic = client.topics[str.encode(app_config["events"]["topic"])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,consumer_timeout_ms=1000)
    logger.info("Retrieving anomalies")
    anomaly_list = []

    try:
        for msg in consumer:
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            logger.debug(msg)
            has_anomaly = anomaly_checks[msg['type']](msg['payload'])
            if not has_anomaly:
                continue
            anomaly_list.append(msg)
    except:
        logger.error("No stats found")
        return NoContent, 404

    logger.info("Populating anomalies datastore...")
    populate_anomalies(anomaly_list)
    logger.info("Populated anomalies datastore!")


def populate_anomalies(anomaly_list):
    if not os.path.isfile(app_config['datastore']['filename']):
        data = []
    else:
        logger.debug(f"Loading {app_config['datastore']['filename']}")
        with open(app_config['datastore']['filename'], "r") as events:
            data = json.load(events)

    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for event in anomaly_list:
        if event['type'] == 'dispense':
            anomaly_item = {
                "event_id": event['payload']['id'],
                "trace_id": event['payload']['trace_id'],
                "event_type": "Dispense",
                "anomaly_type": "TooHigh",
                "description": f"The value is too high (amount paid of {event['payload']['amount_paid']} is greater than threshold of {app_config['anomalies']['amount_paid_threshold']})",
                "timestamp": current_time
            }
        elif event['type'] == 'refill':
            anomaly_item = {
                "event_id": event['payload']['id'],
                "trace_id": event['payload']['trace_id'],
                "event_type": "Refill",
                "anomaly_type": "TooLow",
                "description": f"The value is too low (item quantity of {event['payload']['item_quantity']} is lower than threshold of {app_config['anomalies']['item_quantity_threshold']})",
                "timestamp": current_time
            }
        else:
            logger.error(f"Unknown event type", event['type'])
        data.append(anomaly_item)
        logger.info(f"Anomaly with trace ID {event['payload']['trace_id']} added to list")

    with open(app_config['datastore']['filename'], "w") as events:
        logger.debug(f"Dumping anomalies to {app_config['datastore']['filename']}")
        json.dump(data, events)




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
