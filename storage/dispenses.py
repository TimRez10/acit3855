from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql.functions import now
from base import Base
import datetime


class DispenseItem(Base):
    """ Dispensed Item """

    __tablename__ = "dispenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vending_machine_id = Column(String(250), primary_key=True)
    amount_paid = Column(Integer, nullable=False)
    payment_method = Column(String(100), nullable=False)
    transaction_time = Column(DateTime, nullable=False)
    item_id = Column(Integer, nullable=False)
    date_created = Column(DateTime, nullable=False)
    trace_id = Column(String(250), primary_key=True)

    def __init__(self, vending_machine_id, amount_paid, payment_method, transaction_time, item_id, trace_id):
        """ Initializes a dispense record """
        self.vending_machine_id = vending_machine_id
        self.amount_paid = amount_paid
        self.payment_method = payment_method
        self.transaction_time = transaction_time
        self.item_id = item_id
        self.date_created = datetime.datetime.now() # Sets the date/time record is created
        self.trace_id = trace_id

    def to_dict(self):
        """ Dictionary Representation of a dispense record """
        dict = {}
        dict['id'] = self.id
        dict['vending_machine_id'] = self.vending_machine_id
        dict['amount_paid'] = self.amount_paid
        dict['payment_method'] = self.payment_method
        dict['transaction_time'] = self.transaction_time
        dict['item_id'] = self.item_id
        dict['trace_id'] = self.trace_id

        return dict
