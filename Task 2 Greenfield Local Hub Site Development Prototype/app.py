from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
import os
from werkzeug.utils import secure_filename
from datetime import datetime



ADMIN_PRODUCER_KEY = "IAMMUSIC"
app = Flask(__name__)
app.secret_key = "Croski-Kun"

app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///users.db'
db = SQLAlchemy(app)



def require_login():
    return "user_id" in session

def require_producer():
    return session.get("role") == "producer"

def require_customer():
    return session.get("role") == "customer"

def calculate_cart_total(cart):
    total = 0
    for product_id, qty in cart.items():
        product = Product.query.get(int(product_id))
        if product:
            total += product.price_gbp * qty
    return total

#Database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="customer")
    name = db.Column(db.String(50))
    phone = db.Column(db.String(50))
    adress = db.Column(db.String(300))
    loyalty_points = db.Column(db.Integer, default=0)
    profile_image = db.Column(db.String(200), default="default.jpg")
    products = db.relationship("Product", backref="producer", lazy=True)
    customer_orders = db.relationship(
        "Order",
        foreign_keys="Order.customer_id",
        backref="customer_user",
        lazy=True
    )

    producer_items = db.relationship(
    "OrderItem",
    foreign_keys="OrderItem.producer_id",
    backref="producer_user",
    lazy=True
)

      

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(300), nullable=False)
    description = db.Column(db.Text)
    price_gbp = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)
    image = db.Column(db.String(255))
    producer_id = db.Column(db.Integer, db.ForeignKey('user.id'))



class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_price_gbp = db.Column(db.Float)
    items = db.relationship("OrderItem", backref="order", lazy=True)



class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)

    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))
    product_id = db.Column(db.Integer, db.ForeignKey("product.id"))
    producer_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    status = db.Column(db.String(20), default="Pending")
    quantity = db.Column(db.Integer, default=1)
    price_each_gbp = db.Column(db.Float)
    product = db.relationship("Product")
    producer = db.relationship("User")

with app.app_context():
    db.create_all()



@app.route("/")
def home():
    products = Product.query.limit(4).all()
    producers = User.query.filter_by(role="producer").all()
    logged_in = "user_id" in session
    return render_template(
    "home.html",
    logged_in=logged_in,
    email=session.get("email"),
    products=products,
    producers= producers
)

    
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        email = request.form["email"]
        password = request.form["psw"]
        repeat = request.form["psw_repeat"]
        role = request.form.get("role", "customer")

        if password != repeat:
            return "Passwords do not match"

        existing = User.query.filter_by(email=email).first()
        if existing:
            return "Email already registered. Please log in."

        if role == "producer":
            admin_key = request.form.get("admin_key")
            if admin_key != ADMIN_PRODUCER_KEY:
                return "Invalid admin key. You cannot register as a producer."

        user = User(
            email=email,
            password=password,
            role=role,
            name=name
        )
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session["user_id"] = user.id
            session["email"] = user.email
            session["role"] = user.role
            session["name"] = user.name

            if user.role == "producer":
                return redirect(url_for("producer_dashboard"))
            else:
                return redirect(url_for("customer_dashboard"))

        return "Invalid Login"
        
    return render_template("login.html")



@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route('/products')
def products_page():
    query = request.args.get('q', '').lower()

    all_products = Product.query.all()

    if query:
        filtered_products = [p for p in all_products if query in p.name.lower()]
    else:
        filtered_products = all_products

    return render_template('products.html', products=filtered_products)




@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = Product.query.get_or_404(product_id)
    return render_template("product_detail.html", product=product)


#dASHBOARD  
@app.route("/producer/add_product", methods=["GET", "POST"])
def add_product():
    if not require_producer():
        return redirect("/login")

    producer = User.query.get(session["user_id"])

    if request.method == "POST":
        name = request.form["name"]
        description = request.form["description"]
        price = float(request.form["price"])
        stock = int(request.form["stock"])
        image = request.form["image"]
        new_product = Product(
            name=name,
            description=description,
            price_gbp=price,
            stock=stock,
            image=image,
            producer_id=producer.id
        )

        db.session.add(new_product)
        db.session.commit()

        return redirect(url_for("producer_dashboard"))

    return render_template("add_product.html", producer=producer)





@app.route("/producer_dashboard")
def producer_dashboard():
    if "user_id" not in session:
        return redirect("/login")

    producer = User.query.get(session["user_id"])

    if producer.role != "producer":
        return "Access denied"

    products = Product.query.filter_by(producer_id=producer.id).all()

    return render_template(
        "producer_dashboard.html",
        producer=producer,
        products=products
    )



@app.route("/upload_profile_image", methods=["POST"])
def upload_profile_image():
    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    if "profile_image" not in request.files:
        return redirect("/account")

    file = request.files["profile_image"]

    if file.filename == "":
        return redirect("/account")

    filename = secure_filename(file.filename)
    filepath = os.path.join("static/images/producers", filename)
    file.save(filepath)

    user.profile_image = filename
    db.session.commit()

    return redirect("/account")


@app.route("/customer/dashboard")
def customer_dashboard():
    if session.get("role") != "customer":
        return redirect("/login")

    user = User.query.get(session["user_id"])
    return render_template("customer_dashboard.html", user=user)


#Cart Functionality
@app.route("/cart")
def cart():
    cart = session.get("cart", {})

    cart_items = []
    cart_total = 0

    for pid, qty in cart.items():
        product = Product.query.get(int(pid))
        if product:
            line_total = product.price_gbp * qty
            cart_items.append({
                "product": product,
                "quantity": qty,
                "line_total" : line_total
                })
            cart_total += line_total

    return render_template("cart.html",
                           cart_items=cart_items,
                           cart_total=cart_total)
                           
@app.route("/remove_from_cart/<int:product_id>")
def remove_from_cart(product_id):
    cart = session.get("cart", {})
    if str(product_id) in cart:
        del cart[str(product_id)]

    session["cart"] = cart
    return redirect("/cart")                       


@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):

    if "user_id" not in session:
        return redirect(f"/login?next=/add_to_cart/{product_id}")

    cart = session.get("cart", {})
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    session["cart"] = cart

    return redirect('/products')



@app.route("/producer/<int:producer_id>")
def producer_profile(producer_id):
    producer  = User.query.filter_by(role="producer")
    return render_template("producer_profile.html",producer=producer)




def get_cart():
    return session.get("cart",{})

@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        return redirect("/login")

    cart = session.get("cart", {})
    if not cart:
        return redirect("/cart")

    user = User.query.get(session["user_id"])

    if request.method == "POST":
        total_amount = calculate_cart_total(cart)

      
        discount = min(user.loyalty_points, 20)
        final_price = total_amount - discount

 
        user.loyalty_points -= discount

        user.loyalty_points += int(final_price // 10)

        order = Order(
            customer_id=user.id,
            total_price_gbp=final_price
        )
        db.session.add(order)
        db.session.commit()

        for pid, qty in cart.items():
            product = Product.query.get(int(pid))
            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                producer_id=product.producer_id,
                quantity=qty,
                price_each_gbp=product.price_gbp
            )

            db.session.add(item)
            product.stock -= qty

        db.session.commit()

   
        session["cart"] = {}

        return redirect(f"/order/{order.id}/summary")

    total = calculate_cart_total(cart)
    return render_template("checkout.html", cart=cart, total=total, user=user)




@app.route("/account")
def account():
    if "user_id" not in session:
        return redirect("/login")
    user = User.query.get(session["user_id"])
    return render_template("account.html", user=user)

@app.route("/account/orders")
def account_orders():
    if "user_id" not in session:
        return redirect("/login")
    user = User.query.get(session["user_id"])
    return render_template("order_history.html", orders=user.orders)

@app.route("/producer/orders")
def producer_orders():
    if session.get("role") != "producer":
        return redirect("/login")

    producer_id = session["user_id"]

    items = OrderItem.query.filter_by(producer_id=producer_id).all()

    return render_template("producer_orders.html", items=items)




@app.route("/product/<int:id>/delete", methods=["POST"])
def delete_product(id):
    if "user_id" not in session:
        return redirect("/login")

    product = Product.query.get_or_404(id)

    if product.producer_id != session["user_id"]:
        return "Unauthorized", 403

    db.session.delete(product)
    db.session.commit()

    return redirect("/producer_dashboard")



@app.route("/product/<int:id>/edit", methods=["GET", "POST"])
def edit_product(id):
    if "user_id" not in session:
        return redirect("/login")

    product = Product.query.get_or_404(id)

    if product.producer_id != session["user_id"]:
        return "Unauthorised", 403
    
    if request.method == "POST":
        product.name = request.form["name"]
        product.price_gbp = request.form["price"]
        product.stock = request.form["stock"]
        product.description = request.form["description"]
        db.session.commit()
        return redirect(f"/product/{id}")

    return render_template("edit_product.html", product=product)

@app.route("/order/<int:id>/summary")
def order_summary(id):
    order = Order.query.get_or_404(id)

  
    if order.customer_id != session.get("user_id"):
        return "Unauthorized", 403

  
    order_items = OrderItem.query.filter_by(order_id=id).all()

    subtotal = sum(item.price_each_gbp * item.quantity for item in order_items)
    discount = getattr(order, "discount", 0)
    total = order.total_price_gbp
    points_earned = int(total)

    return render_template(
        "order_summary.html",
        order=order,
        order_items=order_items,
        subtotal=subtotal,
        discount=discount,
        total=total,
        points_earned=points_earned
    )


@app.route("/orders")
def order_history():
    orders = Order.query.filter_by(customer_id=session["user_id"]).order_by(Order.created_at.desc()).all()
    return render_template("order_history.html", orders=orders)


@app.route("/producer/approve/<int:order_id>")
def approve_order(order_id):
    if session.get("role") != "producer":
        return redirect("/login")

    order = Order.query.get_or_404(order_id)

    
    if order.producer_id != session["user_id"]:
        return "Unauthorized", 403

    order.status = "Approved"
    db.session.commit()

    return redirect("/producer/orders")




@app.route("/producer/item/<int:item_id>/approve")
def approve_item(item_id):
    if session.get("role") != "producer":
        return redirect("/login")

    item = OrderItem.query.get_or_404(item_id)

    if item.producer_id != session["user_id"]:
        return "Unauthorized", 403

    item.status = "Approved"
    db.session.commit()

    return redirect("/producer/orders")


if __name__ == "__main__":
    app.run(debug=True)


with app.app_context():
    db.create_all()


    default_producer = User.query.filter_by(email="greenfield@produce.com").first()
    if not default_producer:
        default_producer = User(
            email="greenfield@produce.com",
            password="default123",
            role="producer",
            name="Greenfield Produce"
        )
        db.session.add(default_producer)
        db.session.commit()

    default_products = [
        ("Fresh Greenfield Apples", "Cool Apples.", 2.50, 100, "apples.jpg"),
        ("Greenfield Organic Carrots", "Bright Carrots.", 1.80, 150, "carrots.jpg"),
        ("Greenfield Free-Range Eggs (12 pack)", "Chicken Eggs.", 3.20, 80, "eggs.jpg"),
        ("Thick Greenfield Wine", "Rich homemade wine.", 13.50, 80, "wine.jpg"),
        ("Freshly Baked Bread", "Soft warm bread.", 1.80, 20, "bread.jpg"),
        ("Crisp Greenfield Lettuce", "Fresh crunchy lettuce.", 1.20, 60, "lettuce.jpg"),
        ("Sweet Greenfield Strawberries", "Juicy red strawberries.", 2.90, 90, "strawberries.jpg"),
        ("Golden Greenfield Honey", "Pure natural honey.", 5.50, 40, "honey.jpg"),
        ("Creamy Greenfield Milk", "Fresh whole milk.", 1.10, 100, "milk.jpg"),
        ("Zesty Greenfield Lemons", "Fresh yellow lemons.", 1.50, 120, "lemons.jpg"),
        ("Juicy Greenfield Oranges", "Sweet oranges.", 2.20, 110, "oranges.jpg"),
        ("Tender Greenfield Chicken", "Farm-raised chicken.", 6.80, 50, "chicken.jpg"),
        ("Smooth Greenfield Butter", "Creamy farm butter.", 2.40, 70, "butter.jpg"),
        ("Hearty Greenfield Potatoes", "Fresh earthy potatoes.", 1.60, 200, "potatoes.jpg"),
        ("Crispy Greenfield Cucumbers", "Cool crunchy cucumbers.", 1.30, 90, "cucumbers.jpg"),
        ("Ripe Greenfield Tomatoes", "Red juicy tomatoes.", 2.10, 140, "tomatoes.jpg"),
        ("Warm Greenfield Muffins", "Freshly baked muffins.", 2.50, 30, "muffins.jpg"),
        ("Soft Greenfield Cheese", "Creamy farmhouse cheese.", 4.20, 60, "cheese.jpg"),
        ("Crisp Greenfield Peppers", "Fresh mixed peppers.", 2.40, 80, "peppers.jpg"),
        ("Sweet Greenfield Corn", "Golden sweetcorn.", 1.90, 100, "corn.jpg"),
        ("Fresh Greenfield Spinach", "Leafy green spinach.", 1.70, 70, "spinach.jpg"),
    ]

    for name, desc, price, stock, image in default_products:
        existing = Product.query.filter_by(name=name).first()
        if not existing:
            new_product = Product(
                name=name,
                description=desc,
                price_gbp=price,
                stock=stock,
                image=image,
                producer_id=default_producer.id
            )
            db.session.add(new_product)

    db.session.commit()
