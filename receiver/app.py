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

# def create_events_file():
#     with open(EVENT_FILE, "w") as events:
#         data_fields =   {"count_dr":0,
#                             "recent_dr":[],
#                             "count_rr":0,
#                             "recent_rr":[]
#                         }
#         test = json.dumps(data_fields)
#         events.write(test)
#     return None


def add_dispense_record(body):
    # if not os.path.isfile(EVENT_FILE):
    #     create_events_file()

    # with open(EVENT_FILE, "r") as events:
    #     data = json.load(events)

    # data["count_dr"] += 1
    # message = {"msg_data":f"Vending Machine {body['vending_machine_id']} dispensed item ID {body['item_id']}. Payment of {body['amount_paid']:.2f}$ with payment method '{body['payment_method']}' at {body['transaction_time']}.",
    #            "received_timestamp": str(datetime.datetime.now())}
    # data["recent_dr"].insert(0, message)
    # if len(data["recent_dr"]) > MAX_EVENTS:
    #     data["recent_dr"].pop(-1)
    # with open(EVENT_FILE, "w") as events:
    #     json.dump(data, events)

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
    # if not os.path.isfile(EVENT_FILE):
    #     create_events_file()

    # with open(EVENT_FILE, "r") as events:
    #     data = json.load(events)

    # data["count_rr"] += 1
    # message = {"msg_data":f"Vending Machine {body['vending_machine_id']} refilled with {body['item_quantity']} of item ID {body['item_id']}. Refilled by {body['staff_name']} at {body['refill_time']}.",
    #             "received_timestamp": str(datetime.datetime.now())}
    
    # data["recent_rr"].insert(0, message)
    # if len(data["recent_rr"]) > MAX_EVENTS:
    #     data["recent_rr"].pop(-1)
    
    # with open(EVENT_FILE, "w") as events:
    #     json.dump(data, events)

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
