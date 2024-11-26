import connexion
from connexion import NoContent
import json
import yaml
import logging
import logging.config
import uuid
import datetime
import os
import time
import sys
from pykafka import KafkaClient

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
        producer = topic.get_sync_producer()
        retry_count = retries
        break
    except Exception as e:
        time.sleep(app_config["events"]["sleep_time"])
        retry_count += 1
        logger.error(f"{e}. {retries-retry_count} out of {retries} retries remaining.")
    if retry_count == retries:
        logger.info(f"Can't connect to Kafka. Exiting...")
        sys.exit()


def add_dispense_record(body):
    trace_id = str(uuid.uuid4())
    logger.info(f"Received event add_dispense_record request with a trace id of {trace_id}")
    body["trace_id"] = trace_id


    msg = {
        "type": "dispense",
        "datetime" : datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Returned event add_dispense_record response (Id: {trace_id})")

    return NoContent, 201


def add_refill_record(body):
    trace_id=str(uuid.uuid4())
    logger.info(f"Received event add_refill_record request with a trace id of {trace_id}")
    body["trace_id"] = trace_id

    msg = {
        "type": "refill",
        "datetime" : datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
    }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))

    logger.info(f"Returned event add_refill_record response (Id: {trace_id})")

    return NoContent, 201


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", base_path="/receiver", strict_validation=True, validate_responses=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
