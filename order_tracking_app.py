# app.py
from io import BytesIO
import pandas as pd
from flask import Flask, request, send_file, jsonify, abort
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Integer, Float, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import func
from flask_sqlalchemy import SQLAlchemy
import os
from flask import jsonify
from collections import defaultdict, Counter
from flask import jsonify

app = Flask(__name__)

# Configure the SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///orders.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
# Set the upload folder path
UPLOAD_FOLDER = 'images'  # Change this to your desired folder
os.makedirs(UPLOAD_FOLDER, exist_ok=True)  # Create the folder if it doesn't exist

# Set allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Configure the second SQLite database (products.db)
PRODUCT_DATABASE_URI = 'sqlite:///instance/products.db'
product_engine = create_engine(PRODUCT_DATABASE_URI)

ProductBase = declarative_base()
ProductSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=product_engine)

# Define the Product model for the second database
class Product(ProductBase):
    __tablename__ = "products"  # matches the table name in the database
    barcode = Column(String, primary_key=True, index=True)
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
    in_stock = Column(Boolean)

# Define the Order model
class Order(db.Model):
    id = db.Column(db.String(30), primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(15), nullable=False)
    district = db.Column(db.String(100), nullable=False)
    tc = db.Column(db.String(11), nullable=False)
    birthday = db.Column(db.String(10), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    quantity_text = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=True)
    remaining_amount = db.Column(db.Integer, nullable=True)
    is_receipt_done = db.Column(db.Boolean, nullable=True)
    is_gts_done = db.Column(db.Boolean, nullable=True)
    cargo_barcode = db.Column(db.String(100), nullable=True)
    gts_barcode = db.Column(db.String(100), nullable=True)
    source = db.Column(db.String(100), nullable=True)
    order_type = db.Column(db.String(100), nullable=True)
    last_update = db.Column(db.String(100), nullable=True)
    purchase_date = db.Column(db.String(20), nullable=True)
    activity_log_id = db.Column(db.String(100), nullable=True)
    comments = db.Column(db.String(1000), nullable=True)
    delivery_status = db.Column(db.String(100), nullable=True)

class PaymentLog(db.Model):
    id = db.Column(db.String(30), primary_key=True)
    order_id = db.Column(db.String(30), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    payment_date = db.Column(db.String(20), nullable=False, default=lambda: datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    method = db.Column(db.String(50), nullable=True)  # Cash, Credit Card, etc.
    note = db.Column(db.String(500), nullable=True)

# Define the Client model
class Client(db.Model):
    id = db.Column(db.String, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone_number = db.Column(db.String, nullable=False)
    district = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    tc = db.Column(db.String, nullable=False)
    birthday = db.Column(db.String, nullable=False)
    source = db.Column(db.String, nullable=False)
    comments = db.Column(db.String, nullable=True)
    email = db.Column(db.String, nullable=True)
    title = db.Column(db.String, nullable=False)
    gts_number = db.Column(db.String, nullable=False)

# Define the Order model
class ClientOrder(db.Model):
    id = db.Column(db.String(30), primary_key=True)
    client_id = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    quantity_text = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=True)
    remaining_amount = db.Column(db.Integer, nullable=True)
    is_receipt_done = db.Column(db.Boolean, nullable=True)
    is_gts_done = db.Column(db.Boolean, nullable=True)
    cargo_barcode = db.Column(db.String(100), nullable=True)
    gts_barcode = db.Column(db.String(100), nullable=True)
    order_type = db.Column(db.String(100), nullable=True)
    last_update = db.Column(db.String(100), nullable=True)
    purchase_date = db.Column(db.String(20), nullable=True)
    comments = db.Column(db.String(1000), nullable=True)
    delivery_status = db.Column(db.String(100), nullable=True)
    yield_type = db.Column(db.String(100), nullable=True)
    intermediar_id = db.Column(db.String(100), nullable=True)
    intermediar_amount = db.Column(db.Integer, nullable=True)
    product_type = db.Column(db.String(50), nullable=True)

@app.route('/stock/summary', methods=['GET'])
def summarize_stock():
    # Query: group by package_barcode and warehouse, aggregate amount and count
    product_db = next(get_product_db())

    grouped_results = (
        product_db.query(
            Product.package_barcode,
            Product.warehouse,
            func.sum(Product.amount).label('total_amount'),
            func.count(Product.barcode).label('count')
        )
        .filter(Product.in_stock == True)
        .group_by(Product.package_barcode, Product.warehouse)
        .all()
    )

    # Build group list
    group_summary = []
    for package_barcode, warehouse, total_amount, count in grouped_results:
        group_summary.append({
            "package_barcode": package_barcode,
            "warehouse": warehouse,
            "total_amount": total_amount,
            "count": count
        })

    # Optional overall summary
    total_groups = len(group_summary)
    total_amount_all = sum(item['total_amount'] for item in group_summary)

    return jsonify({
        "grouped_summary": group_summary,
        "total_groups": total_groups,
        "total_amount_all": total_amount_all
    })

@app.route('/stock/warehouse_summary', methods=['GET'])
def summarize_stock_by_warehouse():
    product_db = next(get_product_db())

    # Group by warehouse only
    results = (
        product_db.query(
            Product.warehouse,
            func.count(Product.barcode).label('item_count'),
            func.sum(Product.amount).label('total_amount')
        )
        .filter(Product.in_stock == True)
        .group_by(Product.warehouse)
        .all()
    )

    summary = []
    for warehouse, item_count, total_amount in results:
        summary.append({
            "warehouse": warehouse,
            "item_count": item_count,
            "total_amount": total_amount
        })

    return jsonify(summary)

@app.route('/export/orders', methods=['GET'])
def export_orders():
    # Query all orders where is_receipt_done is False
    # Collect only order data
    data = [] 

    db_orders = ClientOrder.query.all()
    orders = []
    clients = []

    for order in db_orders:
        client = Client.query.get(order.client_id)
        if client: 
            gts_text = "Yapılmadı"
            if order.is_gts_done == True:
                gts_text = "OK"

            receipt_text = "Yapılmadı"
            if order.is_receipt_done == True:
                receipt_text = "OK"

            data.append({
            "Sipariş Id": order.id,
            "İsim": client.name,
            "Telefon": client.phone_number,
            "Bölge": client.district,
            "TC": client.tc,
            "Doğum Tarihi": client.birthday,
            "Adres": client.address,
            "Email": client.email,
            "Miktar": order.quantity,
            "Fatura": receipt_text,
            "GTS": gts_text,
            "GTS Barcode": order.gts_barcode,
            "Miktar Yazısı": order.quantity_text,
            "Fiyat": order.price,
            "Toplam Ücret": order.quantity * order.price,
            "Kalan Miktar": order.remaining_amount,
            "Kaynak": client.source,
            "Sipariş Tipi": order.order_type,
            "Ürün Tipi": order.yield_type,
            "Sipariş Tarihi": order.purchase_date,
            "Sipariş Durumu": order.delivery_status,
        })

    # Create a pandas DataFrame
    df = pd.DataFrame(data)

    # Save DataFrame to an Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="Orders")

    output.seek(0)

    # Return the file
    return send_file(
        output,
        download_name="orders.xlsx",
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

def serialize_order(order):
    return {
        "id": order.id,
        "clientId": order.client_id,
        "quantity": order.quantity,
        "quantityText": order.quantity_text,
        "price": order.price,
        "remainingAmount": order.remaining_amount,
        "isReceiptDone": order.is_receipt_done,
        "isGtsDone": order.is_gts_done,
        "cargoBarcode": order.cargo_barcode,
        "gtsBarcode": order.gts_barcode,
        "orderType": order.order_type,
        "lastUpdate": order.last_update,
        "purchaseDate": order.purchase_date,
        "comments": order.comments,
        "deliveryStatus": order.delivery_status,
        "yieldType": order.yield_type,
        "intermediarId": order.intermediar_id,
        "intermediarAmount": order.intermediar_amount,
        "productType": order.product_type
    }

def serialize_client(client):
    return {
        "id": client.id,
        "name": client.name,
        "phoneNumber": client.phone_number,
        "district": client.district,
        "address": client.address,
        "tc": client.tc,
        "birthday": client.birthday,
        "source": client.source,
        "comments": client.comments,
        "email": client.email,
        "title": client.title,
        "gtsNumber": client.gts_number
    }

@app.route('/orders/unpaid', methods=['GET'])
def get_unpaid_orders():
    orders = db.session.query(ClientOrder).all()
    response = []

    for order in orders:
        # Ensure price and quantity are valid
        if order.price is None or order.quantity is None:
            continue

        total_amount = order.price * order.quantity

        paid_amount = db.session.query(
            func.coalesce(func.sum(PaymentLog.amount), 0)
        ).filter(PaymentLog.order_id == order.id).scalar()

        remaining_amount = total_amount - paid_amount

        # if remaining_amount > 0:
        client = db.session.query(Client).filter(Client.id == order.client_id).first()
        response.append({
            "order": serialize_order(order),
            "client": serialize_client(client),
            "paid_amount": paid_amount,
            "remaining_amount": remaining_amount
        })

    return jsonify(response)

# Create the tables for both databases
with app.app_context():
    db.create_all()
    ProductBase.metadata.create_all(bind=product_engine)

# Function to get a session for the product database
def get_product_db():
    db = ProductSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Endpoint to save a new client
@app.route('/api/save_client', methods=['POST'])
def save_client():
    data = request.get_json()
    new_client = Client(
        id=data.get('id'),
        name=data.get('name'),
        phone_number=data.get('phoneNumber'),
        district=data.get('district'),
        address=data.get('address'),
        tc=data.get('tc'),
        birthday=data.get('birthday'),
        source=data.get('source'),
        comments=data.get('comments'),
        email=data.get('email'),
        title=data.get('title'),
        gts_number=data.get('gtsNumber')
    )
    db.session.add(new_client)
    db.session.commit()
    return jsonify({"message": "Client added successfully!"}), 200

# Endpoint to update an existing client
@app.route('/api/update_client/<string:client_id>', methods=['PUT'])
def update_client(client_id):
    data = request.get_json()
    client = Client.query.get(client_id)

    if not client:
        return jsonify({"message": "Client not found!"}), 404
    print(data)
    # Update only the fields that are provided in the request using setattr
    for key, value in data.items():
        if hasattr(client, key):  # Check if the attribute exists
            setattr(client, key, value)  # Set the attribute to the new value

    db.session.commit()
    return jsonify({"message": "Client updated successfully!"}), 200

# Endpoint to delete a client
@app.route('/api/delete_client/<string:client_id>', methods=['DELETE'])
def delete_client(client_id):
    client = Client.query.get(client_id)
    if not client:
        return jsonify({"message": "Client not found!"}), 404

    db.session.delete(client)
    db.session.commit()
    return jsonify({"message": "Client deleted successfully!"}), 200

@app.route('/api/get_clients', methods=['GET'])
def get_clients():
    clients = Client.query.all()  # Fetch all orders from the database
    return jsonify([{
        'id': client.id,
        'name': client.name,
        'phoneNumber': client.phone_number,
        'district': client.district,
        'address': client.address,
        'email': client.email,
        'tc': client.tc,
        'birthday': client.birthday,
        'source': client.source,
        'comments': client.comments,
        'title': client.title,
        'gtsNumber': client.gts_number
    } for client in clients])

@app.route('/api/save_client_order', methods=['POST'])
def save_client_order():
    data = request.json
    new_order = ClientOrder(
        id=data.get('id'),
        client_id=data.get('clientId'),
        price=data.get('price'),
        quantity=data.get('quantity'),
        remaining_amount=data.get('remainingAmount'),
        cargo_barcode=data.get('cargoBarcode'),
        gts_barcode=data.get('gtsBarcode'),
        is_receipt_done=data.get('isReceiptDone', False),
        is_gts_done=data.get('isGTSDone', False),
        order_type=data.get('orderType'),
        last_update=data.get('lastUpdate'),
        purchase_date=data.get('purchaseDate'),
        comments=data.get('comments'),
        delivery_status=data.get('deliveryStatus'),
        quantity_text=data.get('quantityText'),
        yield_type=data.get('yieldType'),
        intermediar_id=data.get('intermediarId'),
        intermediar_amount=data.get('intermediarAmount'),
        productType=data.get('productType'),
    )
    
    db.session.add(new_order)
    db.session.commit()
    
    return jsonify({'message': 'Client order saved successfully!'}), 200

# Endpoint to update an existing client
@app.route('/api/update_client_order/<string:order_id>', methods=['PUT'])
def update_client_order(order_id):
    data = request.get_json()
    order = ClientOrder.query.get(order_id)

    if not order:
        return jsonify({"message": "ClientOrder not found!"}), 404

    # Update only the fields that are provided in the request using setattr
    for key, value in data.items():
        if hasattr(order, key):  # Check if the attribute exists
            setattr(order, key, value)  # Set the attribute to the new value

    db.session.commit()
    return jsonify({"message": "ClientOrder updated successfully!"}), 200

# Endpoint to delete a client
@app.route('/api/delete_client_order/<string:client_id>', methods=['DELETE'])
def delete_client_order(client_id):
    order = ClientOrder.query.get(client_id)
    if not order:
        return jsonify({"message": "Client Order not found!"}), 404

    db.session.delete(order)
    db.session.commit()
    return jsonify({"message": "Client deleted successfully!"}), 200

@app.route('/api/get_client_orders', methods=['GET'])
def get_client_orders():
    db_orders = ClientOrder.query.all()
    orders = []
    clients = []

    for order in db_orders:
        client = Client.query.get(order.client_id)
        if client:
            orders.append({
                    "id": order.id,
                    "clientId": order.client_id,
                    "quantity": order.quantity,
                    "quantityText": order.quantity_text,
                    "price": order.price,
                    "remainingAmount": order.remaining_amount,
                    "isReceiptDone": order.is_receipt_done,
                    "isGTSDone": order.is_gts_done,
                    "cargoBarcode": order.cargo_barcode,
                    "gtsBarcode": order.gts_barcode,
                    "orderType": order.order_type,
                    "lastUpdate": order.last_update,
                    "purchaseDate": order.purchase_date,
                    "comments": order.comments,
                    "deliveryStatus": order.delivery_status,
                    "yieldType": order.yield_type,
                    "intermediarId": order.intermediar_id,
                    "intermediarAmount": order.intermediar_amount,
                    "productType": order.product_type,
                })
            clients.append({
                    "id": client.id,
                    "name": client.name,
                    "phoneNumber": client.phone_number,
                    "district": client.district,
                    "address": client.address,
                    "tc": client.tc,
                    "birthday": client.birthday,
                    "source": client.source,
                    "comments": client.comments,
                    "email": client.email,
                    "title": client.title,
                    "gtsNumber": client.gts_number
                })

    return jsonify({'orders': orders, 'clients': clients}), 200

@app.route('/api/get_one_client_orders/<string:client_id>', methods=['GET'])
def get_one_client_orders(client_id):
    orders = ClientOrder.query.filter_by(client_id=client_id).all()
    if not orders:
        return jsonify({'message': 'No orders found for this client.'}), 404

    orders_list = []
    for order in orders:
        orders_list.append({
                    "id": order.id,
                    "clientId": order.client_id,
                    "quantity": order.quantity,
                    "quantityText": order.quantity_text,
                    "price": order.price,
                    "remainingAmount": order.remaining_amount,
                    "isReceiptDone": order.is_receipt_done,
                    "isGTSDone": order.is_gts_done,
                    "cargoBarcode": order.cargo_barcode,
                    "gtsBarcode": order.gts_barcode,
                    "orderType": order.order_type,
                    "lastUpdate": order.last_update,
                    "purchaseDate": order.purchase_date,
                    "comments": order.comments,
                    "deliveryStatus": order.delivery_status,
                    "yieldType": order.yield_type,
                    "intermediarId": order.intermediar_id,
                    "intermediarAmount": order.intermediar_amount,
                    "productType": order.product_type,
                })

    return jsonify(orders_list), 200

##############################
@app.route('/api/save_order', methods=['POST'])
def save_order():
    data = request.json  # Get the JSON data from the request

    # Create a new Order instance
    new_Order = Order(
        id=data.get('id'),
        name=data.get('name'),
        phone_number=data.get('phoneNumber'),
        district=data.get('district'),
        tc=data.get('tc'),
        birthday=data.get('birthday'),
        address=data.get('address'),
        email=data.get('email'),
        quantity_text=data.get('quantityText'),
        quantity=float(data.get('quantity')),
        price=int(data.get('price')),
        remaining_amount=int(data.get('remainingAmount')),
        cargo_barcode=data.get('cargoBarcode'),
        gts_barcode=data.get('gtsBarcode'),
        is_receipt_done=data.get('isReceiptDone'),
        is_gts_done=data.get('isGTSDone'),
        source=data.get('source'),
        order_type=data.get('orderType'),
        last_update=data.get('lastUpdate'),
        activity_log_id=data.get('activityLogId'),
        purchase_date=data.get('purchaseDate'),
        comments=data.get('comments'),
        delivery_status=data.get('deliveryStatus'),
    )

    # Add the new Order to the session and commit
    db.session.add(new_Order)
    db.session.commit()

    return jsonify({'status': 'success'}), 200

# Fetch order data by ID
@app.route('/api/get_order/<string:order_id>', methods=['GET'])
def get_order(order_id):
    order = Order.query.get(order_id)
    if order:
        return jsonify({
            'name': order.name,
            'phoneNumber': order.phone_number,
            'district': order.district,
            'price': order.price,
            'quantity': order.quantity,
            'remainingAmount': order.remaining_amount,
            'quantityText': order.quantity_text,
            'address': order.address,
            'email': order.email,
            'cargoBarcode': order.cargo_barcode,
            'gtsBarcode': order.gts_barcode,
            'tc': order.tc,
            'birthday': order.birthday,
            'isReceiptDone': order.is_receipt_done,
            'isGTSDone': order.is_gts_done,
            'source': order.source,
            'orderType': order.order_type,
            'activityLogId': order.activity_log_id,
            'purchaseDate': order.purchase_date,
            'comments': order.comments,
            'deliveryStatus': order.delivery_status,            
        }), 200
    else:
        return jsonify({'error': 'Order not found'}), 404

# Update order endpoint
@app.route('/api/update_order', methods=['PUT'])
def update_order():
    data = request.get_json()  # Get the JSON data from the request
    order_id = data.get('id')  # Extract the order ID from the data

    # Find the order by ID
    # order = Order.query.get(order_id)
    order = db.session.get(Order, order_id)
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    # Update the order fields
    order.name = data.get('name', order.name)
    order.phone_number = data.get('phoneNumber', order.phone_number)
    order.district = data.get('district', order.district)
    order.price = data.get('price', order.price)
    order.quantity = data.get('quantity', order.quantity)
    order.remaining_amount = data.get('remainingAmount', order.remaining_amount)
    order.address = data.get('address', order.address)
    order.email = data.get('email', order.email)
    order.quantity_text = data.get('quantityText', order.quantity_text)
    order.cargo_barcode = data.get('cargoBarcode', order.cargo_barcode)
    order.gts_barcode = data.get('gtsBarcode', order.gts_barcode)
    order.tc = data.get('tc', order.tc)
    order.birthday = data.get('birthday', order.birthday)
    order.is_receipt_done = data.get('isReceiptDone', order.is_receipt_done)
    order.is_gts_done = data.get('isGTSDone', order.is_gts_done)
    order.source = data.get('source', order.source)
    order.order_type = data.get('orderType', order.order_type)
    order.activity_log_id = data.get('activityLogId', order.activity_log_id)
    order.purchase_date = data.get('purchaseDate', order.purchase_date)
    order.comments = data.get('comments', order.comments)
    order.delivery_status = data.get('deliveryStatus', order.delivery_status)

    # Commit the changes to the database
    db.session.commit()

    return jsonify({'message': 'Order updated successfully'}), 200

# Endpoint to get all orders
@app.route('/api/get_orders', methods=['GET'])
def get_orders():
    orders = Order.query.all()  # Fetch all orders from the database
    return jsonify([{
        'id': order.id,
        'name': order.name,
        'phoneNumber': order.phone_number,
        'district': order.district,
        'price': order.price,
        'quantity': order.quantity,
        'quantityText': order.quantity_text,
        'remainingAmount': order.remaining_amount,
        'address': order.address,
        'email': order.email,
        'cargoBarcode': order.cargo_barcode,
        'gtsBarcode': order.gts_barcode,
        'tc': order.tc,
        'birthday': order.birthday,
        'isReceiptDone': order.is_receipt_done,
        'isGTSDone': order.is_gts_done,
        'source': order.source,
        'lastUpdate': order.last_update,
        'orderType': order.order_type,
        'activityLogId': order.activity_log_id,
        'purchaseDate': order.purchase_date,
        'comments': order.comments,
        'deliveryStatus': order.delivery_status,
    } for order in orders])

@app.route('/api/delete_order/<int:item_id>', methods=['DELETE'])
def delete_order(item_id):
    item = Order.query.get(item_id)  # Query the item by ID
    if item:
        db.session.delete(item)  # Delete the item
        db.session.commit()  # Commit the changes
        return jsonify({'message': 'Item deleted successfully'}), 200
    else:
        return jsonify({'message': 'Item not found'}), 404

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/api/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['image']
    image_id = request.form.get('image_id')  # Get the image ID from the form data

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # Save the file
        filename = f"{image_id}.jpg"  # Optionally prepend the image ID to the filename
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        return jsonify({'message': 'File uploaded successfully', 'file_path': file_path}), 200
    else:
        return jsonify({'error': 'File type not allowed'}), 400

@app.route('/api/get_image/<file_id>', methods=['GET'])
def get_image(file_id):
    # Construct the file path
    file_path = os.path.join("images", f"{file_id}.jpg")  # Assuming images are in JPG format

    # Check if the file exists
    if os.path.exists(file_path):
        return send_file(file_path)  # Send the image file
    else:
        abort(404)  # Return a 404 error if the file does not exist


@app.route("/payments/add", methods=["POST"])
def add_payment():
    data = request.json
    payment_id = data.get("payment_id")
    payment_date = data.get("payment_date")
    order_id = data.get("order_id")
    amount = data.get("amount")
    method = data.get("method", "Cash")
    note = data.get("note", "")

    order = ClientOrder.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    payment = PaymentLog(
        id=payment_id,
        order_id=order_id,
        amount=amount,
        method=method,
        note=note,
        payment_date=payment_date
    )

    order.remaining_amount = (order.remaining_amount or 0) - amount  # Update received money

    db.session.add(payment)
    db.session.commit()

    return jsonify({"message": "Payment added successfully", "payment_id": payment.id}), 200

@app.route("/payments/<order_id>", methods=["GET"])
def get_payments(order_id):
    payments = PaymentLog.query.filter_by(order_id=order_id).all()
    return jsonify([
        {
            "id": p.id,
            "order_id": p.order_id,
            "amount": p.amount,
            "payment_date": p.payment_date,
            "method": p.method,
            "note": p.note
        }
        for p in payments
    ])

@app.route("/payments/delete", methods=["POST"])
def delete_payment():
    data = request.json
    payment_id = data.get("payment_id")
    order_id = data.get("order_id")
    amount = data.get("amount")

    payment = PaymentLog.query.get(payment_id)
    if not payment:
        return jsonify({"error": "Payment not found"}), 404
    
    order = Order.query.get(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404

    order.remaining_amount = (order.remaining_amount or 0) + amount  # Update received money

    db.session.delete(payment)
    db.session.commit()

    return jsonify({"message": "Payment updated successfully", "payment_id": payment.id}), 200

@app.route('/api/get_gts_status/<string:barcode>', methods=['GET'])
def get_gts_status(barcode):
    product_db = next(get_product_db())
    try:
        # Search for barcode
        products = product_db.query(Product).filter(Product.barcode == barcode).all()
        if not products:
            # If not found by barcode, search by package_barcode
            products = product_db.query(Product).filter(Product.package_barcode == barcode).all()
        else:
            return jsonify({'is_gts_done': products[0].is_gts_done}), 200
            
        if products:
            retVal = True
            for p in products:
                retVal = retVal and p.is_gts_done
                
            return jsonify({'is_gts_done': retVal}), 200
        
        # Nothing found
        return jsonify({'is_gts_done': retVal, 'status': 'error', 'message': f'{barcode} barkoduna sahip ürün bulunamadı.'}), 404

    finally:
        product_db.close()

@app.route('/api/get_product_details/<string:barcode>', methods=['GET'])
def get_product_details(barcode):
    product_db = next(get_product_db())
    try:
        # Search for barcode
        products = product_db.query(Product).filter(Product.barcode == barcode).all()
        if not products:
            # If not found by barcode, search by package_barcode
            products = product_db.query(Product).filter(Product.package_barcode == barcode).all()
        
        if products:
            product_list = []
            for p in products:
                product_list.append({
                    'barcode': p.barcode,
                    'package_barcode': p.package_barcode,
                    'pallet_barcode': p.pallet_barcode,
                    'shipment_number': p.shipment_number,
                    'delivery_number': p.delivery_number,
                    'batch_number': p.batch_number,
                    'production_date': p.production_date,
                    'end_date': p.end_date,
                    'order_id': p.order_id,
                    'amount': p.amount,
                    'is_gts_done': p.is_gts_done,
                    'warehouse': p.warehouse,
                    'in_stock': p.in_stock
                })
            return jsonify(product_list), 200

        # Nothing found
        return jsonify({'status': 'error', 'message': f'{barcode} barkoduna sahip ürün bulunamadı.'}), 404

    finally:
        product_db.close()

@app.route('/api/products', methods=['GET'])
def get_all_products_grouped():
    product_db = next(get_product_db())
    try:
        products = product_db.query(Product).all()

        if not products:
            return jsonify({'status': 'error', 'message': 'Veritabanında ürün bulunamadı.'}), 404

        grouped = defaultdict(list)
        for product in products:
            grouped[product.package_barcode].append(product)

        result = []
        total_products = 0
        total_packages = 0
        total_gts_done = 0
        total_gts_not_done = 0
        package_size_counter = Counter()
        total_pending_amount = 0

        for package_barcode, product_list in grouped.items():
            products_data = []
            all_gts_done = all(p.is_gts_done for p in product_list)
            package_pending_amount = 0
            warehouse = ""
            in_stock = False
            for p in product_list:
                products_data.append({
                    'barcode': p.barcode,
                    'warehose': p.warehouse,
                    'order_id': p.order_id,
                    'is_gts_done': p.is_gts_done,
                    'in_stock': p.in_stock,
                    'amount': p.amount,
                })
                warehouse = p.warehouse
                in_stock = p.in_stock
                total_products += 1

                if p.is_gts_done:
                    total_gts_done += 1
                else:
                    total_gts_not_done += 1
                    package_pending_amount += p.amount or 0  # Only pending ones

            package_size = len(product_list)
            package_size_counter[(package_size, package_pending_amount)] += 1

            result.append({
                'package_barcode': package_barcode,
                'count': package_size,
                'warehouse': warehouse,
                'in_stock': in_stock,
                'pending_amount': package_pending_amount,
                'all_gts_done': all_gts_done,
                'products': products_data
            })

            total_packages += 1
            total_pending_amount += package_pending_amount

        result.sort(
            key=lambda x: (not x['all_gts_done'], x['count'])
        )

        # Create the basic summary
        basic_summary = (
            f"Toplam {total_packages} kolide {total_products} GTS barkodlu {total_pending_amount} lt ürün kaldı depoda.\n"
            f"{total_gts_done} ürünün GTS'si tamamlandı. {total_gts_not_done} tane işlenmemiş barkod mevcut."
        )

        # Create the detailed unique count summary
        detailed_summary_lines = []
        for (package_size, pending_amount), count in sorted(package_size_counter.items(), reverse=True):
            if pending_amount > 0:
                detailed_summary_lines.append(
                    f"{count} tane {package_size}x0.25'lik kolide {pending_amount} lt ürün var."
                )
        detailed_summary = "\n".join(detailed_summary_lines)

        return jsonify({
            'summary': basic_summary,
            'detailed_summary': detailed_summary,
            'packages': result
        }), 200

    finally:
        product_db.close()

@app.route('/api/update_product', methods=['POST'])
def update_product():
    data = request.json
    barcode = data.get('barcode')
    order_id = data.get('order_id')
    is_gts_done = data.get('is_gts_done')

    product_db = next(get_product_db())
    products_to_update = []
    search_type = "barkod"

    try:
        product = product_db.query(Product).filter(Product.barcode == barcode).first()
        if product:
            products_to_update.append(product)
        else:
            search_type = "paket barkodu"
            products_to_update = product_db.query(Product).filter(Product.package_barcode == barcode).all()

        if not products_to_update:
            return jsonify({'status': 'error', 'message': f"'{barcode}' {search_type} olan ürün bulunamadı."}), 404

        for product in products_to_update:
            product.order_id = order_id
            product.is_gts_done = is_gts_done

        product_db.commit()
        return jsonify({'status': 'success', 'message': f"{len(products_to_update)} adet ürünün GTS durumu ve sipariş ID'si güncellendi (arama türü: {search_type})."}), 200

    except Exception as e:
        print(e)
        product_db.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        product_db.close()

@app.route('/api/update_gts_barcode', methods=['POST'])
def update_order_gts():
    data = request.get_json()  # Get the JSON data from the request
    barcode = data["barcode"]
    print(data)
    order = db.session.get(Order, "order_id")
    if not order:
        return jsonify({'error': 'Order not found'}), 404

    order.is_gts_done = data["isGTSDone"]

    # Commit the changes to the database
    db.session.commit()

    return jsonify({'message': 'Order gts updated successfully'}), 200

# @app.route("/payments/summary", methods=["GET"])
# def get_payment_summary():
#     start_date_str = request.args.get("start_date")  # Expected: "YYYY-MM-DD"
#     end_date_str = request.args.get("end_date")  # Expected: "YYYY-MM-DD"

#     if not start_date_str or not end_date_str:
#         return jsonify({"error": "Missing start_date or end_date"}), 400

#     # Convert start_date and end_date to datetime objects
#     start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
#     end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

#     # Query for weekly summary
#     weekly_query = db.session.query(
#         func.strftime("%Y-%W", func.date(PaymentLog.payment_date, 'start of month')).label("week"),
#         PaymentLog.method,
#         func.sum(PaymentLog.amount).label("total_amount")
#     ).filter(
#         func.strftime("%d/%m/%Y", PaymentLog.payment_date).between(
#             start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y")
#         )
#     ).group_by("week", PaymentLog.method).order_by("week").all()

#     # Query for monthly summary
#     monthly_query = db.session.query(
#         func.strftime("%Y-%m", func.date(PaymentLog.payment_date, 'start of month')).label("month"),
#         PaymentLog.method,
#         func.sum(PaymentLog.amount).label("total_amount")
#     ).filter(
#         func.strftime("%d/%m/%Y", PaymentLog.payment_date).between(
#             start_date.strftime("%d/%m/%Y"), end_date.strftime("%d/%m/%Y")
#         )
#     ).group_by("month", PaymentLog.method).order_by("month").all()

#     # Format the results
#     weekly_summary = {}
#     for week, method, total in weekly_query:
#         if week not in weekly_summary:
#             weekly_summary[week] = {"iyzico": 0, "havale": 0, "nakit": 0}
#         weekly_summary[week][method] = total

#     monthly_summary = {}
#     for month, method, total in monthly_query:
#         if month not in monthly_summary:
#             monthly_summary[month] = {"iyzico": 0, "havale": 0, "nakit": 0}
#         monthly_summary[month][method] = total

#     return jsonify({
#         "weekly": weekly_summary,
#         "monthly": monthly_summary
#     })

BACKEND_AVAILABLE = True

@app.route('/api/health', methods=['GET'])
def health_check():
    if BACKEND_AVAILABLE:
        return jsonify({"status": "ok"}), 200
    else:
        return jsonify({"status": "maintenance"}), 503

from sqlalchemy.exc import IntegrityError

@app.route('/api/migrate_orders_to_clients_and_client_orders', methods=['GET'])
def migrate_orders_to_clients_and_client_orders():
    orders = Order.query.all()
    for order in orders:
        # First, create or get the Client
        client = Client(
            id=order.id,  # Assuming phone_number is unique for Client ID (you can adjust this)
            name=order.name,
            phone_number=order.phone_number,
            district=order.district,
            address=order.address,
            tc=order.tc,
            birthday=order.birthday,
            source=order.source if order.source else "Unknown",
            comments=order.comments,
            email=order.email,
            title="Müşteri",  # You can set a default title; adjust if needed
            gts_number=""
        )

        try:
            db.session.add(client)
            db.session.commit()
        except IntegrityError:
            # Client already exists (same ID/phone number), rollback and continue
            db.session.rollback()

        # Then, create the ClientOrder
        client_order = ClientOrder(
            id=order.id,
            client_id=client.id,
            quantity=order.quantity,
            quantity_text=order.quantity_text,
            price=order.price,
            remaining_amount=order.remaining_amount,
            is_receipt_done=order.is_receipt_done,
            is_gts_done=order.is_gts_done,
            cargo_barcode=order.cargo_barcode,
            gts_barcode=order.gts_barcode,
            order_type=order.order_type,
            last_update=order.last_update,
            purchase_date=order.purchase_date,
            comments=order.comments,
            delivery_status=order.delivery_status,
            intermediar_id=order.intermediar_id,
            intermediar_amount=order.intermediar_amount,
            product_type=order.product_type
        )

        db.session.add(client_order)

    db.session.commit()
    print("Migration completed successfully.")
    return 200

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8082)