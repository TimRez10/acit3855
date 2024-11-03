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
from pykafka import KafkaClient 

load_dotenv()

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())
    app_config["events"]["hostname"] = os.getenv("KAFKA_HOST_NAME")

with open('log_conf.yaml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')
hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])

def add_dispense_record(body):
    trace_id = str(uuid.uuid4())
    logger.info(f"Received event add_dispense_record request with a trace id of {trace_id}")
    body["trace_id"] = trace_id

    try:
        logger.info("Attempting to connect to Kafka at %s", hostname)
        client = KafkaClient(hosts=hostname)
    except Exception as e:
        logger.error(f"{e}")
        return e, 400
    logger.debug(f'Connected to Kafka client on {hostname}')

    topic = client.topics[str.encode(app_config["events"]["topic"])]
    producer = topic.get_sync_producer()
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
    
    try:
        logger.info("Attempting to connect to Kafka at %s", hostname)
        client = KafkaClient(hosts=hostname)
    except Exception as e:
        logger.error(f"{e}")
        return e, 400
    logger.debug(f'Connected to Kafka client on {hostname}')
    
    topic = client.topics[str.encode(app_config["events"]["topic"])]
    producer = topic.get_sync_producer()
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
