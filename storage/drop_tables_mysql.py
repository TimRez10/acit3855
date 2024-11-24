import mysql.connector
import yaml
import os

# Environment-based configuration file paths
if "TARGET_ENV" in os.environ and os.environ["TARGET_ENV"] == "test":
    print("In Test Environment")
    APP_CONF_FILE = "/config/app_conf.yaml"
else:
    print("In Dev Environment")
    APP_CONF_FILE = "app_conf.yaml"

# Load application configuration
with open(APP_CONF_FILE, 'r', encoding="utf-8") as app_file:
    APP_CONFIG = yaml.safe_load(app_file.read())


db_conn = mysql.connector.connect(host=APP_CONFIG["datastore"]["hostname"], user=APP_CONFIG["datastore"]["user"], password=APP_CONFIG["datastore"]["password"], database=APP_CONFIG["datastore"]["db"])

db_cursor = db_conn.cursor()

db_cursor.execute('''
DROP TABLE dispenses, refills
''')

db_conn.commit()
db_conn.close()