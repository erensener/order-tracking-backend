import pandas as pd
import glob
from sqlalchemy import create_engine, Column, Float, String, Boolean
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

# Specify the pattern for your CSV files
file_pattern = './stok_bilgisi.csv'

# Get a list of all CSV files
csv_files = glob.glob(file_pattern)

# Database file name
db_file = '../instance/products.db'
database_url = f'sqlite:///{db_file}'

# SQLAlchemy setup
Base = declarative_base()

class Product(Base):
    __tablename__ = 'products'

    barcode = Column(String, primary_key=True)
    package_barcode = Column(String)
    pallet_barcode = Column(String)
    shipment_number = Column(String)
    delivery_number = Column(String)
    batch_number = Column(String)
    production_date = Column(String)
    end_date = Column(String)
    order_id = Column(String)
    amount = Column(Float)
    is_gts_done = Column(Boolean, nullable=True)
    warehouse = Column(String)
    in_stock = Column(Boolean, nullable=True)

engine = create_engine(database_url)
Base.metadata.create_all(engine)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

db = next(get_db())

db_products = db.query(Product).all()
for product in db_products:
    product.warehouse = "ENDER"
    product.in_stock = False
db.commit()

def insert_or_update_product(db: SessionLocal, product_data: dict):
    db_products = db.query(Product).filter(Product.package_barcode == product_data[1]).all()
    
    if db_products:
        for product in db_products:
        # Update existing record
            setattr(product, "in_stock", True)
            setattr(product, "warehouse", product_data[5])
    db.commit()

for file_path in csv_files:
    try:
        # Read the CSV file
        df = pd.read_csv(file_path, header=None, sep=';')

        if not df.empty:

            print(f"Processing file: {file_path} for database insertion (SQLAlchemy)...")

            # if num_columns == num_expected_columns:
            #     df.columns = expected_columns

            db = next(get_db())
            # Iterate through each row and insert/update using SQLAlchemy
            for index, row in df.iterrows():
                product_data = row.to_dict()
                print(product_data)
                insert_or_update_product(db, product_data)
            db.close()

            print(f"Successfully inserted/updated data from {file_path} into the database (SQLAlchemy).")

            # else:
            #     print(f"Error: Column mismatch in {file_path}. Expected {num_expected_columns} columns, but found {num_columns}.")

        else:
            print(f"Warning: No data found in {file_path} after skipping the first two rows.")

    except FileNotFoundError:
        print(f"Error: File not found - {file_path}")
    except pd.errors.EmptyDataError:
        print(f"Error: Empty data in file - {file_path}")
    except Exception as e:
        print(f"An error occurred while processing {file_path}: {e}")

print("\nData processing and database update complete (SQLAlchemy).")