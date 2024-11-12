import connexion
from connexion import NoContent
from dotenv import load_dotenv
import json
import yaml
import logging
import logging.config
import uuid
import datetime
import os
import time
from pykafka import KafkaClient 

load_dotenv()

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())
    app_config["events"]["hostname"] = os.getenv("HOST_NAME")

with open('log_conf.yaml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)
logger = logging.getLogger('basicLogger')

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
        logger.info(f"Quitting...")
        quit


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
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
