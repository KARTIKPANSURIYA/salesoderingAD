import os

from flask import Flask, render_template, request, redirect, url_for, session
import csv
from datetime import datetime
from flask import send_file
from fpdf import FPDF

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Secret key for session management


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

    # Save PDF
    output_dir = "static/pdfs"
    pdf_filename = f"{output_dir}/order_{customer_account}.pdf"
    pdf.output(pdf_filename)
    return pdf_filename





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

    app.run(debug=True)
