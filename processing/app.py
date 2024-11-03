import connexion
from connexion import NoContent
import requests
import json
import yaml
import os
import logging
import logging.config
import datetime
from apscheduler.schedulers.background import BackgroundScheduler

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())

with open('log_conf.yaml', 'r') as f:
    log_config = yaml.safe_load(f.read())
    logging.config.dictConfig(log_config)

logger = logging.getLogger('basicLogger')

def populate_stats():
    logger.info("Start Periodic Processing")

    if not os.path.isfile(app_config['datastore']['filename']):
        data = {"num_dispense_records": 0,
                "max_dispense_amount_paid": 0,
                "num_refill_records": 0,
                "max_refill_quantity": 0,
                "last_updated": "2023-10-10T03:30:20"}
    else:
        with open(app_config['datastore']['filename'], "r") as events:
            data = json.load(events)

    current_time = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    dispense_url = f"{app_config['eventstore']['url']}/dispenses?end_timestamp={current_time}&start_timestamp={data['last_updated']}"

    try:
        logger.debug(f"Calling GET to /dispenses")
        dispense_event = requests.get(dispense_url)
    except Exception as e:
        logger.error(f"{e}")
    
    if dispense_event.status_code == 200:
        logger.info(f"dispenses: Received {len(dispense_event.json())} events.")
    else:
        logger.error(f"dispenses: Response code is not 200. Response code is {dispense_event.status_code}.")
    
    refill_url = f"{app_config['eventstore']['url']}/refills?end_timestamp={current_time}&start_timestamp={data['last_updated']}"

    try:
        logger.debug(f"Calling GET to /refills")
        refill_event = requests.get(refill_url)
    except Exception as e:
        logger.error(f"{e}")

    if refill_event.status_code == 200:
        logger.info(f"refills: Received {len(refill_event.json())} events.")
    else:
        logger.error(f"refills: Response code is not 200. Response code is {refill_event.status_code}.")

    dispense_items = dispense_event.json()
    refill_items = refill_event.json()

    try:
        data['num_dispense_records'] += len(dispense_items)
        if len(dispense_items):
            data['max_dispense_amount_paid'] = max(data['max_dispense_amount_paid'], *[x['amount_paid'] for x in dispense_items])
        data['num_refill_records'] += len(refill_items)
        if len(refill_items):
            data['max_refill_quantity'] = max(data['max_refill_quantity'], *[y['item_quantity'] for y in refill_items])
        data['last_updated'] = current_time
    except Exception as e:
        logger.error(f"{e}")

    with open(app_config['datastore']['filename'], "w") as events:
        json.dump(data, events)
    
    logger.info("Ended Periodic Processing")
        

def get_stats():
    logger.info("get_stats request started")
   
    if not os.path.isfile(app_config['datastore']['filename']):
        logger.error(f"Statistics do not exist.")
        return "Statistics do not exist.", 404

    with open(app_config['datastore']['filename'], "r") as events:
        data = json.load(events)

    response = {
        'num_dispense_records': data['num_dispense_records'],
        'max_dispense_amount_paid': data['max_dispense_amount_paid'],
        'num_refill_records': data['num_refill_records'],
        'max_refill_quantity': data['max_refill_quantity']
    }

    logger.debug(f"Contents: {response}")

    logger.info("get_stats request completed")

    return response, 200


def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats,'interval',seconds=app_config['scheduler']['period_sec'])

    sched.start()

app = connexion.FlaskApp(__name__, specification_dir='')
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)
if __name__ == "__main__":
    init_scheduler()
    app.run(host="0.0.0.0", port=8100)
