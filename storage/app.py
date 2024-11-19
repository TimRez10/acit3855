import connexion
from connexion import NoContent
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from base import Base
from dispenses import DispenseItem
from refills import RefillItem
from threading import Thread
from pykafka import KafkaClient
from pykafka.common import OffsetType
import json
import datetime
import logging
import logging.config
import yaml
import os
import time
import sys

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

### DB CONNECTION ###
DB_ENGINE = create_engine(
    f'mysql+pymysql://{app_config["datastore"]["user"]}:{app_config["datastore"]["password"]}@{app_config["datastore"]["hostname"]}:{app_config["datastore"]["port"]}/{app_config["datastore"]["db"]}',
    pool_recycle=-1,
    pool_size=0,
    pool_pre_ping=True
)
Base.metadata.bind = DB_ENGINE
DB_SESSION = sessionmaker(bind=DB_ENGINE)
logger.info(f'Connecting to DB {app_config["datastore"]["hostname"]}. Port: {app_config["datastore"]["port"]}')

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

def add_dispense_record(body):
    """ Receives a dispense record """
    data=body
    session = DB_SESSION()
    dr = DispenseItem(data['vending_machine_id'],
                       data['amount_paid'],
                       data['payment_method'],
                       datetime.datetime.strptime(data['transaction_time'], "%Y-%m-%dT%H:%M:%S.%fZ"),
                       data['item_id'],
                       data['trace_id'])
    session.add(dr)
    session.commit()
    session.close()
    logger.debug(f"Stored event add_dispense_record request with a trace id of {data['trace_id']}")

    return NoContent, 201



def add_refill_record(body):
    """ Receives a refill record """
    session = DB_SESSION()
    data=body
    rr = RefillItem(data['vending_machine_id'],
                       data['staff_name'],
                       datetime.datetime.strptime(data['refill_time'], "%Y-%m-%dT%H:%M:%S.%fZ"),
                       data['item_id'],
                       data['item_quantity'],
                       data['trace_id'])
    session.add(rr)
    session.commit()
    session.close()
    logger.debug(f"Stored event add_refill_record request with a trace id of {data['trace_id']}")

    return NoContent, 201



def get_refill_record(start_timestamp, end_timestamp):
    """ Gets new refill record between the start and end timestamps """
    session = DB_SESSION()

    inspector = inspect(session.bind)
    if not inspector.has_table("refills"):
        logger.warning("The 'refills' table does not exist in the database.")
        session.close()
        return NoContent, 404

    start_timestamp_datetime = datetime.datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S")
    end_timestamp_datetime = datetime.datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S")

    logger.debug(f"get_refill_record: Received timestamps between '{start_timestamp_datetime}' and '{end_timestamp_datetime}'")
    results = session.query(RefillItem).filter(end_timestamp_datetime > RefillItem.date_created).filter(RefillItem.date_created >= start_timestamp_datetime)
    results_list = []
    for reading in results:
        results_list.append(reading.to_dict())
    session.close()
    logger.info(f"Query for refill records returns {len(results_list)} results")

    return results_list, 200


def get_dispense_record(start_timestamp, end_timestamp):
    """ Gets new dispense record between the start and end timestamps """
    session = DB_SESSION()

    inspector = inspect(session.bind)
    if not inspector.has_table("dispenses"):
        logger.warning("The 'dispenses' table does not exist in the database.")
        session.close()
        return NoContent, 404

    start_timestamp_datetime = datetime.datetime.strptime(start_timestamp, "%Y-%m-%dT%H:%M:%S")
    end_timestamp_datetime = datetime.datetime.strptime(end_timestamp, "%Y-%m-%dT%H:%M:%S")

    logger.debug(f"get_dispense_record: Received timestamps between '{start_timestamp_datetime}' and '{end_timestamp_datetime}'")
    results = session.query(DispenseItem).filter(end_timestamp_datetime > DispenseItem.date_created).filter(DispenseItem.date_created >= start_timestamp_datetime)
    results_list = []
    for reading in results:
        results_list.append(reading.to_dict())
    session.close()
    logger.info(f"Query for dispense records returns {len(results_list)} results")

    return results_list, 200

def process_messages():
    """ Process event messages """
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)
        payload = msg["payload"]
        logger.info(f"Consumer received msg of type {msg['type']}.")

        if msg["type"] == "dispense":
            add_dispense_record(payload)
        elif msg["type"] == "refill":
            add_refill_record(payload)
        consumer.commit_offsets()


app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yml", strict_validation=True, validate_responses=True)
if __name__ == "__main__":
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()
    app.run(host="0.0.0.0", port=8090)
