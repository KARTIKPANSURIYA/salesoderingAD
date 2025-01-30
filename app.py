from flask import Flask, render_template, request, redirect, url_for, session
import csv
from datetime import datetime

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Secret key for session management


# Validate credentials from CSV
def validate_credentials(salesman_id, password):
    try:
        with open("salesmen.csv", mode="r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row["salesman_id"] == salesman_id and row["password"] == password:
                    return row["name"]  # Return name if valid credentials
        return None
    except FileNotFoundError:
        return None


# Save order to CSV
def save_order(data):
    with open("orders.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(data)


@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        salesman_id = request.form["salesman_id"]
        password = request.form["password"]
        name = validate_credentials(salesman_id, password)
        if name:
            session["salesman"] = name  # Store salesman name in session
            return redirect(url_for("order_form"))
        return render_template("login.html", error="Invalid credentials!")
    return render_template("login.html")


@app.route("/order", methods=["GET", "POST"])
def order_form():
    if "salesman" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Collect form data
        customer_account = request.form["customer_account"]
        store_name = request.form["store_name"]
        products = request.form.getlist("product_name[]")  # List of product search inputs
        quantities = request.form.getlist("quantity[]")  # List of quantities

        # Pair product names with quantities
        paired_products = [(product, quantity) for product, quantity in zip(products, quantities) if
                           product and quantity]

        delivery_date = request.form["delivery_date"]
        priority = request.form["priority"]
        description = request.form["description"]

        # Save order data to CSV
        order_data = [
            session["salesman"],
            customer_account,
            store_name,
            str(paired_products),  # Store paired products as a string
            delivery_date,
            priority,
            description
        ]
        save_order(order_data)  # Function to save to `orders.csv`
        return render_template("order_success.html")

    return render_template("order_form.html")


@app.route("/logout")
def logout():
    session.pop("salesman", None)  # Remove salesman from session
    return redirect(url_for("login"))

# Load products from CSV
def load_products():
    try:
        with open("skincare_products_clean.csv", mode="r") as file:
            reader = csv.DictReader(file)
            products = [row["product_name"] for row in reader]  # Adjust column name if necessary
            return products
    except FileNotFoundError:
        return []

# Save new product to CSV
def save_new_product(product_name, variant="", price=0, description=""):
    with open("skincare_products_clean.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([product_name, variant, price, description])

# Route to fetch products dynamically (for AJAX)
@app.route("/products", methods=["GET"])
def get_products():
    products = load_products()
    return {"products": products}, 200

if __name__ == "__main__":
    # Create orders.csv if it doesn't exist
    try:
        with open("orders.csv", mode="x", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["Salesman", "Customer Account", "Store Name",
                             "Product Details", "Delivery Date", "Priority", "Description"])
    except FileExistsError:
        pass

    app.run(debug=True)
