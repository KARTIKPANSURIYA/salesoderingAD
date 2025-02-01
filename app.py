import os

from flask import Flask, render_template, request, redirect, url_for, session, Response
import csv
from datetime import datetime
from flask import send_file
from fpdf import FPDF
from flask import flash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Secret key for session management

# Hardcoded Admin Credentials (You can later store this in a database)
ADMIN_CREDENTIALS = {
    "admin": "admin123"  # Username: Password
}

########## ADMIN SETTINGS
# Admin Login Route
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        admin_id = request.form["admin_id"]
        password = request.form["password"]

        if admin_id in ADMIN_CREDENTIALS and ADMIN_CREDENTIALS[admin_id] == password:
            session["admin"] = admin_id  # Store admin session
            flash("Admin login successful!", "success")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Invalid credentials!", "danger")

    return render_template("admin_login.html")
# Admin Logout Route
@app.route("/admin-logout")
def admin_logout():
    session.pop("admin", None)  # Remove admin from session
    flash("You have been logged out.", "info")
    return redirect(url_for("admin_login"))

# View All Salesmen
@app.route("/admin-salesmen")
def admin_salesmen():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    salesmen = []
    try:
        with open("salesmen.csv", "r") as file:
            reader = csv.DictReader(file)
            salesmen = list(reader)
    except FileNotFoundError:
        flash("Salesmen data not found!", "danger")

    return render_template("admin_salesmen.html", salesmen=salesmen)

# Add a New Salesman
@app.route("/admin-add-salesman", methods=["GET", "POST"])
def admin_add_salesman():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    if request.method == "POST":
        salesman_id = request.form["salesman_id"]
        name = request.form["name"]
        password = request.form["password"]

        # Append new salesman to CSV
        with open("salesmen.csv", "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([salesman_id, name, password])

        flash("Salesman account created successfully!", "success")
        return redirect(url_for("admin_salesmen"))

    return render_template("admin_add_salesman.html")

@app.route("/admin-dashboard")
def admin_dashboard():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    # Count salesmen from salesmen.csv
    try:
        with open("salesmen.csv", "r") as file:
            reader = csv.DictReader(file)
            salesmen = list(reader)
            total_salesmen = len(salesmen)
    except FileNotFoundError:
        total_salesmen = 0

    # Count orders from orders.csv (Handle Empty File)
    total_orders = 0
    try:
        with open("orders.csv", "r") as file:
            reader = csv.reader(file)
            header = next(reader, None)  # Skip header safely

            if header:  # If the file is not empty
                orders = list(reader)
                total_orders = len(orders)

    except FileNotFoundError:
        total_orders = 0

    return render_template(
        "admin_dashboard.html",
        total_salesmen=total_salesmen,
        total_orders=total_orders
    )


@app.route("/admin-edit-order/<order_id>", methods=["GET", "POST"])
def admin_edit_order(order_id):
    # Fetch all orders
    orders = []
    with open("orders.csv", "r") as file:
        reader = csv.reader(file)
        header = next(reader)  # Save the header row
        for row in reader:
            orders.append(row)

    # Find the specific order to edit
    order_to_edit = None
    for order in orders:
        if order[1] == order_id:  # Assuming order ID is in the second column
            order_to_edit = order
            break

    if not order_to_edit:
        flash("Order not found!", "danger")
        return redirect("/admin-orders")

    # Fetch the list of products
    products = []
    with open("skincare_products_clean.csv", "r") as file:
        reader = csv.DictReader(file)
        for row in reader:
            products.append({"name": row["product_name"], "price": row.get("price", "")})

    # On POST, update the order
    if request.method == "POST":
        updated_order = [
            request.form["salesman"],
            order_id,
            request.form["store_name"],
            str([{"name": name, "quantity": qty} for name, qty in zip(request.form.getlist("product_name[]"), request.form.getlist("quantity[]"))]),
            request.form["delivery_date"],
            request.form["priority"],
            order_to_edit[6],  # Preserve original order placed date
            request.form["description"]
        ]

        # Update the order in the list
        for idx, order in enumerate(orders):
            if order[1] == order_id:
                orders[idx] = updated_order
                break

        # Save all orders back to the file
        with open("orders.csv", "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(header)  # Write the header row
            writer.writerows(orders)  # Write all updated orders

        flash("Order updated successfully!", "success")
        return redirect("/admin-orders")

    # Render the edit order page
    return render_template(
        "admin_edit_order.html",
        order=order_to_edit,
        product_details=eval(order_to_edit[3]),  # Convert string back to product details
        products=products,
    )



@app.route("/admin-orders", methods=["GET"])
def admin_orders():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    orders = []
    search_query = request.args.get("search", "").lower()
    filter_priority = request.args.get("priority", "")
    filter_date = request.args.get("date", "")  # Delivery Date
    filter_order_date = request.args.get("order_date", "")  # Order Placed Date

    try:
        with open("orders.csv", "r") as file:
            reader = csv.reader(file)
            header = next(reader, None)

            for row in reader:
                if len(row) < 8:
                    continue  # Skip invalid rows

                salesman, customer_account, store_name, product_details, delivery_date, priority, order_date, description = row

                # Extract only the date portion from the order_date field for comparison
                order_date_only = order_date.split(" ")[0]  # Get date part (e.g., "2025-01-30")

                # Ensure correct filtering logic
                if (
                        (search_query in salesman.lower() or
                         search_query in customer_account.lower() or
                         search_query in store_name.lower())
                        and (filter_priority == "" or filter_priority == priority)
                        and (filter_date == "" or filter_date == delivery_date)
                        and (filter_order_date == "" or filter_order_date == order_date_only)  # Updated filtering
                ):
                    orders.append(
                        [salesman, customer_account, store_name, product_details, delivery_date, priority, order_date,
                         description])

        # Sort orders by order placing date (latest first)
        orders.sort(key=lambda x: x[6], reverse=True)

    except FileNotFoundError:
        flash("No orders found!", "danger")

    return render_template("admin_orders.html", orders=orders, search_query=search_query,
                           filter_priority=filter_priority, filter_date=filter_date,
                           filter_order_date=filter_order_date)


# orders download admin dashboard
@app.route("/download-orders")
def download_orders():
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    try:
        with open("orders.csv", "r") as file:
            csv_content = file.read()

        response = Response(csv_content, mimetype="text/csv")
        response.headers["Content-Disposition"] = "attachment; filename=all_orders.csv"
        return response

    except FileNotFoundError:
        flash("No orders available to download!", "danger")
        return redirect(url_for("admin_orders"))
# Edit Salesman
@app.route("/admin-edit-salesman/<salesman_id>", methods=["GET", "POST"])
def admin_edit_salesman(salesman_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    salesmen = []
    try:
        with open("salesmen.csv", "r") as file:
            reader = csv.DictReader(file)
            salesmen = list(reader)
    except FileNotFoundError:
        flash("Salesmen data not found!", "danger")
        return redirect(url_for("admin_salesmen"))

    # Find the salesman to edit
    salesman = next((s for s in salesmen if s["salesman_id"] == salesman_id), None)

    if not salesman:
        flash("Salesman not found!", "danger")
        return redirect(url_for("admin_salesmen"))

    if request.method == "POST":
        new_id = request.form["salesman_id"]
        new_name = request.form["name"]
        new_password = request.form["password"]

        # Update the salesman record
        for s in salesmen:
            if s["salesman_id"] == salesman_id:
                s["salesman_id"] = new_id
                s["name"] = new_name
                s["password"] = new_password

        # Save updated data to CSV
        with open("salesmen.csv", "w", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["salesman_id", "name", "password"])
            writer.writeheader()
            writer.writerows(salesmen)

        flash("Salesman details updated successfully!", "success")
        return redirect(url_for("admin_salesmen"))

    return render_template("admin_edit_salesman.html", salesman=salesman)

# Delete Salesman
@app.route("/admin-delete-salesman/<salesman_id>", methods=["POST"])
def admin_delete_salesman(salesman_id):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    salesmen = []
    try:
        with open("salesmen.csv", "r") as file:
            reader = csv.DictReader(file)
            salesmen = list(reader)
    except FileNotFoundError:
        flash("Salesmen data not found!", "danger")
        return redirect(url_for("admin_salesmen"))

    # Remove the salesman with matching ID
    salesmen = [s for s in salesmen if s["salesman_id"] != salesman_id]

    # Save updated data to CSV
    with open("salesmen.csv", "w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=["salesman_id", "name", "password"])
        writer.writeheader()
        writer.writerows(salesmen)

    flash("Salesman deleted successfully!", "success")
    return redirect(url_for("admin_salesmen"))

@app.route("/admin-delete-order/<customer_account>", methods=["POST"])
def admin_delete_order(customer_account):
    if "admin" not in session:
        return redirect(url_for("admin_login"))

    orders = []
    try:
        with open("orders.csv", "r") as file:
            reader = csv.reader(file)
            header = next(reader, None)
            orders = [row for row in reader if row[1] != customer_account]
    except FileNotFoundError:
        flash("Orders not found!", "danger")
        return redirect(url_for("admin_orders"))

    # Save updated orders back to CSV
    with open("orders.csv", "w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(orders)

    flash("Order deleted successfully!", "success")
    return redirect(url_for("admin_orders"))


##########
class CustomPDF(FPDF):
    def header(self):
        # Minimal header with title
        self.set_font("Arial", style="B", size=16)
        self.cell(0, 10, "Order Summary", ln=True, align="C")
        self.ln(10)  # Add spacing


def generate_pdf(salesman, customer_account, store_name, delivery_date, priority, order_date, description, products, staff_placeholders):
    pdf = CustomPDF()
    pdf.add_page()

    # Header Section
    pdf.set_font("Arial", size=12)
    pdf.cell(95, 10, f"Salesman: {salesman}", border=1)
    pdf.cell(95, 10, f"Customer Account: {customer_account}", border=1, ln=True)
    pdf.cell(95, 10, f"Store Name: {store_name}", border=1)
    pdf.cell(95, 10, f"Delivery Date: {delivery_date}", border=1, ln=True)
    pdf.cell(95, 10, f"Delivery Priority: {priority}", border=1)
    pdf.cell(95, 10, f"Order Placed: {order_date}", border=1, ln=True)
    pdf.ln(10)

    # Description Section
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(0, 10, "Description:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.multi_cell(190, 10, description, border=1)
    pdf.ln(10)

    # Product Table Header
    pdf.set_font("Arial", style="B", size=12)
    col_widths = [30, 40, 80, 40]  # Fixed widths for AD Code, Barcode, Product Name, Quantity
    pdf.cell(col_widths[0], 10, "AD Code", border=1, align="C")
    pdf.cell(col_widths[1], 10, "Barcode", border=1, align="C")
    pdf.cell(col_widths[2], 10, "Product Name", border=1, align="C")
    pdf.cell(col_widths[3], 10, "Quantity", border=1, align="C", ln=True)

    # Product Table Rows
    pdf.set_font("Arial", size=10)
    for product in products:
        # Split product name into lines and calculate row height
        product_name_lines = pdf.multi_cell(col_widths[2], 10, product.get("name", ""), border=0, split_only=True)
        max_lines = max(
            len(product_name_lines),
            1  # Ensure at least one line
        )
        row_height = max_lines * 10  # 10 units per line

        # Draw the row with synchronized heights
        y_start = pdf.get_y()  # Starting Y position
        pdf.cell(col_widths[0], row_height, product.get("ad_code", ""), border=1, align="C")
        pdf.cell(col_widths[1], row_height, product.get("barcode", ""), border=1, align="C")
        x_pos = pdf.get_x()
        pdf.multi_cell(col_widths[2], 10, product.get("name", ""), border=1, align="L")
        pdf.set_xy(x_pos + col_widths[2], y_start)  # Reset position for Quantity
        pdf.cell(col_widths[3], row_height, str(product.get("quantity", "")), border=1, align="C", ln=True)

    pdf.ln(10)

    # Footer for Staff Section (2x2 Grid Layout)
    pdf.set_font("Arial", style="B", size=12)
    pdf.cell(0, 10, "For Staff:", ln=True)
    pdf.set_font("Arial", size=12)

    for i in range(0, len(staff_placeholders), 2):  # Process two placeholders per row
        placeholder_1 = staff_placeholders[i]
        placeholder_2 = staff_placeholders[i + 1] if i + 1 < len(staff_placeholders) else ""

        pdf.cell(95, 10, f"{placeholder_1}: __________", border=1)
        if placeholder_2:
            pdf.cell(95, 10, f"{placeholder_2}: __________", border=1, ln=True)
        else:
            pdf.ln(10)

    # Ensure the output directory exists
    output_dir = "static/pdfs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    pdf_filename = f"{output_dir}/order_{customer_account}.pdf"
    pdf.output(pdf_filename)
    return pdf_filename


@app.route("/dashboard")
def dashboard():
    if "salesman" not in session:
        return redirect(url_for("login"))

    try:
        # Read orders from the CSV file
        with open("orders.csv", "r") as file:
            reader = csv.reader(file)
            next(reader)  # Skip header row
            orders = list(reader)

        total_orders = len(orders)
        recent_orders = orders[-5:] if len(orders) > 5 else orders

        # Get the most recent order's PDF file
        if orders:
            last_order = orders[-1]
            customer_account = last_order[1]
            pdf_path = f"/static/pdfs/order_{customer_account}.pdf"
        else:
            pdf_path = None

    except FileNotFoundError:
        total_orders = 0
        recent_orders = []
        pdf_path = None

    return render_template(
        "dashboard.html",
        total_orders=total_orders,
        recent_orders=recent_orders,
        pdf_path=pdf_path
    )




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

@app.route("/download-pdf/<customer_account>")
def download_pdf(customer_account):
    # Load the order data for the given customer_account (you may need to read it from a database or CSV)
    try:
        with open("orders.csv", mode="r") as file:
            reader = csv.reader(file)
            for row in reader:
                # Match the order based on customer account
                if row[1] == customer_account:
                    salesman = row[0]
                    store_name = row[2]
                    products = eval(row[3])  # Convert string to list of tuples
                    delivery_date = row[4]
                    priority = row[5]
                    description = row[6]
                    break
            else:
                return "Order not found", 404  # If no matching order is found
    except FileNotFoundError:
        return "Orders file not found", 500

    # Generate the PDF
    pdf_filename = generate_pdf(
        salesman,
        customer_account,
        store_name,
        products,
        delivery_date,
        priority,
        description
    )

    # Serve the PDF as a downloadable file
    return send_file(
        pdf_filename,
        as_attachment=True,
        download_name=pdf_filename,
        mimetype="application/pdf"
    )


@app.route("/order", methods=["GET", "POST"])
def order_form():
    if "salesman" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Collect form data
        customer_account = request.form["customer_account"]
        store_name = request.form["store_name"]
        products = request.form.getlist("product_name[]")
        quantities = request.form.getlist("quantity[]")
        delivery_date = request.form["delivery_date"]
        priority = request.form["priority"]
        description = request.form["description"]  # ✅ Ensure description is collected

        # Pair products with quantities
        paired_products = [{"ad_code": f"AD{index + 1}",
                            "barcode": f"BAR{index + 1:03}",
                            "name": product,
                            "quantity": quantity} for index, (product, quantity) in enumerate(zip(products, quantities))]

        # Save the order to CSV or database
        order_data = [
            session["salesman"],
            customer_account,
            store_name,
            str(paired_products),
            delivery_date,
            priority,
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            description  # ✅ Ensure description is saved
        ]
        save_order(order_data)

        # Generate PDF (Fixed: Added `description` argument)
        pdf_filename = generate_pdf(
            salesman=session["salesman"],
            customer_account=customer_account,
            store_name=store_name,
            delivery_date=delivery_date,
            priority=priority,
            order_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            description=description,  # ✅ Pass description here
            products=paired_products,
            staff_placeholders=["Order Pulled", "Order Verified", "Order Shipped", "Payment"]
        )
        # Flash a success message
        flash("Order submitted successfully!", "success")
        return redirect(url_for("dashboard"))

        # Redirect to success page
        return render_template("order_success.html", customer_account=customer_account, pdf_filename=pdf_filename)


    # Render the order form for GET requests
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

    app.run(host="0.0.0.0", port=5001)

