import mysql.connector
import yaml
from dotenv import load_dotenv
import os

load_dotenv()

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())
    app_config["datastore"]["hostname"] = os.getenv("KAFKA_HOST_NAME")
    app_config["datastore"]["user"] = os.getenv("MYSQL_USER")
    app_config["datastore"]["password"] = os.getenv("MYSQL_PASSWORD")

db_conn = mysql.connector.connect(host=app_config["datastore"]["hostname"], user=app_config["datastore"]["user"], password=app_config["datastore"]["password"], database=app_config["datastore"]["db"])

db_cursor = db_conn.cursor()

db_cursor.execute('''
DROP TABLE dispenses, refills
''')

db_conn.commit()
db_conn.close()