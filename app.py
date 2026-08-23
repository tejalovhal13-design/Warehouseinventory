from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import check_password_hash
from flask_wtf.csrf import CSRFProtect
import mysql.connector
import os

app = Flask(__name__)

# CSRF protection
csrf = CSRFProtect(app)

# ==================================================
# SECURITY CONFIGURATION
# ==================================================

# Secret key
# For your local project, this fallback will work.
# For real deployment, set WIMS_SECRET_KEY as an environment variable.
app.secret_key = os.environ.get(
    "WIMS_SECRET_KEY",
    "change-this-development-secret-key"
)

# Session security
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Keep False while running on localhost.
# Change to True when using HTTPS in deployment.
app.config["SESSION_COOKIE_SECURE"] = False


# ==================================================
# MYSQL DATABASE CONNECTION
# ==================================================

def get_db_connection():

    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="tejal@ayansh#1306",
        database="wims"
    )


# ==================================================
# LOGIN PAGE
# ==================================================

@app.route("/")
def login():

    return render_template("login.html")


# ==================================================
# LOGIN AUTHENTICATION
# ==================================================

@app.route("/login", methods=["POST"])
def login_user():

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    # ----------------------------------------------
    # Basic validation
    # ----------------------------------------------

    if not email or not password:

        return """
        <h3>Email and password are required.</h3>
        <a href="/">Go back to Login</a>
        """


    # ----------------------------------------------
    # Database connection
    # ----------------------------------------------

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ----------------------------------------------
    # Find user using email
    # ----------------------------------------------

    cursor.execute(
        """
        SELECT user_id, name, email, password, role
        FROM users
        WHERE email = %s
        """,
        (email,)
    )

    user = cursor.fetchone()


    cursor.close()
    connection.close()


    # ----------------------------------------------
    # Verify hashed password
    # ----------------------------------------------

    if user and check_password_hash(
        user["password"],
        password
    ):

        # Clear any old session data
        session.clear()

        # Store only required user information
        session["user_id"] = user["user_id"]
        session["name"] = user["name"]
        session["role"] = user["role"]

        return redirect(url_for("dashboard"))


    # ----------------------------------------------
    # Invalid login
    # ----------------------------------------------

    return """
    <h3>Invalid email or password</h3>
    <a href="/">Go back to Login</a>
    """


# ==================================================
# DASHBOARD
# ==================================================

@app.route("/dashboard")
def dashboard():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:

        return redirect(url_for("login"))


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ----------------------------------------------
    # Total devices
    # ----------------------------------------------

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total_devices
        FROM products
    """)

    total_devices = cursor.fetchone()["total_devices"]


    # ----------------------------------------------
    # Low stock
    # ----------------------------------------------

    cursor.execute("""
        SELECT COUNT(*) AS low_stock
        FROM products
        WHERE quantity > 0
        AND quantity <= minimum_stock
    """)

    low_stock = cursor.fetchone()["low_stock"]


    # ----------------------------------------------
    # Out of stock
    # ----------------------------------------------

    cursor.execute("""
        SELECT COUNT(*) AS out_of_stock
        FROM products
        WHERE quantity = 0
    """)

    out_of_stock = cursor.fetchone()["out_of_stock"]


    # ----------------------------------------------
    # Recent products
    # ----------------------------------------------

    cursor.execute("""
        SELECT *
        FROM products
        ORDER BY product_id DESC
        LIMIT 5
    """)

    products = cursor.fetchall()


    # ==================================================
    # DYNAMIC STOCK OVERVIEW
    # ==================================================

    # Total quantity

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total_quantity
        FROM products
    """)

    total_quantity = cursor.fetchone()["total_quantity"]


    # Quantity by category

    cursor.execute("""
        SELECT
            category,
            SUM(quantity) AS category_quantity
        FROM products
        GROUP BY category
        ORDER BY category_quantity DESC
    """)

    stock_overview = cursor.fetchall()


    # Calculate percentage

    for item in stock_overview:

        if total_quantity > 0:

            item["percentage"] = round(
                (item["category_quantity"] / total_quantity) * 100,
                1
            )

        else:

            item["percentage"] = 0


    # ----------------------------------------------
    # Close database
    # ----------------------------------------------

    cursor.close()
    connection.close()


    # ----------------------------------------------
    # Send data to dashboard
    # ----------------------------------------------

    return render_template(
        "dashboard.html",

        name=session["name"],
        role=session["role"],

        total_devices=total_devices,
        low_stock=low_stock,
        out_of_stock=out_of_stock,

        products=products,

        stock_overview=stock_overview
    )


# ==================================================
# INVENTORY
# ==================================================

@app.route("/inventory")
def inventory():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:

        return redirect(url_for("login"))


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ----------------------------------------------
    # Get all products
    # ----------------------------------------------

    cursor.execute("""
        SELECT *
        FROM products
        ORDER BY product_id DESC
    """)

    products = cursor.fetchall()


    # ----------------------------------------------
    # Total devices
    # ----------------------------------------------

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total_devices
        FROM products
    """)

    total_devices = cursor.fetchone()["total_devices"]


    # ----------------------------------------------
    # Low stock
    # ----------------------------------------------

    cursor.execute("""
        SELECT COUNT(*) AS low_stock
        FROM products
        WHERE quantity > 0
        AND quantity <= minimum_stock
    """)

    low_stock = cursor.fetchone()["low_stock"]


    # ----------------------------------------------
    # Out of stock
    # ----------------------------------------------

    cursor.execute("""
        SELECT COUNT(*) AS out_of_stock
        FROM products
        WHERE quantity = 0
    """)

    out_of_stock = cursor.fetchone()["out_of_stock"]


    cursor.close()
    connection.close()


    return render_template(
        "inventory.html",

        name=session["name"],
        role=session["role"],

        products=products,

        total_devices=total_devices,
        low_stock=low_stock,
        out_of_stock=out_of_stock
    )


# ==================================================
# ADD PRODUCT
# ==================================================

@app.route("/inventory/add", methods=["GET", "POST"])
def add_product():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:

        return redirect(url_for("login"))


    # ----------------------------------------------
    # Show Add Product page
    # ----------------------------------------------

    if request.method == "GET":

        return render_template(
            "add_product.html",

            name=session["name"],
            role=session["role"]
        )


    # ----------------------------------------------
    # Get form data
    # ----------------------------------------------

    product_name = request.form.get(
        "product_name", ""
    ).strip()

    category = request.form.get(
        "category", ""
    ).strip()

    brand = request.form.get(
        "brand", ""
    ).strip()

    model = request.form.get(
        "model", ""
    ).strip()

    quantity = request.form.get(
        "quantity", ""
    )

    price = request.form.get(
        "price", ""
    )

    minimum_stock = request.form.get(
        "minimum_stock", ""
    )

    supplier = request.form.get(
        "supplier", ""
    ).strip()

    warehouse = request.form.get(
        "warehouse", ""
    ).strip()


    # ----------------------------------------------
    # Basic validation
    # ----------------------------------------------

    if not product_name or not category:

        return """
        <h3>Product name and category are required.</h3>
        <a href="/inventory">Back to Inventory</a>
        """


    # ----------------------------------------------
    # Database connection
    # ----------------------------------------------

    connection = get_db_connection()
    cursor = connection.cursor()


    # ----------------------------------------------
    # Insert product
    # Parameterized query prevents SQL injection
    # ----------------------------------------------

    cursor.execute("""
        INSERT INTO products
        (
            product_name,
            category,
            brand,
            model,
            quantity,
            price,
            minimum_stock,
            supplier,
            warehouse
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        product_name,
        category,
        brand,
        model,
        quantity,
        price,
        minimum_stock,
        supplier,
        warehouse
    ))


    connection.commit()

    cursor.close()
    connection.close()


    return redirect(url_for("inventory"))


# ==================================================
# EDIT PRODUCT
# ==================================================

@app.route(
    "/inventory/edit/<int:product_id>",
    methods=["GET", "POST"]
)
def edit_product(product_id):

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:

        return redirect(url_for("login"))


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ==================================================
    # GET PRODUCT
    # ==================================================

    if request.method == "GET":

        cursor.execute("""
            SELECT *
            FROM products
            WHERE product_id = %s
        """, (product_id,))

        product = cursor.fetchone()


        cursor.close()
        connection.close()


        if product is None:

            return "Product not found", 404


        return render_template(
            "edit_product.html",

            product=product,

            name=session["name"],
            role=session["role"]
        )


    # ==================================================
    # UPDATE PRODUCT
    # ==================================================

    product_name = request.form.get(
        "product_name", ""
    ).strip()

    category = request.form.get(
        "category", ""
    ).strip()

    brand = request.form.get(
        "brand", ""
    ).strip()

    model = request.form.get(
        "model", ""
    ).strip()

    quantity = request.form.get(
        "quantity", ""
    )

    price = request.form.get(
        "price", ""
    )

    minimum_stock = request.form.get(
        "minimum_stock", ""
    )

    supplier = request.form.get(
        "supplier", ""
    ).strip()

    warehouse = request.form.get(
        "warehouse", ""
    ).strip()


    # ----------------------------------------------
    # Update database
    # ----------------------------------------------

    cursor.execute("""
        UPDATE products

        SET
            product_name = %s,
            category = %s,
            brand = %s,
            model = %s,
            quantity = %s,
            price = %s,
            minimum_stock = %s,
            supplier = %s,
            warehouse = %s

        WHERE product_id = %s

    """, (
        product_name,
        category,
        brand,
        model,
        quantity,
        price,
        minimum_stock,
        supplier,
        warehouse,
        product_id
    ))


    connection.commit()

    cursor.close()
    connection.close()


    return redirect(url_for("inventory"))


# ==================================================
# DELETE PRODUCT
# ==================================================

@app.route("/inventory/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor()

    # ----------------------------------------------
    # Delete product
    # Parameterized query
    # ----------------------------------------------

    cursor.execute("""
        DELETE FROM products
        WHERE product_id = %s
    """, (product_id,))

    connection.commit()

    cursor.close()
    connection.close()

    return redirect(url_for("inventory"))

# ==================================================
# STOCK MOVEMENT
# ==================================================

@app.route("/stock-movement", methods=["GET", "POST"])
def stock_movement():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ----------------------------------------------
    # POST - Process Stock Movement
    # ----------------------------------------------

    if request.method == "POST":

        product_id = request.form.get("product_id")
        movement_type = request.form.get("movement_type")
        quantity = request.form.get("quantity")


        # ------------------------------------------
        # Basic validation
        # ------------------------------------------

        if not product_id or movement_type not in ["IN", "OUT"] or not quantity:

            cursor.close()
            connection.close()

            return "Invalid stock movement data.", 400


        try:

            quantity = int(quantity)

            if quantity <= 0:
                raise ValueError

        except ValueError:

            cursor.close()
            connection.close()

            return "Quantity must be a positive number.", 400


        # ------------------------------------------
        # Get current product stock
        # ------------------------------------------

        cursor.execute("""
            SELECT quantity
            FROM products
            WHERE product_id = %s
        """, (product_id,))

        product = cursor.fetchone()


        if product is None:

            cursor.close()
            connection.close()

            return "Product not found.", 404


        current_quantity = product["quantity"]


        # ------------------------------------------
        # Calculate new quantity
        # ------------------------------------------

        if movement_type == "IN":

            new_quantity = current_quantity + quantity

        else:

            if quantity > current_quantity:

                cursor.close()
                connection.close()

                return "Insufficient stock.", 400

            new_quantity = current_quantity - quantity


        # ------------------------------------------
        # Update product quantity
        # ------------------------------------------

        cursor.execute("""
            UPDATE products
            SET quantity = %s
            WHERE product_id = %s
        """, (new_quantity, product_id))


        # ------------------------------------------
        # Record stock movement
        # ------------------------------------------

        cursor.execute("""
            INSERT INTO stock_movements
            (
                product_id,
                movement_type,
                quantity,
                user_id
            )
            VALUES (%s, %s, %s, %s)
        """, (
            product_id,
            movement_type,
            quantity,
            session["user_id"]
        ))


        # ------------------------------------------
        # Save changes
        # ------------------------------------------

        connection.commit()


        cursor.close()
        connection.close()


        return redirect(url_for("stock_movement"))


    # ----------------------------------------------
    # GET - Get products
    # ----------------------------------------------

    cursor.execute("""
        SELECT
            product_id,
            product_name,
            quantity
        FROM products
        ORDER BY product_name ASC
    """)

    products = cursor.fetchall()


    # ----------------------------------------------
    # GET - Get movement history
    # ----------------------------------------------

    cursor.execute("""
        SELECT
            sm.movement_id,
            p.product_name,
            sm.movement_type,
            sm.quantity,
            sm.movement_date,
            u.name AS user_name
        FROM stock_movements sm

        INNER JOIN products p
            ON sm.product_id = p.product_id

        INNER JOIN users u
            ON sm.user_id = u.user_id

        ORDER BY sm.movement_date DESC
    """)

    movements = cursor.fetchall()


    # ----------------------------------------------
    # Close database
    # ----------------------------------------------

    cursor.close()
    connection.close()


    # ----------------------------------------------
    # Display page
    # ----------------------------------------------

    return render_template(
        "stock_movement.html",

        name=session["name"],
        role=session["role"],

        products=products,
        movements=movements
    )
# ==================================================
# WAREHOUSES
# ==================================================

@app.route("/warehouses")
def warehouses():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # ----------------------------------------------
    # Get warehouses
    # ----------------------------------------------

    cursor.execute("""
        SELECT
            warehouse_id,
            warehouse_name,
            location,
            manager_name,
            contact_number,
            status
        FROM warehouses
        ORDER BY warehouse_id DESC
    """)

    warehouses = cursor.fetchall()

    cursor.close()
    connection.close()

    # ----------------------------------------------
    # Display page
    # ----------------------------------------------

    return render_template(
        "warehouses.html",

        name=session["name"],
        role=session["role"],

        warehouses=warehouses
    )

# ==================================================
# ADD WAREHOUSE
# ==================================================

@app.route("/add-warehouse", methods=["GET", "POST"])
def add_warehouse():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    # ----------------------------------------------
    # POST - Add warehouse
    # ----------------------------------------------

    if request.method == "POST":

        warehouse_name = request.form.get("warehouse_name", "").strip()
        location = request.form.get("location", "").strip()
        manager_name = request.form.get("manager_name", "").strip()
        contact_number = request.form.get("contact_number", "").strip()
        status = request.form.get("status", "Active").strip()

        # ------------------------------------------
        # Basic validation
        # ------------------------------------------

        if not warehouse_name or not location or not manager_name or not contact_number:

            return """
            <h3>All warehouse fields are required.</h3>
            <a href="/add-warehouse">Go back</a>
            """

        # ------------------------------------------
        # Database connection
        # ------------------------------------------

        connection = get_db_connection()
        cursor = connection.cursor()

        # ------------------------------------------
        # Insert warehouse
        # ------------------------------------------

        cursor.execute("""
            INSERT INTO warehouses
            (
                warehouse_name,
                location,
                manager_name,
                contact_number,
                status
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            warehouse_name,
            location,
            manager_name,
            contact_number,
            status
        ))

        connection.commit()

        cursor.close()
        connection.close()

        # ------------------------------------------
        # Return to warehouses page
        # ------------------------------------------

        return redirect(url_for("warehouses"))

    # ----------------------------------------------
    # GET - Display form
    # ----------------------------------------------

    return render_template(
        "add_warehouse.html",

        name=session["name"],
        role=session["role"]
    )

# ==================================================
# MAKE WAREHOUSE INACTIVE
# ==================================================

@app.route("/warehouse/<int:warehouse_id>/inactive", methods=["POST"])
def make_warehouse_inactive(warehouse_id):

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    # ----------------------------------------------
    # Database connection
    # ----------------------------------------------

    connection = get_db_connection()
    cursor = connection.cursor()

    # ----------------------------------------------
    # Change warehouse status
    # ----------------------------------------------

    cursor.execute("""
        UPDATE warehouses
        SET status = 'Inactive'
        WHERE warehouse_id = %s
    """, (warehouse_id,))

    connection.commit()

    cursor.close()
    connection.close()

    # ----------------------------------------------
    # Return to warehouses page
    # ----------------------------------------------

    return redirect(url_for("warehouses"))

# ==================================================
# ACTIVATE WAREHOUSE
# ==================================================

@app.route("/warehouse/<int:warehouse_id>/activate", methods=["POST"])
def activate_warehouse(warehouse_id):

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    # ----------------------------------------------
    # Database connection
    # ----------------------------------------------

    connection = get_db_connection()
    cursor = connection.cursor()

    # ----------------------------------------------
    # Change warehouse status
    # ----------------------------------------------

    cursor.execute("""
        UPDATE warehouses
        SET status = 'Active'
        WHERE warehouse_id = %s
    """, (warehouse_id,))

    connection.commit()

    cursor.close()
    connection.close()

    # ----------------------------------------------
    # Return to warehouses page
    # ----------------------------------------------

    return redirect(url_for("warehouses"))

# ==================================================
# ORDERS
# ==================================================

@app.route("/orders")
def orders():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # ----------------------------------------------
    # Get all orders
    # ----------------------------------------------

    cursor.execute("""
        SELECT
            order_id,
            product_id,
            quantity,
            order_type,
            party_name,
            warehouse,
            order_date,
            status
        FROM orders
        ORDER BY order_id DESC
    """)

    orders = cursor.fetchall()

    cursor.close()
    connection.close()

    # ----------------------------------------------
    # Display page
    # ----------------------------------------------

    return render_template(
        "orders.html",

        name=session["name"],
        role=session["role"],

        orders=orders
    )

# ==================================================
# ADD ORDER
# ==================================================

@app.route("/orders/add", methods=["GET", "POST"])
def add_order():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    # ----------------------------------------------
    # GET PRODUCTS
    # ----------------------------------------------

    cursor.execute("""
        SELECT
            product_id,
            product_name,
            brand,
            model,
            warehouse
        FROM products
        ORDER BY product_name ASC
    """)

    products = cursor.fetchall()


    # ----------------------------------------------
    # SHOW ADD ORDER PAGE
    # ----------------------------------------------

    if request.method == "GET":

        cursor.close()
        connection.close()

        return render_template(
            "add_order.html",

            products=products,

            name=session["name"],
            role=session["role"]
        )


    # ----------------------------------------------
    # GET FORM DATA
    # ----------------------------------------------

    product_id = request.form.get("product_id")
    quantity = request.form.get("quantity")
    order_type = request.form.get("order_type")
    party_name = request.form.get("party_name", "").strip()
    warehouse = request.form.get("warehouse", "").strip()
    order_date = request.form.get("order_date")


    # ----------------------------------------------
    # BASIC VALIDATION
    # ----------------------------------------------

    if not product_id or not quantity or not order_type \
            or not party_name or not warehouse or not order_date:

        cursor.close()
        connection.close()

        return """
        <h3>All fields are required.</h3>
        <a href="/orders/add">Back to Add Order</a>
        """


    # ----------------------------------------------
    # INSERT ORDER
    # ----------------------------------------------

    cursor.execute("""
        INSERT INTO orders
        (
            product_id,
            quantity,
            order_type,
            party_name,
            warehouse,
            order_date,
            status
        )
        VALUES (%s, %s, %s, %s, %s, %s, 'Pending')
    """, (
        product_id,
        quantity,
        order_type,
        party_name,
        warehouse,
        order_date
    ))


    connection.commit()

    cursor.close()
    connection.close()


    return redirect(url_for("orders"))


# ==================================================
# COMPLETE ORDER
# ==================================================

@app.route(
    "/orders/complete/<int:order_id>",
    methods=["POST"]
)
def complete_order(order_id):

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    try:

        # ------------------------------------------
        # Start transaction
        # ------------------------------------------

        connection.start_transaction()


        # ------------------------------------------
        # Get order
        # ------------------------------------------

        cursor.execute("""
            SELECT *
            FROM orders
            WHERE order_id = %s
            FOR UPDATE
        """, (order_id,))

        order = cursor.fetchone()


        # ------------------------------------------
        # Order not found
        # ------------------------------------------

        if order is None:

            connection.rollback()

            return "Order not found", 404


        # ------------------------------------------
        # Prevent completing twice
        # ------------------------------------------

        if order["status"] != "Pending":

            connection.rollback()

            return redirect(url_for("orders"))


        product_id = order["product_id"]
        order_quantity = order["quantity"]
        order_type = order["order_type"]


        # ------------------------------------------
        # Get product
        # ------------------------------------------

        cursor.execute("""
            SELECT *
            FROM products
            WHERE product_id = %s
            FOR UPDATE
        """, (product_id,))

        product = cursor.fetchone()


        # ------------------------------------------
        # Product not found
        # ------------------------------------------

        if product is None:

            connection.rollback()

            return "Product not found", 404


        current_quantity = product["quantity"]


        # ==========================================
        # OUTGOING ORDER
        # ==========================================

        if order_type == "Outgoing":

            # --------------------------------------
            # Check available stock
            # --------------------------------------

            if current_quantity < order_quantity:

                connection.rollback()

                return f"""
                <h3>Insufficient Stock</h3>

                <p>
                    Available stock:
                    <strong>{current_quantity}</strong>
                </p>

                <p>
                    Required quantity:
                    <strong>{order_quantity}</strong>
                </p>

                <br>

                <a href="/orders">
                    Back to Orders
                </a>
                """, 400


            # --------------------------------------
            # Decrease inventory
            # --------------------------------------

            new_quantity = current_quantity - order_quantity

            cursor.execute("""
                UPDATE products
                SET quantity = %s
                WHERE product_id = %s
            """, (
                new_quantity,
                product_id
            ))


            # --------------------------------------
            # Add OUT stock movement
            # --------------------------------------

            cursor.execute("""
                INSERT INTO stock_movements
                (
                    product_id,
                    movement_type,
                    quantity,
                    user_id
                )
                VALUES (%s, 'OUT', %s, %s)
            """, (
                product_id,
                order_quantity,
                session["user_id"]
            ))


        # ==========================================
        # INCOMING ORDER
        # ==========================================

        elif order_type == "Incoming":

            # --------------------------------------
            # Increase inventory
            # --------------------------------------

            new_quantity = current_quantity + order_quantity

            cursor.execute("""
                UPDATE products
                SET quantity = %s
                WHERE product_id = %s
            """, (
                new_quantity,
                product_id
            ))


            # --------------------------------------
            # Add IN stock movement
            # --------------------------------------

            cursor.execute("""
                INSERT INTO stock_movements
                (
                    product_id,
                    movement_type,
                    quantity,
                    user_id
                )
                VALUES (%s, 'IN', %s, %s)
            """, (
                product_id,
                order_quantity,
                session["user_id"]
            ))


        # ------------------------------------------
        # Mark order as completed
        # ------------------------------------------

        cursor.execute("""
            UPDATE orders
            SET status = 'Completed'
            WHERE order_id = %s
        """, (order_id,))


        # ------------------------------------------
        # Save everything
        # ------------------------------------------

        connection.commit()


    except Exception as e:

        # ------------------------------------------
        # If anything fails, undo everything
        # ------------------------------------------

        connection.rollback()

        print("Complete Order Error:", e)

        return "Something went wrong while completing the order.", 500


    finally:

        cursor.close()
        connection.close()


    return redirect(url_for("orders"))

# ==================================================
# CANCEL ORDER
# ==================================================

@app.route(
    "/orders/cancel/<int:order_id>",
    methods=["POST"]
)
def cancel_order(order_id):

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))


    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    try:

        # ------------------------------------------
        # Get order
        # ------------------------------------------

        cursor.execute("""
            SELECT *
            FROM orders
            WHERE order_id = %s
        """, (order_id,))

        order = cursor.fetchone()


        # ------------------------------------------
        # Order not found
        # ------------------------------------------

        if order is None:

            return "Order not found", 404


        # ------------------------------------------
        # Only Pending orders can be cancelled
        # ------------------------------------------

        if order["status"] != "Pending":

            return redirect(url_for("orders"))


        # ------------------------------------------
        # Cancel order
        # ------------------------------------------

        cursor.execute("""
            UPDATE orders

            SET status = 'Cancelled'

            WHERE order_id = %s
        """, (order_id,))


        connection.commit()


    except Exception as e:

        connection.rollback()

        return f"""
        <h3>Error cancelling order.</h3>

        <p>{e}</p>

        <a href="/orders">
            Back to Orders
        </a>
        """


    finally:

        cursor.close()
        connection.close()


    return redirect(url_for("orders"))


# ==================================================
# REPORTS
# ==================================================

@app.route("/reports")
def reports():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)

    # ==================================================
    # INVENTORY SUMMARY
    # ==================================================

    # Total number of products

    cursor.execute("""
        SELECT COUNT(*) AS total_products
        FROM products
    """)

    total_products = cursor.fetchone()["total_products"]


    # Total stock quantity

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS total_stock
        FROM products
    """)

    total_stock = cursor.fetchone()["total_stock"]


    # Low stock products

    cursor.execute("""
        SELECT COUNT(*) AS low_stock
        FROM products
        WHERE quantity > 0
        AND quantity <= minimum_stock
    """)

    low_stock = cursor.fetchone()["low_stock"]


    # Out of stock products

    cursor.execute("""
        SELECT COUNT(*) AS out_of_stock
        FROM products
        WHERE quantity = 0
    """)

    out_of_stock = cursor.fetchone()["out_of_stock"]


    # ==================================================
    # ORDER SUMMARY
    # ==================================================

    # Total orders

    cursor.execute("""
        SELECT COUNT(*) AS total_orders
        FROM orders
    """)

    total_orders = cursor.fetchone()["total_orders"]


    # Pending orders

    cursor.execute("""
        SELECT COUNT(*) AS pending_orders
        FROM orders
        WHERE status = 'Pending'
    """)

    pending_orders = cursor.fetchone()["pending_orders"]


    # Completed orders

    cursor.execute("""
        SELECT COUNT(*) AS completed_orders
        FROM orders
        WHERE status = 'Completed'
    """)

    completed_orders = cursor.fetchone()["completed_orders"]


    # Cancelled orders

    cursor.execute("""
        SELECT COUNT(*) AS cancelled_orders
        FROM orders
        WHERE status = 'Cancelled'
    """)

    cancelled_orders = cursor.fetchone()["cancelled_orders"]


    # ==================================================
    # STOCK MOVEMENT SUMMARY
    # ==================================================

    # Total movements

    cursor.execute("""
        SELECT COUNT(*) AS total_movements
        FROM stock_movements
    """)

    total_movements = cursor.fetchone()["total_movements"]


    # Total incoming quantity

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS incoming_quantity
        FROM stock_movements
        WHERE movement_type = 'IN'
    """)

    incoming_quantity = cursor.fetchone()["incoming_quantity"]


    # Total outgoing quantity

    cursor.execute("""
        SELECT COALESCE(SUM(quantity), 0) AS outgoing_quantity
        FROM stock_movements
        WHERE movement_type = 'OUT'
    """)

    outgoing_quantity = cursor.fetchone()["outgoing_quantity"]


    # ==================================================
    # LOW STOCK PRODUCTS
    # ==================================================

    cursor.execute("""
        SELECT
            product_id,
            product_name,
            category,
            quantity,
            minimum_stock,
            warehouse
        FROM products
        WHERE quantity > 0
        AND quantity <= minimum_stock
        ORDER BY quantity ASC
    """)

    low_stock_products = cursor.fetchall()


    # ==================================================
    # RECENT ORDERS
    # ==================================================

    cursor.execute("""
        SELECT
            order_id,
            product_id,
            quantity,
            order_type,
            party_name,
            warehouse,
            order_date,
            status
        FROM orders
        ORDER BY order_id DESC
        LIMIT 10
    """)

    recent_orders = cursor.fetchall()


    # ==================================================
    # RECENT STOCK MOVEMENTS
    # ==================================================

    cursor.execute("""
        SELECT
            sm.movement_id,
            p.product_name,
            sm.movement_type,
            sm.quantity,
            sm.movement_date,
            u.name AS user_name
        FROM stock_movements sm

        INNER JOIN products p
            ON sm.product_id = p.product_id

        INNER JOIN users u
            ON sm.user_id = u.user_id

        ORDER BY sm.movement_date DESC
        LIMIT 10
    """)

    recent_movements = cursor.fetchall()


    # ----------------------------------------------
    # Close database
    # ----------------------------------------------

    cursor.close()
    connection.close()


    # ----------------------------------------------
    # Display report page
    # ----------------------------------------------

    return render_template(
        "reports.html",

        name=session["name"],
        role=session["role"],

        # Inventory
        total_products=total_products,
        total_stock=total_stock,
        low_stock=low_stock,
        out_of_stock=out_of_stock,

        # Orders
        total_orders=total_orders,
        pending_orders=pending_orders,
        completed_orders=completed_orders,
        cancelled_orders=cancelled_orders,

        # Stock movements
        total_movements=total_movements,
        incoming_quantity=incoming_quantity,
        outgoing_quantity=outgoing_quantity,

        # Tables
        low_stock_products=low_stock_products,
        recent_orders=recent_orders,
        recent_movements=recent_movements
    )

# ==================================================
# SETTINGS
# ==================================================

@app.route("/settings")
def settings():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))


    # ----------------------------------------------
    # Display Settings page
    # ----------------------------------------------

    return render_template(
        "settings.html",

        name=session["name"],
        role=session["role"]
    )

# ==================================================
# CHANGE PASSWORD
# ==================================================

@app.route("/change-password", methods=["POST"])
def change_password():

    # ----------------------------------------------
    # Access control
    # ----------------------------------------------

    if "user_id" not in session:
        return redirect(url_for("login"))


    current_password = request.form.get(
        "current_password",
        ""
    )

    new_password = request.form.get(
        "new_password",
        ""
    )

    confirm_password = request.form.get(
        "confirm_password",
        ""
    )


    # ----------------------------------------------
    # Basic validation
    # ----------------------------------------------

    if not current_password or not new_password or not confirm_password:

        return """
        <h3>All password fields are required.</h3>
        <a href="/settings">Back to Settings</a>
        """


    # ----------------------------------------------
    # Check new password
    # ----------------------------------------------

    if new_password != confirm_password:

        return """
        <h3>New passwords do not match.</h3>
        <a href="/settings">Back to Settings</a>
        """


    if len(new_password) < 8:

        return """
        <h3>Password must contain at least 8 characters.</h3>
        <a href="/settings">Back to Settings</a>
        """


    # ----------------------------------------------
    # Database connection
    # ----------------------------------------------

    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)


    try:

        # ------------------------------------------
        # Get current password
        # ------------------------------------------

        cursor.execute("""
            SELECT password
            FROM users
            WHERE user_id = %s
        """, (session["user_id"],))

        user = cursor.fetchone()


        if user is None:

            return "User not found", 404


        # ------------------------------------------
        # Verify current password
        # ------------------------------------------

        if not check_password_hash(
            user["password"],
            current_password
        ):

            return """
            <h3>Current password is incorrect.</h3>
            <a href="/settings">Back to Settings</a>
            """


        # ------------------------------------------
        # Hash new password
        # ------------------------------------------

        from werkzeug.security import generate_password_hash

        new_password_hash = generate_password_hash(
            new_password
        )


        # ------------------------------------------
        # Update password
        # ------------------------------------------

        cursor.execute("""
            UPDATE users
            SET password = %s
            WHERE user_id = %s
        """, (
            new_password_hash,
            session["user_id"]
        ))


        connection.commit()


    except Exception as e:

        connection.rollback()

        print("Change Password Error:", e)

        return """
        <h3>Something went wrong while changing the password.</h3>
        <a href="/settings">Back to Settings</a>
        """


    finally:

        cursor.close()
        connection.close()


    return """
    <h3>Password changed successfully.</h3>
    <a href="/settings">Return to Settings</a>
    """
# ==================================================
# LOGOUT
# ==================================================

@app.route("/logout")
def logout():

    # Remove all session information

    session.clear()

    return redirect(url_for("login"))


# ==================================================
# RUN APPLICATION
# ==================================================

if __name__ == "__main__":

    app.run(host="0.0.0.0", port=8000, debug=False)