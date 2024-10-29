import mysql.connector
import yaml

with open('app_conf.yaml', 'r') as f:
    app_config = yaml.safe_load(f.read())

db_conn = mysql.connector.connect(host=app_config["datastore"]["hostname"], user=app_config["datastore"]["user"], password=app_config["datastore"]["password"], database=app_config["datastore"]["db"])

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

db_conn.commit()
db_conn.close()
