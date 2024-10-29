from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql.functions import now
from base import Base
import datetime


class RefillItem(Base):
    """ Refill Item """

    __tablename__ = "refills"

    id = Column(Integer, primary_key=True, autoincrement=True)
    vending_machine_id = Column(String(250), primary_key=True)
    staff_name = Column(String(250), nullable=False)
    refill_time = Column(DateTime, nullable=False)
    item_id = Column(Integer, nullable=False)
    item_quantity = Column(Integer, nullable=False)
    date_created = Column(DateTime, nullable=False)
    trace_id = Column(String(250), primary_key=True)

    def __init__(self, vending_machine_id, staff_name, refill_time, item_id, item_quantity, trace_id):
        """ Initializes a refill record"""
        self.vending_machine_id = vending_machine_id
        self.staff_name = staff_name
        self.refill_time = refill_time
        self.item_id = item_id
        self.item_quantity = item_quantity
        self.date_created = datetime.datetime.now() # Sets the date/time record is created
        self.trace_id = trace_id

    def to_dict(self):
        """ Dictionary Representation of a heart rate reading """
        dict = {}
        dict['id'] = self.id
        dict['vending_machine_id'] = self.vending_machine_id
        dict['staff_name'] = self.staff_name
        dict['refill_time'] = self.refill_time
        dict['item_id'] = self.item_id
        dict['item_quantity'] = self.item_quantity
        dict['date_created'] = self.date_created
        dict['trace_id'] = self.trace_id

        return dict
