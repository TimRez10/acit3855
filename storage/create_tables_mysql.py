import mysql.connector
import yaml
import logging
import os
import logging.config

# Environment-based configuration file paths
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    APP_CONF_FILE = "/config/app_conf.yaml"
    LOG_CONF_FILE = "/config/log_conf.yaml"
else:
    print("In Dev Environment")
    APP_CONF_FILE = "app_conf.yaml"
    LOG_CONF_FILE = "log_conf.yaml"

# Load application configuration
with open(APP_CONF_FILE, 'r', encoding="utf-8") as app_file:
    APP_CONFIG = yaml.safe_load(app_file.read())

# Load logging configuration
with open(LOG_CONF_FILE, 'r', encoding="utf-8") as log_file:
    LOG_CONFIG = yaml.safe_load(log_file.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

db_conn = mysql.connector.connect(host=APP_CONFIG["datastore"]["hostname"], user=APP_CONFIG["datastore"]["user"], password=APP_CONFIG["datastore"]["password"], database=APP_CONFIG["datastore"]["db"])

logger.info(f'Connecting to DB {APP_CONFIG["datastore"]["hostname"]}. Port: {APP_CONFIG["datastore"]["port"]}')

logger.debug(f'Created table "dispenses"')

db_cursor = db_conn.cursor()
db_cursor.execute('''
          CREATE TABLE dispenses
          (id INT NOT NULL AUTO_INCREMENT,
           vending_machine_id VARCHAR(250) NOT NULL,
           amount_paid INTEGER NOT NULL,
           payment_method VARCHAR(100) NOT NULL,
           transaction_time DATETIME NOT NULL,
           item_id INTEGER NOT NULL,
           date_created DATETIME NOT NULL,
           trace_id VARCHAR(250) NOT NULL,
           CONSTRAINT dispenses_pk PRIMARY KEY (id))
          ''')

db_cursor.execute('''
          CREATE TABLE refills
          (id INT NOT NULL AUTO_INCREMENT,
           vending_machine_id VARCHAR(250) NOT NULL,
           staff_name VARCHAR(250) NOT NULL,
           refill_time DATETIME NOT NULL,
           item_id INTEGER NOT NULL,
           item_quantity INTEGER NOT NULL,
           date_created DATETIME NOT NULL,
           trace_id VARCHAR(250) NOT NULL,
           CONSTRAINT refills_pk PRIMARY KEY (id))
          ''')

logger.debug(f'Created table "refills"')

db_conn.commit()
db_conn.close()
