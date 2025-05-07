import pandas as pd
import glob
from sqlalchemy import create_engine, Column, Float, String, Boolean, Integer
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Database file name
db_file = '../instance/orders.db'
DATABASE_URL = f'sqlite:///{db_file}'

Base = declarative_base()

# Define the Order model
class ClientOrder(Base):
    __tablename__ = 'client_order'

    id = Column(String(30), primary_key=True)
    client_id = Column(String(100), nullable=False)
    quantity = Column(Float, nullable=False)
    quantity_text = Column(String(200), nullable=False)
    price = Column(Integer, nullable=True)
    remaining_amount = Column(Integer, nullable=True)
    is_receipt_done = Column(Boolean, nullable=True)
    is_gts_done = Column(Boolean, nullable=True)
    cargo_barcode = Column(String(100), nullable=True)
    gts_barcode = Column(String(100), nullable=True)
    order_type = Column(String(100), nullable=True)
    last_update = Column(String(100), nullable=True)
    purchase_date = Column(String(20), nullable=True)
    comments = Column(String(1000), nullable=True)
    delivery_status = Column(String(100), nullable=True)
    yield_type = Column(String(100), nullable=True)
    intermediar_id = Column(String(100), nullable=True)
    intermediar_amount = Column(Integer, nullable=True)
    product_type = Column(String(50), nullable=True)


# Connect to database
engine = create_engine(DATABASE_URL)

Session = sessionmaker(bind=engine)
session = Session()

# Query and update
orders = session.query(ClientOrder).all()
for order in orders:
    order.intermediar_amount = 0
    order.intermediar_id = ""
    order.product_type = "Cropsil"

# Commit changes
session.commit()
print(f"Updated {len(orders)} orders.")

# Optional: Close session
session.close()