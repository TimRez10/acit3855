# import sqlite3

# conn = sqlite3.connect('readings.sqlite')

# c = conn.cursor()
# c.execute('''
#           CREATE TABLE dispenses
#           (id INTEGER PRIMARY KEY ASC,
#            vending_machine_id VARCHAR(250) NOT NULL, 
#            amount_paid INTEGER NOT NULL,
#            payment_method VARCHAR(100) NOT NULL,
#            transaction_time VARCHAR(100) NOT NULL,
#            item_id INTEGER NOT NULL,
#            date_created VARCHAR(100) NOT NULL),
#            tracing_id VARCHAR(250)
#           ''')

# c.execute('''
#           CREATE TABLE refills
#           (id INTEGER PRIMARY KEY ASC,
#            vending_machine_id VARCHAR(250) NOT NULL, 
#            staff_name VARCHAR(250) NOT NULL,
#            refill_time VARCHAR(100) NOT NULL,
#            item_id INTEGER NOT NULL,
#            item_quantity INTEGER NOT NULL,
#            date_created VARCHAR(100) NOT NULL),
#            tracing_id VARCHAR(250)
#           ''')

# conn.commit()
# conn.close()
