from flask import Flask,request,redirect,render_template,session,url_for,jsonify,flash
import pymysql
import pymysql.cursors
from werkzeug.security import generate_password_hash,check_password_hash
from flask_mail import Mail,Message
import secrets
import os
from pymysql.cursors import DictCursor
from werkzeug.utils import secure_filename
import razorpay

con = pymysql.connect(
    host = "localhost",
    user = "root",
    password = "",
    database = "manufacture",
    cursorclass=pymysql.cursors.DictCursor 
)
app = Flask(__name__)
app.secret_key = 'hdjfjkdhe'
cursor = con.cursor()

client = razorpay.Client(auth=("rzp_test_RLhlv7OvzhV9ma", "1cvZAOcfJ49Ntrs3EIhkb48P")) 

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USERNAME'] = 'hetvisuthar311@gmail.com'
app.config['MAIL_PASSWORD'] = 'izcykjlqumdtlqze'
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False

mail = Mail(app)

productimgpath = "static/uploads/product"
blogimgpath = "static/uploads/blog"
sizeimgpath = "static/uploads/size"
popup = "static/uploads/popup"

@app.route("/admin/admin_login", methods = ['POST','GET'])
def admin_login():
    cursor = con.cursor(pymysql.cursors.DictCursor)

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        sql = "SELECT * FROM `admin_login` WHERE email = %s"
        cursor.execute(sql,(email,))
        admin = cursor.fetchone()

        if admin and check_password_hash(admin[2],password):
            session['admin_id'] = admin[0]
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin/admin_login.html', error="Invalid email or password")

    return render_template('admin/admin_login.html')

@app.route("/admin/admin_logout")
def admin_logout():
    session.pop('admin_id',None)
    return redirect(url_for('admin_login'))

@app.route("/admin/admin_forgotpassword", methods=['GET', 'POST'])
def admin_forgotpassword():
    if request.method == 'POST':
        email = request.form['email']
        sql = "SELECT * FROM admin_login WHERE email = %s"
        cursor.execute(sql, (email,))
        admin = cursor.fetchone()

        if admin:
            token = secrets.token_urlsafe(16)
            update_sql = "UPDATE admin_login SET reset_token = %s WHERE email = %s"
            cursor.execute(update_sql, (token, email))
            con.commit()

            reset_link = url_for('admin_resetpassword', token=token, _external=True)

            msg = Message("Password Reset Request",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email])
            msg.body = f"Click the link to reset your password:\n{reset_link}\n\nIf you did not request this, please ignore this email."
            mail.send(msg)

            return render_template("admin/admin_forgotpassword.html", message="Reset link sent to your email.")
        else:
            return render_template("admin/admin_forgotpassword.html", error="Email not found.")

    return render_template("admin/admin_forgotpassword.html")

@app.route("/admin/admin_resetpassword/<token>", methods=['GET', 'POST'])
def admin_resetpassword(token):
    sql = "SELECT * FROM admin_login WHERE reset_token = %s"
    cursor.execute(sql, (token,))
    admin = cursor.fetchone()

    if not admin:
        return "Invalid or expired reset link!"

    if request.method == 'POST':
        new_password = request.form['password']
        hashed_password = generate_password_hash(new_password)

        update_sql = "UPDATE admin_login SET password = %s, reset_token = NULL WHERE reset_token = %s"
        cursor.execute(update_sql, (hashed_password, token))
        con.commit()

        return redirect(url_for('admin_login'))

    return render_template('admin/admin_resetpassword.html')


@app.route("/admin/admin_product")
def admin_product():
    return render_template('admin/admin_product.html')

@app.route("/addproduct", methods=['POST'])
def addproduct():
    name = request.form['name']
    description = request.form['description']
    
    has_type = 1 if request.form.get('has_type') else 0
    is_new = 1 if request.form.get('is_new') else 0
    is_featured = 1 if request.form.get('is_featured') else 0

    image1 = request.files.get('image1')
    image2 = request.files.get('image2')
    image3 = request.files.get('image3')

    image1_name = secure_filename(image1.filename) if image1 else None
    image2_name = secure_filename(image2.filename) if image2 else None
    image3_name = secure_filename(image3.filename) if image3 else None

    if image1:
        image1.save(os.path.join(productimgpath, image1_name))
    if image2:
        image2.save(os.path.join(productimgpath, image2_name))
    if image3:
        image3.save(os.path.join(productimgpath, image3_name))

    sql = """
        INSERT INTO products 
        (name, description, has_type, image1, image2, image3, is_new, is_featured)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """
    val = (name, description, has_type, image1_name, image2_name, image3_name, is_new, is_featured)

    cursor.execute(sql, val)
    con.commit()

    flash("Product added successfully!", "success")
    return redirect('/admin/admin_productlist')

@app.route("/admin/admin_productlist")
def admin_productlist():
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template("admin/admin_productlist.html", products=products)

@app.route("/admin/edit_product/<int:id>", methods=['GET', 'POST'])
def edit_product(id):
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        has_type = 1 if request.form.get('has_type') else 0
        is_new = 1 if request.form.get('is_new') else 0
        is_featured = 1 if request.form.get('is_featured') else 0

        image1 = request.files.get('image1')
        image2 = request.files.get('image2')
        image3 = request.files.get('image3')

        cursor.execute("SELECT image1, image2, image3 FROM products WHERE id=%s", (id,))
        old_images = cursor.fetchone()

        image1_name = old_images['image1']
        image2_name = old_images['image2']
        image3_name = old_images['image3']

        if image1 and image1.filename != '':
            image1_name = secure_filename(image1.filename)
            image1.save(os.path.join(productimgpath, image1_name))
        if image2 and image2.filename != '':
            image2_name = secure_filename(image2.filename)
            image2.save(os.path.join(productimgpath, image2_name))
        if image3 and image3.filename != '':
            image3_name = secure_filename(image3.filename)
            image3.save(os.path.join(productimgpath, image3_name))

        sql = """
            UPDATE products SET
                name=%s, description=%s, has_type=%s,
                is_new=%s, is_featured=%s,
                image1=%s, image2=%s, image3=%s
            WHERE id=%s
        """
        val = (name, description, has_type, is_new, is_featured,
               image1_name, image2_name, image3_name, id)
        cursor.execute(sql, val)
        con.commit()
        flash("Product updated successfully!", "success")
        return redirect(url_for('admin_productlist'))

    cursor.execute("SELECT * FROM products WHERE id=%s", (id,))
    product = cursor.fetchone()
    return render_template("admin/admin_editproduct.html", product=product)

@app.route("/admin/delete_product/<int:id>", methods=['POST'])
def delete_product(id):
    cursor.execute("DELETE FROM products WHERE id=%s", (id,))
    con.commit()
    flash("Product deleted successfully!", "success")
    return redirect(url_for('admin_productlist'))

@app.route("/admin/admin_variant", methods=['GET', 'POST'])
def admin_variant():
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT id, name FROM products")
    products = cursor.fetchall()
    print("Products fetched:", products)  

    if request.method == 'POST':
        product_id = request.form['product_id']
        type_ = request.form.get('type') or None
        size = request.form['size']
        material = request.form['material']

        sql = "INSERT INTO product_variants (product_id, type, size, material) VALUES (%s,%s,%s,%s)"
        val = (product_id, type_, size, material)
        cursor.execute(sql, val)
        con.commit()

        flash("Variant Added Successfully!")
        return redirect(url_for('admin_productlist')) 

    return render_template("admin/admin_variant.html", products=products)

@app.route("/admin/admin_variantlist")
def admin_variantlist():
    cursor = con.cursor(pymysql.cursors.DictCursor)

    sql = """
        SELECT pv.id, p.name AS product_name, pv.type, pv.size, pv.material
        FROM product_variants pv
        JOIN products p ON pv.product_id = p.id"""
    cursor.execute(sql)
    variants = cursor.fetchall()
    
    return render_template("admin/admin_variantlist.html", variants=variants)

@app.route("/admin/edit_variant/<int:id>", methods=['GET', 'POST'])
def edit_variant(id):
    cursor = con.cursor(pymysql.cursors.DictCursor)
    
    if request.method == 'POST':
        product_id = request.form['product_id']
        type_ = request.form.get('type') or None
        size = request.form['size']
        material = request.form['material']
        
        sql = "UPDATE product_variants SET product_id=%s, type=%s, size=%s, material=%s WHERE id=%s"
        val = (product_id, type_, size, material, id)
        cursor.execute(sql, val)
        con.commit()
        flash("Variant updated successfully!")
        return redirect(url_for('admin_variantlist'))

    cursor.execute("SELECT * FROM product_variants WHERE id=%s", (id,))
    variant = cursor.fetchone()
    cursor.execute("SELECT id, name FROM products")
    products = cursor.fetchall()
    
    return render_template("admin/admin_editvariant.html", variant=variant, products=products)

@app.route("/admin/delete_variant/<int:id>", methods=['POST'])
def delete_variant(id):
    cursor = con.cursor(pymysql.cursors.DictCursor)

    cursor.execute("DELETE FROM product_variants WHERE id=%s", (id,))
    con.commit()

    flash("Variant deleted successfully!", "success")
    return redirect(url_for('admin_variantlist'))

@app.route("/admin/admin_dimensions", methods=['GET', 'POST'])
def admin_dimensions():
    cursor.execute("SELECT pv.id, p.name, pv.type, pv.size FROM product_variants pv JOIN products p ON pv.product_id=p.id")
    variants = cursor.fetchall()
    
    if request.method == 'POST':
        variant_id = request.form['variant_id']
        dimension = request.form['dimension']
        material = request.form.get('material', None)
        price = request.form['price']     
        weight = request.form['weight'] 

        sql = "INSERT INTO variant_dimensions (variant_id, dimension, material, price, weight) VALUES (%s,%s,%s,%s,%s)"
        val = (variant_id, dimension, material, price, weight)
        cursor.execute(sql, val)
        con.commit()

        flash("Dimension Added Successfully!")
        return redirect('/admin/admin_productlist')

    return render_template("admin/admin_dimensions.html", variants=variants)

@app.route("/admin/admin_dimensionslist")
def admin_dimensionslist():
    cursor = con.cursor(pymysql.cursors.DictCursor)
    sql = """
        SELECT vd.id, pv.type, pv.size, p.name AS product_name,
               vd.dimension, vd.material, vd.price, vd.weight
        FROM variant_dimensions vd
        JOIN product_variants pv ON vd.variant_id = pv.id
        JOIN products p ON pv.product_id = p.id
    """
    cursor.execute(sql)
    dimensions = cursor.fetchall()
    return render_template("admin/admin_dimensionslist.html", dimensions=dimensions)

@app.route("/admin/edit_dimension/<int:id>", methods=['GET', 'POST'])
def edit_dimension(id):
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT vd.*, pv.type, pv.size, p.name AS product_name, pv.product_id
        FROM variant_dimensions vd
        JOIN product_variants pv ON vd.variant_id = pv.id
        JOIN products p ON pv.product_id = p.id
        WHERE vd.id = %s
    """, (id,))
    dimension = cursor.fetchone()
    cursor.execute("SELECT pv.id, p.name, pv.type, pv.size FROM product_variants pv JOIN products p ON pv.product_id=p.id")
    variants = cursor.fetchall()

    if request.method == "POST":
        variant_id = request.form['variant_id']
        dimension_val = request.form['dimension']
        material = request.form.get('material', None)
        price = request.form['price']
        weight = request.form['weight']

        cursor.execute("""
            UPDATE variant_dimensions
            SET variant_id=%s, dimension=%s, material=%s, price=%s, weight=%s
            WHERE id=%s
        """, (variant_id, dimension_val, material, price, weight, id))
        con.commit()
        flash("Dimension updated successfully!", "success")
        return redirect(url_for("admin_dimensionslist"))

    return render_template("admin/admin_editdimensions.html", dimension=dimension, variants=variants)

@app.route("/admin/delete_dimension/<int:id>", methods=['POST'])
def delete_dimension(id):
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("DELETE FROM variant_dimensions WHERE id=%s", (id,))
    con.commit()
    flash("Dimension deleted successfully!", "success")
    return redirect(url_for("admin_dimensionslist"))

@app.route("/admin/orders")
def admin_orders():
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM orders")
    orders = cursor.fetchall()    
    return render_template("admin/admin_orders.html", orders=orders)

@app.route("/admin/order/<int:order_id>")
def admin_order_details(order_id):
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM orders WHERE id=%s", (order_id,))
    order = cursor.fetchone()
    cursor.execute("""
        SELECT oi.*, p.name AS product_name, pv.type, pv.size, vd.dimension
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        JOIN product_variants pv ON oi.variant_id = pv.id
        LEFT JOIN variant_dimensions vd ON oi.dimension_id = vd.id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cursor.fetchall()   
    return render_template("admin/admin_order_details.html", order=order, items=items)

@app.route("/products")
def products():
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM products")
    products = cursor.fetchall()
    return render_template("user/user_product.html", products=products)

@app.route("/product_detail/<int:product_id>")
def product_detail(product_id):
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM products WHERE id=%s", (product_id,))
    product = cursor.fetchone()
    cursor.execute("SELECT * FROM product_variants WHERE product_id=%s", (product_id,))
    variants = cursor.fetchall()
    has_type = any(v['type'] for v in variants)
    return render_template(
        "user/user_productdetails.html",
        product=product,
        variants=variants,
        has_type=has_type
    )

@app.route("/get_sizes/<int:product_id>/<type>")
def get_sizes(product_id, type):
    cursor = con.cursor()
    cursor.execute("SELECT id, size FROM product_variants WHERE product_id=%s AND type=%s", (product_id, type))
    sizes = cursor.fetchall()
    return jsonify(sizes)

@app.route("/get_dimensions/<int:variant_id>")
def get_dimensions(variant_id):
    material = request.args.get('material')
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT id, dimension, price, weight 
        FROM variant_dimensions 
        WHERE variant_id=%s AND material=%s
    """, (variant_id, material))
    dimensions = cursor.fetchall()
    return jsonify(dimensions)

@app.route("/get_price_weight/<int:dimension_id>")
def get_price_weight(dimension_id):
    cursor = con.cursor()
    cursor.execute("SELECT price, weight FROM variant_dimensions WHERE id=%s", (dimension_id,))
    data = cursor.fetchone()
    return jsonify(data)

@app.route("/get_materials/<int:variant_id>")
def get_materials(variant_id):
    cursor = con.cursor()
    cursor.execute("SELECT DISTINCT material FROM variant_dimensions WHERE variant_id=%s AND material IS NOT NULL", (variant_id,))
    materials = cursor.fetchall()
    return jsonify(materials)

@app.route("/user_cart")
def user_cart():
    user_id = session.get("user_id", 0) 
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT c.*, 
               p.name AS product_name, p.image1 AS product_image,
               v.type AS variant_type, v.size AS variant_size,
               d.dimension AS dimension_name
        FROM cart c
        LEFT JOIN products p ON c.product_id = p.id
        LEFT JOIN product_variants v ON c.variant_id = v.id
        LEFT JOIN variant_dimensions d ON c.dimension_id = d.id
        WHERE c.user_id = %s
    """, (user_id,))
    cart_items = cursor.fetchall()

    total = sum(float(item['price']) * int(item['quantity']) for item in cart_items)
    return render_template("user/user_cart.html", cart_items=cart_items, total=total)

@app.route('/remove_from_cart/<int:item_id>', methods=['POST'])
def remove_from_cart(item_id):
    cursor = con.cursor()
    cursor.execute("DELETE FROM cart WHERE id=%s", (item_id,))
    con.commit()    
    flash('Item removed from cart!', 'success')
    return redirect(url_for('user_cart'))  

@app.route("/add_to_cart", methods=["POST"])
def add_to_cart():
    if 'user_id' not in session:
        return jsonify({'status': 'not_logged_in'})
    data = request.get_json()
    product_id = data['product_id']
    variant_id = data['variant_id']
    material = data.get('material', None)
    dimension_id = data['dimension_id']
    price = float(data['price'])
    weight = data.get('weight', None)
    quantity = int(data.get('quantity', 1))
    user_id = session.get("user_id", 0)
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT * FROM cart 
        WHERE user_id=%s AND product_id=%s AND variant_id=%s 
        AND material=%s AND dimension_id=%s
    """, (user_id, product_id, variant_id, material, dimension_id))
    existing_item = cursor.fetchone()

    if existing_item:
        new_quantity = existing_item['quantity'] + quantity
        new_price = float(existing_item['price']) + (price * quantity)
        cursor.execute("""
            UPDATE cart 
            SET quantity=%s, price=%s 
            WHERE id=%s
        """, (new_quantity, new_price, existing_item['id']))
    else:

        cursor.execute("""
            INSERT INTO cart (user_id, product_id, variant_id, material, dimension_id, price, weight, quantity)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (user_id, product_id, variant_id, material, dimension_id, price, weight, quantity))

    con.commit()
    cursor.close()
    return jsonify({"status": "success"})

@app.route('/update_cart', methods=['POST'])
def update_cart():
    item_id = request.form.get('item_id')
    quantity = int(request.form.get('quantity', 1))
    cursor = con.cursor()
    cursor.execute("UPDATE cart SET quantity=%s WHERE id=%s", (quantity, item_id))
    con.commit()
    flash('Cart updated!')
    return redirect(url_for('user_cart'))

@app.route("/checkout")
def checkout():
    user_id = session.get("user_id", 0)
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT c.*, 
               p.name AS product_name,
               v.type AS variant_type, v.size AS variant_size,
               d.dimension AS dimension_name
        FROM cart c
        LEFT JOIN products p ON c.product_id = p.id
        LEFT JOIN product_variants v ON c.variant_id = v.id
        LEFT JOIN variant_dimensions d ON c.dimension_id = d.id
        WHERE c.user_id = %s
    """, (user_id,))
    cart_items = cursor.fetchall()
    total = sum(float(item['price']) * int(item['quantity']) for item in cart_items)
    return render_template("user/user_checkout.html", cart_items=cart_items, total=total)

@app.route("/place_order", methods=["POST"])
def place_order():
    if "user_id" not in session:
        return jsonify({"status": "not_logged_in"})

    data = request.get_json()  # <-- important, JSON data ko parse karna
    name = data.get("name")
    email = data.get("email")
    phone = data.get("phone")
    address = data.get("address")
    user_id = session["user_id"]

    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT * FROM cart WHERE user_id=%s", (user_id,))
    cart_items = cursor.fetchall()
    if not cart_items:
        return jsonify({"status": "empty_cart"})

    total = sum(float(item['price']) * int(item['quantity']) for item in cart_items)

    # Insert into orders table
    cursor.execute("""
        INSERT INTO orders (user_id, name, email, phone, address, total_amount, status)
        VALUES (%s,%s,%s,%s,%s,%s,'Pending')
    """, (user_id, name, email, phone, address, total))
    order_id = cursor.lastrowid

    for item in cart_items:
        cursor.execute("""
            INSERT INTO order_items (order_id, product_id, variant_id, material, dimension_id, price, quantity)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            order_id,
            item['product_id'],
            item['variant_id'],
            item.get('material'),
            item['dimension_id'],
            item['price'],
            item['quantity']
        ))

    # Create Razorpay order
    razorpay_order = client.order.create({
        "amount": int(total * 100),  
        "currency": "INR",
        "receipt": str(order_id),
        "payment_capture": 1
    })
    razorpay_order_id = razorpay_order['id']
    cursor.execute("UPDATE orders SET razorpay_order_id=%s WHERE id=%s", (razorpay_order_id, order_id))
    con.commit()

    return jsonify({
        "status": "created",
        "order_id": order_id,
        "razorpay_order_id": razorpay_order_id,
        "total_amount": total
    })

@app.route("/verify_payment", methods=["POST"])
def verify_payment():
    data = request.get_json()
    razorpay_payment_id = data.get('razorpay_payment_id')
    razorpay_order_id = data.get('razorpay_order_id')
    razorpay_signature = data.get('razorpay_signature')

    params_dict = {
        'razorpay_order_id': razorpay_order_id,
        'razorpay_payment_id': razorpay_payment_id,
        'razorpay_signature': razorpay_signature
    }

    try:
        client.utility.verify_payment_signature(params_dict)
        cursor = con.cursor(pymysql.cursors.DictCursor)
        
        # 1️⃣ Update order status
        cursor.execute(
            "UPDATE orders SET status='Paid', payment_id=%s WHERE razorpay_order_id=%s",
            (razorpay_payment_id, razorpay_order_id)
        )

        # 2️⃣ Empty user cart
        # Pehle order_id se user_id nikal lo
        cursor.execute("SELECT user_id FROM orders WHERE razorpay_order_id=%s", (razorpay_order_id,))
        user = cursor.fetchone()
        if user:
            user_id = user['user_id']
            cursor.execute("DELETE FROM cart WHERE user_id=%s", (user_id,))

        con.commit()
        return jsonify({"status": "success"})
    except Exception as e:
        print("Payment verification failed:", e)
        return jsonify({"status": "failed"})


@app.route("/admin/admin_popup")
def admin_popup():
    return render_template("admin/admin_popup.html")

@app.route('/addpopup', methods=['GET', 'POST'])
def addpopup():
    if request.method == 'POST':
        image = request.files.get('image')

        if image and image.filename != '':
            filename = secure_filename(image.filename)

            upload_folder = os.path.join(app.root_path, 'static/uploads/popup')
            os.makedirs(upload_folder, exist_ok=True)

            image.save(os.path.join(upload_folder, filename))
            cur = con.cursor()
            cur.execute("INSERT INTO popup (image) VALUES (%s)", (filename,))
            con.commit()

            flash("Popup image added successfully!", "success")
            return redirect(url_for('admin_popup'))
        else:
            flash("Please select an image before submitting.", "danger")
            return redirect(url_for('admin_popup'))

    return render_template("admin/admin_popup.html")

@app.route("/admin/admin_popuplist")
def admin_popuplist():
    cur = con.cursor(pymysql.cursors.DictCursor)
    cur.execute("SELECT * FROM popup ORDER BY id DESC")
    popups = cur.fetchall()
    return render_template("admin/admin_popuplist.html", popups=popups)

@app.route("/admin/editpopup/<int:popup_id>", methods=["GET", "POST"])
def editpopup(popup_id):
    cur = con.cursor(pymysql.cursors.DictCursor)
    if request.method == "POST":
        new_image = request.files["image"]
        filename = secure_filename(new_image.filename)
        new_image.save(os.path.join(app.root_path, "static/uploads/popup", filename))
        cur.execute("UPDATE popup SET image=%s WHERE id=%s", (filename, popup_id))
        con.commit()
        return redirect(url_for("admin_popuplist"))

    cur.execute("SELECT * FROM popup WHERE id=%s", (popup_id,))
    popup = cur.fetchone()
    return render_template("admin/admin_editpopup.html", popup=popup)

@app.route("/admin/deletepopup/<int:popup_id>")
def deletepopup(popup_id):
    cur = con.cursor()
    cur.execute("SELECT image FROM popup WHERE id=%s", (popup_id,))
    row = cur.fetchone()
    if row:
        image_file = row[0]
        image_path = os.path.join(app.root_path, "static/uploads/popup", image_file)
        if os.path.exists(image_path):
            os.remove(image_path)
    cur.execute("DELETE FROM popup WHERE id=%s", (popup_id,))
    con.commit()
    return redirect(url_for("admin_popuplist"))
   
@app.route("/admin/admin_blog")
def admin_blog():
    return render_template("admin/admin_blog.html")

@app.route("/admin/addblog", methods=['POST'])
def addblog():
    title = request.form['title']
    description = request.form['description']
    
    image = request.files.get('image')
    image_name = secure_filename(image.filename) if image else None
    
    if image:
        image.save(os.path.join(blogimgpath, image_name))
    
    sql = "INSERT INTO blogs (title, image, description) VALUES (%s, %s, %s)"
    cursor.execute(sql, (title, image_name, description))
    con.commit()
    
    return redirect('/admin/admin_bloglist')

@app.route("/admin/admin_bloglist")
def admin_bloglist():
    cursor = con.cursor(pymysql.cursors.DictCursor) 
    cursor.execute("SELECT * FROM blogs") 
    blogs = cursor.fetchall()
    return render_template("admin/admin_bloglist.html",blogs=blogs)

@app.route("/admin/editblog/<int:id>")
def editblog(id):
    cursor.execute("SELECT * FROM blogs WHERE blog_id = %s",(id,))
    blog = cursor.fetchone()

    if not blog:
        return redirect(url_for('admin_bloglist'))
    
    return render_template("admin/admin_editblog.html",blog=blog)

@app.route("/admin/updateblog/<int:id>", methods=['POST'])
def updateblog(id):
    title = request.form['title']
    description = request.form['description']    
    image = request.files.get('image')

    cursor.execute("SELECT image FROM blogs WHERE blog_id = %s", (id,))
    existing = cursor.fetchone()
    existing_image = existing['image'] if existing else None

    image_name = existing_image

    if image and image.filename != "":
        image_name = secure_filename(image.filename)
        image.save(os.path.join(blogimgpath, image_name))
        if existing_image:
            old_image_path = os.path.join(blogimgpath, existing_image)
            if os.path.exists(old_image_path):
                os.remove(old_image_path)

    cursor.execute(
        "UPDATE blogs SET title=%s, description=%s, image=%s WHERE blog_id=%s",
        (title, description, image_name, id)
    )
    con.commit()
    return redirect(url_for('admin_bloglist'))

@app.route("/admin/deleteblog/<int:id>")
def deleteblog(id):
    sql = "DELETE FROM blogs WHERE blog_id = %s"
    cursor.execute(sql,(id,))
    con.commit()
    return redirect('/admin/admin_bloglist')

@app.route("/admin/admin_size")
def admin_size():
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT product_id,name FROM product ORDER BY product_id DESC")
    products = cursor.fetchall()
    cursor.execute("SELECT type_id,name FROM type ORDER BY type_id DESC")
    types = cursor.fetchall()
    return render_template("admin/admin_size.html", types=types,products=products)

@app.route("/admin/addsize", methods=['GET','POST'])
def addsize():
    cursor = con.cursor(pymysql.cursors.DictCursor)
    if request.method == 'POST':
        product_id = request.form['product_id']
        type_id = request.form['type_id']
        size = request.form['size']
        subsize = request.form['subsize']
        price = request.form['price']
        material = request.form['material']

        image1 = request.files.get('image1')
        image2 = request.files.get('image2')
        image3 = request.files.get('image3')

        image1_name = secure_filename(image1.filename) if image1 else None
        image2_name = secure_filename(image2.filename) if image2 else None
        image3_name = secure_filename(image3.filename) if image3 else None

        if image1:
            image1.save(os.path.join(sizeimgpath, image1_name))
        if image2:
            image2.save(os.path.join(sizeimgpath, image2_name))
        if image3:
            image3.save(os.path.join(sizeimgpath, image3_name))

        sql = """
            INSERT INTO size (product_id, type_id, size, sub_size, price, image1, image2, image3, material)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        val = (product_id, type_id, size, subsize, price, image1_name, image2_name, image3_name, material)
        cursor.execute(sql, val)
        con.commit()
        return redirect('/admin/admin_size')

    cursor.execute("SELECT type_id, name FROM type ORDER BY type_id DESC")
    types = cursor.fetchall()
    cursor.execute("SELECT product_id, name FROM product ORDER BY product_id DESC")
    products = cursor.fetchall()
    return render_template("admin/admin_size.html", types=types, products=products)

@app.route("/admin/admin_sizelist")
def admin_sizelist():
    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("""
        SELECT s.size_id, s.size, s.sub_size, s.price, s.image1, s.image2, s.image3, s.material, t.name AS type_name
        FROM size s
        JOIN type t ON s.type_id = t.type_id
        ORDER BY s.size_id DESC
    """)
    sizes = cursor.fetchall()
    return render_template("admin/admin_sizelist.html", sizes=sizes)

@app.route("/admin/editsize/<int:id>", methods=['GET'])
def editsize(id):
    cursor = con.cursor(pymysql.cursors.DictCursor)
   
    cursor.execute("SELECT * FROM size WHERE size_id=%s", (id,))
    size_data = cursor.fetchone()
    
    if not size_data:
        return redirect(url_for('admin_sizelist'))

    cursor.execute("SELECT type_id, name FROM type ORDER BY name")
    types = cursor.fetchall()

    return render_template("admin/admin_editsize.html", size_data=size_data, types=types)

@app.route("/admin/updatesize/<int:id>", methods=['POST'])
def updatesize(id):
    type_id = request.form['type_id']
    size_name = request.form['size']
    subsize = request.form['subsize']
    price = request.form['price']
    material = request.form['material']

    image1 = request.files.get('image1')
    image2 = request.files.get('image2')
    image3 = request.files.get('image3')

    cursor = con.cursor(pymysql.cursors.DictCursor)
    cursor.execute("SELECT image1, image2, image3 FROM size WHERE size_id=%s", (id,))
    existing_images = cursor.fetchone()  

    def save_image(new_img, old_name):
        if new_img:
            filename = secure_filename(new_img.filename)
            new_img.save(os.path.join(sizeimgpath, filename))
            return filename
        else:
            return old_name

    image1_name = save_image(image1, existing_images['image1'])
    image2_name = save_image(image2, existing_images['image2'])
    image3_name = save_image(image3, existing_images['image3'])

    cursor.execute("""
        UPDATE size 
        SET type_id=%s, size=%s, sub_size=%s, price=%s, image1=%s, image2=%s, image3=%s, material=%s
        WHERE size_id=%s
    """, (type_id, size_name, subsize, price, image1_name, image2_name, image3_name, material, id))
    con.commit()

    return redirect(url_for('admin_sizelist'))

@app.route("/admin/deletesize/<int:id>")
def deletesize(id):
    cursor = con.cursor()
    cursor.execute("DELETE FROM size WHERE size_id=%s", (id,))
    con.commit()
    return redirect(url_for('admin_sizelist'))

@app.route("/")
def user_dashboard():
    cursor = con.cursor(pymysql.cursors.DictCursor)

    cursor.execute("SELECT id, name FROM products ORDER BY id")
    menu_products = cursor.fetchall()

    cursor.execute("SELECT * FROM products WHERE is_new = 1 ORDER BY id DESC")
    new_products = cursor.fetchall()

    cursor.execute("SELECT * FROM products WHERE is_featured = 1 ORDER BY id DESC")
    featured_products = cursor.fetchall()

    cursor.execute("SELECT blog_id, title, image, description FROM blogs ORDER BY blog_id DESC LIMIT 3")
    blogs = cursor.fetchall()

    cursor.execute("SELECT * FROM popup ORDER BY id DESC LIMIT 1")
    popup = cursor.fetchone() 

    return render_template(
        'user/user_dashboard.html',menu_products=menu_products,new_products=new_products,featured_products=featured_products,blogs=blogs,popup=popup)

@app.route("/user/user_faq")
def user_faq():
    return render_template("user/user_faq.html")

@app.route("/user/user_register", methods=['GET', 'POST'])
def user_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form.get('phone')
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        existing_user = cursor.fetchone()
        if existing_user:
            return render_template('user/user_register.html', error="Email already registered")

        hashed_password = generate_password_hash(password)

        cursor.execute(
            "INSERT INTO users (name, email, phone, password) VALUES (%s, %s, %s, %s)",
            (name, email, phone, hashed_password)
        )
        con.commit()

    return render_template('user/user_register.html')

@app.route("/user_login", methods=['GET', 'POST'])
def user_login():
    cursor = con.cursor(pymysql.cursors.DictCursor)
    
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['user_name'] = user['name']
            return redirect(url_for('user_dashboard'))
        else:
            # Agar email ya password galat ho
            return render_template('user/user_login.html', error="Invalid email or password")

    return render_template("user/user_login.html")

@app.route("/user/user_logout")
def user_logout():
    session.pop('user_id', None)
    session.pop('user_name', None)
    return redirect(url_for('user_login'))

@app.route("/user/user_contact", methods=['GET', 'POST'])
def user_contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        
        if not name or not email or not message:
            return render_template("user/user_contact.html", error="Please fill all required fields")

        cursor = con.cursor()
        sql = "INSERT INTO contacts (name, email, phone, message) VALUES (%s, %s, %s, %s)"
        cursor.execute(sql, (name, email, phone, message))
        con.commit()
        cursor.close()

        return render_template("user/user_contact.html", success="Your message has been sent successfully!")

    return render_template("user/user_contact.html")

@app.route("/admin/user_contactlist")
def user_contactlist():
    cursor = con.cursor()
    cursor.execute("SELECT contact_id, name, email, phone, message FROM contacts ORDER BY contact_id DESC")
    contacts = cursor.fetchall()
    cursor.close()
    return render_template("admin/user_contactlist.html", contacts=contacts)

@app.route("/user/user_blog")
def user_blog():
    cursor = con.cursor(pymysql.cursors.DictCursor)  
    cursor.execute("SELECT * FROM blogs ORDER BY blog_id DESC")  
    blogs = cursor.fetchall()
    return render_template("user/user_blog.html", blogs=blogs)

@app.route("/user/user_about")
def user_about():
    return render_template("user/user_about.html")   

if __name__ == "__main__":
    app.run(debug=True)

