import connexion
from connexion import NoContent
import requests
import json
import yaml
import logging
import logging.config
import uuid
import datetime
from pykafka import KafkaClient 

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yaml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')
hostname = "%s:%d" % (app_config["events"]["hostname"], app_config["events"]["port"])

def get_refill_record(index):
    """ Get refill record in History """
    logger.debug("Attempting to connect to Kafka at %s", hostname)
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config["events"]["topic"])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
    consumer_timeout_ms=1000)
    logger.debug("Connected to Kafka at %s", hostname)
    logger.info("Retrieving BP at index %d" % index)
    try:
        events = []
        for msg in consumer:
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            if msg['type'] == 'refill':
                events.append(msg['payload'])
        return events[index], 200
    except:
        logger.error("No more messages found")
        pass
    logger.error("Could not find refill at index %d" % index)
    return { "message": "Not Found"}, 404


def get_dispense_record(index):
    """ Get dispense record in History """
    logger.debug("Attempting to connect to Kafka at %s", hostname)
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config["events"]["topic"])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
    consumer_timeout_ms=1000)
    logger.debug("Connected to Kafka at %s", hostname)
    logger.info("Retrieving dispense at index %d" % index)
    try:
        events = []
        for msg in consumer:
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            if msg['type'] == 'dispense':
                events.append(msg['payload'])
        return events[index], 200
    except:
        logger.error("No more messages found")
        pass
    logger.error("Could not find BP at index %d" % index)
    return { "message": "Not Found"}, 404

def get_event_stats():
    """ Get stats in History """
    logger.debug("Attempting to connect to Kafka at %s", hostname)
    client = KafkaClient(hosts=hostname)
    topic = client.topics[str.encode(app_config["events"]["topic"])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
    consumer_timeout_ms=1000)
    logger.debug("Connected to Kafka at %s", hostname)
    logger.info("Retrieving stats")
    try:
        stats = {'dispense': 0, 'refill': 0}
        for msg in consumer:
            msg_str = msg.value.decode('utf-8')
            msg = json.loads(msg_str)
            stats[msg['type']] += 1
        return {'num_dispense': stats['dispense'], 'num_refill': stats['refill']}, 200
    except:
        logger.error("No stats found")
        pass
    logger.error("Could not find stats")
    return { "message": "Not Found"}, 404

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
if __name__ == "__main__":
    logger.info("running on http://localhost:8110/ui")
    app.run(host="0.0.0.0", port=8110)
