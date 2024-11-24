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
    if app_config["anomalies"]["amount_paid_threshold"]  > event['amount_paid']:
        return True
    return False

def check_refill_anomaly(event):
    if app_config["anomalies"]["item_quantity_threshold"] > event['item_quantity']:
        return True
    return False

anomaly_checks = {'dispense': check_dispense_anomaly, 'refill': check_refill_anomaly}

logger.info("Dispense amount_paid anomaly threshold: %s" % app_config["anomalies"]["amount_paid_threshold"])
logger.info("Refill item_quantity anomaly threshold: %s" % app_config["anomalies"]["item_quantity_threshold"])

def get_anomalies():
    """ Get anomalies """
    logger.info("GET /anomalies request is received")
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

    populate_anomalies(anomaly_list)

    with open(app_config['datastore']['filename'], "r") as events:
        data = json.load(events)

    logger.info("GET /anomalies request has been responded to")

    return data, 200

def populate_anomalies(anomaly_list):
    if not os.path.isfile(app_config['datastore']['filename']):
        data = []
    else:
        with open(app_config['datastore']['filename'], "r") as events:
            data = json.load(events)

    current_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    for event in anomaly_list:
        if event['type'] == 'dispense':
            anomaly_item = {
                "event_id": event['payload']['id'],
                "trace_id": event['payload']['trace_id'],
                "event_type": "Dispense",
                "anomaly_type": "Too High",
                "description": f"The value is too high (amount paid of {event['payload']['amount_paid']} is greater than threshold of {app_config['anomalies']['amount_paid_threshold']})",
                "timestamp": current_time
            }
        elif event['type'] == 'refill':
            anomaly_item = {
                "event_id": event['payload']['id'],
                "trace_id": event['payload']['trace_id'],
                "event_type": "Refill",
                "anomaly_type": "Too High",
                "description": f"The value is too high (item quantity of {event['payload']['item_quantity']} is greater than threshold of {app_config['anomalies']['item_quantity_threshold']})",
                "timestamp": current_time
            }
        else:
            logger.error(f"Unknown event type", event['type'])
        data.append(anomaly_item)
        logger.info(f"Anomaly with trace ID {event['payload']['trace_id']} added to database!")

    with open(app_config['datastore']['filename'], "w") as events:
        json.dump(data, events)

    logger.info("Populated anomalies datastore")


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
