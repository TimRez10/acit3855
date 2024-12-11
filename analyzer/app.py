import connexion
from connexion import NoContent
import json
import yaml
import logging
import logging.config
from pykafka import KafkaClient
import os
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

def get_refill_record(index):
    """ Get refill record in History """
    try:
        logger.debug("Attempting to connect to Kafka at %s", hostname)
        client = KafkaClient(hosts=hostname)
    except Exception as e:
        logger.error(f"{e}")
        return e, 400
    topic = client.topics[str.encode(app_config["events"]["topic"])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
    consumer_timeout_ms=1000)
    logger.info("Retrieving refill at index %d" % index)
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
    try:
        logger.debug("Attempting to connect to Kafka at %s", hostname)
        client = KafkaClient(hosts=hostname)
    except Exception as e:
        logger.error(f"{e}")
        return e, 400
    topic = client.topics[str.encode(app_config["events"]["topic"])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
    consumer_timeout_ms=1000)
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
    logger.error("Could not find dispense at index %d" % index)
    return { "message": "Not Found"}, 404

def get_event_stats():
    """ Get stats in History """
    try:
        logger.debug("Attempting to connect to Kafka at %s", hostname)
        client = KafkaClient(hosts=hostname)
    except Exception as e:
        logger.error(f"{e}")
        return e, 400
    topic = client.topics[str.encode(app_config["events"]["topic"])]
    consumer = topic.get_simple_consumer(reset_offset_on_start=True,
    consumer_timeout_ms=1000)
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

app.add_api("openapi.yaml", base_path="/analyzer", strict_validation=True, validate_responses=True)
if "TARGET_ENV" not in os.environ or os.environ["TARGET_ENV"] != "test":
    #CORS(app.app)
    #app.app.config['CORS_HEADERS'] = 'Content-Type'
    app.add_middleware(
        CORSMiddleware,
        position=MiddlewarePosition.BEFORE_EXCEPTION,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
if __name__ == "__main__":
    logger.info("running on http://localhost:8110/ui")
    app.run(host="0.0.0.0", port=8110)