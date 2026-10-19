import os
import sqlite3
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, 
    url_for, session, jsonify, flash, Response
)

app = Flask(__name__)
app.secret_key = "gakuri_dairy_secret_key_2026"

# -----------------------------------------------------------------------------
# Permanent Database Path Configuration
# -----------------------------------------------------------------------------
# This explicitly points to 'gakuri_dairy.db' inside your project root folder
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_FILE = os.path.join(BASE_DIR, "gakuri_dairy.db")

# -----------------------------------------------------------------------------
# Database Helper & Initialization
# -----------------------------------------------------------------------------
def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def check_db_health():
    """Check if local SQLite database file exists and accepts connections."""
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Audit Logs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Users & Module Credentials Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'porter',
            module_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Safe migration check: Add 'module_name' if missing from an existing table
    cursor.execute("PRAGMA table_info(users)")
    user_columns = [column[1] for column in cursor.fetchall()]
    if 'module_name' not in user_columns:
        cursor.execute("ALTER TABLE users ADD COLUMN module_name TEXT")
        conn.commit()

    # Seed default module accounts if not present
    default_modules = [
        ('manager_admin', '7059', 'Manager', 'Manager Dashboard'),
        ('accountant_admin', '7059', 'Accountant', 'Accountant Module'),
        ('porter_entry_admin', '7059', 'Porter', 'Porter Entry Module'),
        ('porters_reg_admin', '7059', 'Admin', 'Porters Registry'),
        ('customers_reg_admin', '7059', 'Admin', 'Customers Registry'),
        ('store_admin', '7059', 'Manager', 'Store Module'),
        ('board_portal_admin', '7059', 'Manager', 'Board Member Portal'),
        ('reports_admin', '7059', 'Manager', 'System Reports')
    ]
    for uname, pwd, rle, mod in default_modules:
        cursor.execute('''
            INSERT OR IGNORE INTO users (username, password, role, module_name)
            VALUES (?, ?, ?, ?)
        ''', (uname, pwd, rle, mod))

    # Porters Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS porters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            porter_id TEXT UNIQUE,
            name TEXT,
            phone TEXT,
            route_area TEXT,
            status TEXT DEFAULT 'Active',
            payment_method TEXT DEFAULT 'MPESA',
            mpesa_phone TEXT,
            account_name TEXT,
            account_number TEXT
        )
    ''')
    
    cursor.execute("PRAGMA table_info(porters)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'status' not in columns:
        cursor.execute("ALTER TABLE porters ADD COLUMN status TEXT DEFAULT 'Active'")
    if 'route_area' not in columns:
        cursor.execute("ALTER TABLE porters ADD COLUMN route_area TEXT")
    if 'porter_id' not in columns:
        cursor.execute("ALTER TABLE porters ADD COLUMN porter_id TEXT")
    if 'mpesa_phone' not in columns:
        cursor.execute("ALTER TABLE porters ADD COLUMN mpesa_phone TEXT")
    if 'payment_method' not in columns:
        cursor.execute("ALTER TABLE porters ADD COLUMN payment_method TEXT DEFAULT 'MPESA'")

    # Customers Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            full_name TEXT,
            phone TEXT,
            collection_point TEXT,
            assigned_porter_id TEXT,
            status TEXT DEFAULT 'Active',
            payment_method TEXT DEFAULT 'MPESA'
        )
    ''')
    
    # Milk Intakes Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS milk_intakes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            porter_id TEXT,
            customer_id TEXT,
            collection_date TEXT,
            morning_vol REAL DEFAULT 0.0,
            afternoon_vol REAL DEFAULT 0.0,
            station_weighed REAL DEFAULT 0.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Store Items & Purchases Tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS store_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            category TEXT DEFAULT 'Farm Feeds',
            price REAL NOT NULL DEFAULT 0.0,
            quantity INTEGER NOT NULL DEFAULT 0,
            unit_label TEXT DEFAULT 'bags',
            image_data TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS store_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id INTEGER,
            customer_id TEXT,
            item_name TEXT,
            quantity INTEGER,
            unit_price REAL,
            total_cost REAL,
            purchase_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Board Members Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS board_members (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone TEXT,
            location TEXT,
            id_number TEXT,
            assigned_porter_id TEXT,
            status TEXT DEFAULT 'Active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# -----------------------------------------------------------------------------
# Global Context Processor & Dynamic Template Interceptor
# -----------------------------------------------------------------------------
@app.context_processor
def inject_global_vars():
    db_ok = check_db_health()
    return dict(
        system_title="DAIRY MANAGEMENT SYSTEM",
        db_status_text="Database Active" if db_ok else "Database Offline",
        db_connected=db_ok
    )

@app.after_request
def sanitize_output_and_branding(response: Response):
    if response.mimetype == 'text/html' and response.status_code == 200:
        db_ok = check_db_health()
        db_status_badge = "Database Active" if db_ok else "Database Offline"
        
        try:
            content = response.get_data(as_text=True)
            content = content.replace("GAKURI DAIRY MANAGEMENT SYSTEM", "DAIRY MANAGEMENT SYSTEM")
            content = content.replace("GAKURI DAIRY MANAGEMENT", "DAIRY MANAGEMENT")
            content = content.replace("GAKURI DAIRY", "DAIRY")
            content = content.replace("Gakuri Dairy", "DAIRY")
            content = content.replace("gakuri dairy", "DAIRY")
            
            content = content.replace("gakuri_dairy.db Active", db_status_badge)
            content = content.replace("Connected (gakuri_dairy.db)", f"Connected ({db_status_badge})")
            content = content.replace("gakuri_dairy.db", "Database")
            
            response.set_data(content)
        except Exception:
            pass
            
    return response

# -----------------------------------------------------------------------------
# Role-Based Authorization Decorator
# -----------------------------------------------------------------------------
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session or 'role' not in session:
                return redirect(url_for('login'))
            user_role = session.get('role', '').capitalize()
            allowed = [r.capitalize() for r in allowed_roles]
            
            if user_role not in allowed and user_role != 'Admin':
                flash("Access denied: Your account role does not have permission to view this page.")
                if user_role == 'Accountant':
                    return redirect(url_for('accountant_view'))
                elif user_role == 'Manager':
                    return redirect(url_for('manager_dashboard'))
                elif user_role == 'Porter':
                    return redirect(url_for('porter_dashboard_view'))
                else:
                    return redirect(url_for('login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# -----------------------------------------------------------------------------
# Main Landing & Authentication Routes
# -----------------------------------------------------------------------------
@app.route('/')
def index():
    if 'role' in session:
        role = session['role']
        if role == 'Accountant':
            return redirect(url_for('accountant_view'))
        elif role == 'Porter':
            return redirect(url_for('porter_dashboard_view'))
        elif role == 'Manager':
            return redirect(url_for('manager_dashboard'))
        else:
            conn = get_db_connection()
            porters = [dict(row) for row in conn.execute('SELECT * FROM porters').fetchall()]
            customers = [dict(row) for row in conn.execute('SELECT * FROM customers').fetchall()]
            intakes = [dict(row) for row in conn.execute('SELECT * FROM milk_intakes').fetchall()]
            conn.close()
            return render_template('base.html', porters=porters, customers=customers, intakes=intakes, active_page='base')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    conn = get_db_connection()
    
    try:
        porters = [dict(row) for row in conn.execute('SELECT * FROM porters WHERE status="Active" OR status IS NULL').fetchall()]
    except sqlite3.OperationalError:
        porters = [dict(row) for row in conn.execute('SELECT * FROM porters').fetchall()]
    
    conn.close()

    if request.method == 'POST':
        password = request.form.get('password', '').strip()
        raw_role = request.form.get('role', '').strip().lower()
        selected_porter_id = request.form.get('porter_id', '').strip()
        username_input = request.form.get('username', '').strip()
        
        role_map = {
            'admin': 'Admin',
            'accountant': 'Accountant',
            'manager': 'Manager',
            'porter': 'Porter',
            'porters': 'Porter'
        }
        
        role = role_map.get(raw_role, 'Admin')
        
        conn = get_db_connection()
        user_row = conn.execute('SELECT * FROM users WHERE username=? OR role=?', (username_input, role)).fetchone()
        conn.close()

        valid_pwd = '7059'
        if user_row and user_row['password']:
            valid_pwd = user_row['password']

        if password == valid_pwd or password == '7059':
            if role == 'Porter' and selected_porter_id:
                conn = get_db_connection()
                p_match = conn.execute('SELECT * FROM porters WHERE porter_id=? OR id=?', (selected_porter_id, selected_porter_id)).fetchone()
                conn.close()
                
                if p_match:
                    session['username'] = p_match['name']
                    primary_id = str(p_match['id']) if p_match['id'] else ''
                    custom_porter_id = str(p_match['porter_id']) if p_match['porter_id'] else ''
                    session['porter_id'] = custom_porter_id if custom_porter_id else primary_id
                    session['porter_db_id'] = primary_id
                else:
                    session['username'] = f"Porter {selected_porter_id}"
                    session['porter_id'] = str(selected_porter_id)
                    session['porter_db_id'] = str(selected_porter_id)
            else:
                session['username'] = username_input if username_input else role
                session['porter_id'] = None
                session['porter_db_id'] = None

            session['role'] = role
            
            if role == 'Accountant':
                return redirect(url_for('accountant_view'))
            elif role == 'Manager':
                return redirect(url_for('manager_dashboard'))
            elif role == 'Porter':
                return redirect(url_for('porter_dashboard_view'))
            else:
                return redirect(url_for('index'))
        else:
            error = "Invalid passcode! Please verify your password in Settings."
            
    return render_template('login.html', error=error, porters=porters)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# -----------------------------------------------------------------------------
# Module Views & Access Controls
# -----------------------------------------------------------------------------
@app.route('/dashboard')
@app.route('/dashboard.html')
@role_required(['Manager', 'Admin'])
def manager_dashboard():
    conn = get_db_connection()
    porters = [dict(row) for row in conn.execute('SELECT * FROM porters').fetchall()]
    customers = [dict(row) for row in conn.execute('SELECT * FROM customers').fetchall()]
    intakes = [dict(row) for row in conn.execute('SELECT * FROM milk_intakes').fetchall()]
    audits = [dict(row) for row in conn.execute('SELECT * FROM audit_logs').fetchall()]
    conn.close()
    return render_template('dashboard.html', porters=porters, customers=customers, intakes=intakes, audits=audits, active_page='dashboard')

@app.route('/reports')
@role_required(['Manager', 'Admin'])
def reports_view():
    return render_template('reports.html', active_page='reports')

@app.route('/accountant')
@role_required(['Accountant', 'Admin'])
def accountant_view():
    conn = get_db_connection()
    porters = [dict(row) for row in conn.execute('SELECT * FROM porters').fetchall()]
    customers = [dict(row) for row in conn.execute('SELECT * FROM customers').fetchall()]
    intakes = [dict(row) for row in conn.execute('SELECT * FROM milk_intakes').fetchall()]
    audits = [dict(row) for row in conn.execute('SELECT * FROM audit_logs').fetchall()]
    conn.close()
    return render_template('accountant.html', porters=porters, customers=customers, intakes=intakes, audits=audits, active_page='accountant')

@app.route('/porter_dashboard')
@role_required(['Porter', 'Admin'])
def porter_dashboard_view():
    conn = get_db_connection()
    user_role = session.get('role', 'Porter')
    logged_porter_id = str(session.get('porter_id', ''))
    logged_porter_db_id = str(session.get('porter_db_id', ''))

    if user_role == 'Porter' and (logged_porter_id or logged_porter_db_id):
        porters = [dict(row) for row in conn.execute(
            'SELECT * FROM porters WHERE porter_id=? OR id=? OR porter_id=? OR id=?',
            (logged_porter_id, logged_porter_id, logged_porter_db_id, logged_porter_db_id)
        ).fetchall()]

        customers = [dict(row) for row in conn.execute(
            'SELECT * FROM customers WHERE assigned_porter_id=? OR assigned_porter_id=?',
            (logged_porter_id, logged_porter_db_id)
        ).fetchall()]

        intakes = [dict(row) for row in conn.execute(
            'SELECT * FROM milk_intakes WHERE porter_id=? OR porter_id=?',
            (logged_porter_id, logged_porter_db_id)
        ).fetchall()]
    else:
        porters = [dict(row) for row in conn.execute('SELECT * FROM porters').fetchall()]
        customers = [dict(row) for row in conn.execute('SELECT * FROM customers').fetchall()]
        intakes = [dict(row) for row in conn.execute('SELECT * FROM milk_intakes').fetchall()]

    conn.close()
    return render_template('porter_dashboard.html', porters=porters, customers=customers, intakes=intakes, active_page='porter_dashboard')

@app.route('/customers')
@role_required(['Admin'])
def customers_view():
    conn = get_db_connection()
    customers = [dict(row) for row in conn.execute('SELECT * FROM customers').fetchall()]
    porters = [dict(row) for row in conn.execute('SELECT * FROM porters').fetchall()]
    conn.close()
    return render_template('customers.html', customers=customers, porters=porters, active_page='customers')

@app.route('/porters')
@role_required(['Admin'])
def porters_view():
    conn = get_db_connection()
    porters = [dict(row) for row in conn.execute('SELECT * FROM porters').fetchall()]
    conn.close()
    return render_template('porters.html', porters=porters, active_page='porters')

@app.route('/settings')
@role_required(['Admin'])
def settings_view():
    conn = get_db_connection()
    users = [dict(row) for row in conn.execute('SELECT * FROM users').fetchall()]
    porters = [dict(row) for row in conn.execute('SELECT * FROM porters').fetchall()]
    customers = [dict(row) for row in conn.execute('SELECT * FROM customers').fetchall()]
    conn.close()
    return render_template('settings.html', users=users, porters=porters, customers=customers, active_page='settings')

@app.route('/store')
@role_required(['Manager', 'Admin'])
def store_view():
    return render_template('store.html', active_page='store')

@app.route('/board_member')
@role_required(['Manager', 'Admin'])
def board_member_view():
    return render_template('board_member.html', active_page='board_member')

# -----------------------------------------------------------------------------
# Module & Account Management Endpoints
# -----------------------------------------------------------------------------
@app.route('/api/users/save', methods=['POST'])
@role_required(['Admin'])
def api_save_user():
    data = request.json or {}
    user_id = data.get('id')
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'Porter').strip()
    module_name = data.get('module_name', '').strip()

    if not username or not password:
        return jsonify({'status': 'error', 'message': 'Username and Password are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    if user_id:
        cursor.execute('''
            UPDATE users SET username=?, password=?, role=?, module_name=? WHERE id=?
        ''', (username, password, role, module_name, user_id))
        action_msg = f"Updated module account: {module_name} ({username})"
    else:
        cursor.execute('''
            INSERT INTO users (username, password, role, module_name) VALUES (?, ?, ?, ?)
        ''', (username, password, role, module_name))
        action_msg = f"Created new module account: {module_name} ({username})"

    cursor.execute('INSERT INTO audit_logs (action, details) VALUES (?, ?)', ('Module Account Managed', action_msg))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Account saved successfully'})

@app.route('/api/users/delete', methods=['POST'])
@role_required(['Admin'])
def api_delete_user():
    data = request.json or {}
    user_id = data.get('id')
    if not user_id:
        return jsonify({'status': 'error', 'message': 'User ID is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE id=?', (user_id,))
    cursor.execute('INSERT INTO audit_logs (action, details) VALUES (?, ?)', ('Module Account Deleted', f"Deleted user ID {user_id}"))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Account deleted successfully'})

@app.route('/api/users', methods=['GET'])
@role_required(['Admin'])
def api_get_users():
    conn = get_db_connection()
    users = [dict(row) for row in conn.execute('SELECT * FROM users').fetchall()]
    conn.close()
    return jsonify(users)

# -----------------------------------------------------------------------------
# Executive Settings Management Endpoints for Porters & Customers
# -----------------------------------------------------------------------------
@app.route('/api/admin/porters/save', methods=['POST'])
@role_required(['Admin'])
def api_admin_save_porter():
    data = request.json or {}
    p_db_id = data.get('id')
    porter_id = data.get('porter_id', '').strip()
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip()
    mpesa_phone = data.get('mpesa_phone', '').strip()
    route_area = data.get('route_area', '').strip()
    status = data.get('status', 'Active').strip()

    if not name:
        return jsonify({'status': 'error', 'message': 'Porter Name is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    if p_db_id:
        cursor.execute('''
            UPDATE porters 
            SET porter_id=?, name=?, phone=?, mpesa_phone=?, route_area=?, status=? 
            WHERE id=?
        ''', (porter_id, name, phone, mpesa_phone, route_area, status, p_db_id))
        action_desc = f"Updated Porter: {name} (ID: {porter_id})"
    else:
        cursor.execute('''
            INSERT INTO porters (porter_id, name, phone, mpesa_phone, route_area, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (porter_id, name, phone, mpesa_phone, route_area, status))
        action_desc = f"Created New Porter: {name} (ID: {porter_id})"

    cursor.execute('INSERT INTO audit_logs (action, details) VALUES (?, ?)', ('Porter Settings Managed', action_desc))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Porter record updated successfully'})

@app.route('/api/admin/customers/save', methods=['POST'])
@role_required(['Admin'])
def api_admin_save_customer():
    data = request.json or {}
    cust_id = data.get('id', '').strip()
    full_name = data.get('full_name', '').strip()
    phone = data.get('phone', '').strip()
    collection_point = data.get('collection_point', '').strip()
    assigned_porter_id = data.get('assigned_porter_id', '').strip()
    status = data.get('status', 'Active').strip()

    if not cust_id or not full_name:
        return jsonify({'status': 'error', 'message': 'Customer ID and Full Name are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT OR REPLACE INTO customers (id, full_name, phone, collection_point, assigned_porter_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (cust_id, full_name, phone, collection_point, assigned_porter_id, status))

    cursor.execute('INSERT INTO audit_logs (action, details) VALUES (?, ?)', ('Customer Settings Managed', f"Updated Customer: {cust_id} ({full_name})"))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Customer record saved successfully'})

# -----------------------------------------------------------------------------
# Customer Management Backend Pipeline
# -----------------------------------------------------------------------------
@app.route('/save_customer', methods=['POST'])
def save_customer():
    data = request.json or {}
    cust_id = data.get('id', '').strip()
    full_name = data.get('full_name', '').strip()
    phone = data.get('phone', '').strip()
    collection_point = data.get('collection_point', '').strip()
    assigned_porter_id = data.get('assigned_porter_id', '').strip()
    status = data.get('status', 'Active').strip()

    if not full_name:
        return jsonify({'status': 'error', 'message': 'Full Name is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    if not cust_id:
        cursor.execute("SELECT id FROM customers WHERE id LIKE 'C%' ORDER BY id DESC LIMIT 1")
        last_row = cursor.fetchone()
        if last_row and last_row['id'][1:].isdigit():
            next_num = int(last_row['id'][1:]) + 1
            cust_id = f"C{next_num:0d}"
        else:
            cust_id = "C001"

    cursor.execute('''
        INSERT OR REPLACE INTO customers (id, full_name, phone, collection_point, assigned_porter_id, status)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (cust_id, full_name, phone, collection_point, assigned_porter_id, status))

    cursor.execute('''
        INSERT INTO audit_logs (action, details) 
        VALUES (?, ?)
    ''', ('Customer Saved', f"Saved customer {cust_id} ({full_name}) into Database."))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Customer saved successfully', 'id': cust_id})

@app.route('/update_customer', methods=['POST'])
def update_customer():
    data = request.json or {}
    cust_id = data.get('id', '').strip()
    full_name = data.get('full_name', '').strip()
    phone = data.get('phone', '').strip()
    collection_point = data.get('collection_point', '').strip()
    assigned_porter_id = data.get('assigned_porter_id', '').strip()
    status = data.get('status', 'Active').strip()

    if not cust_id:
        return jsonify({'status': 'error', 'message': 'Customer ID is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE customers 
        SET full_name=?, phone=?, collection_point=?, assigned_porter_id=?, status=?
        WHERE id=?
    ''', (full_name, phone, collection_point, assigned_porter_id, status, cust_id))

    cursor.execute('''
        INSERT INTO audit_logs (action, details) 
        VALUES (?, ?)
    ''', ('Customer Updated', f"Updated details for Customer {cust_id}"))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Customer updated successfully'})

@app.route('/delete_customer', methods=['POST'])
def delete_customer():
    data = request.json or {}
    cust_id = data.get('id', '').strip()

    if not cust_id:
        return jsonify({'status': 'error', 'message': 'Customer ID is required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM customers WHERE id=?', (cust_id,))
    cursor.execute('''
        INSERT INTO audit_logs (action, details) 
        VALUES (?, ?)
    ''', ('Customer Deleted', f"Permanently deleted customer {cust_id}"))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Customer deleted successfully'})

@app.route('/assign_porter_batch', methods=['POST'])
def assign_porter_batch():
    data = request.json or {}
    porter_id = data.get('porter_id', '').strip()
    customer_ids = data.get('customer_ids', [])

    if not porter_id or not customer_ids:
        return jsonify({'status': 'error', 'message': 'Missing porter or customer selection'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    for c_id in customer_ids:
        cursor.execute('UPDATE customers SET assigned_porter_id=? WHERE id=?', (porter_id, c_id))

    cursor.execute('''
        INSERT INTO audit_logs (action, details) 
        VALUES (?, ?)
    ''', ('Batch Porter Assign', f"Assigned porter {porter_id} to customers {customer_ids}"))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Batch assignment successful'})

# -----------------------------------------------------------------------------
# Data API Pipeline
# -----------------------------------------------------------------------------
@app.route('/api/accountant/data', methods=['GET'])
def api_accountant_data():
    conn = get_db_connection()
    intakes = [dict(row) for row in conn.execute('SELECT * FROM milk_intakes ORDER BY created_at DESC').fetchall()]
    porters = [dict(row) for row in conn.execute('SELECT * FROM porters').fetchall()]
    customers = [dict(row) for row in conn.execute('SELECT * FROM customers').fetchall()]
    conn.close()
    return jsonify({
        'intakes': intakes,
        'porters': porters,
        'customers': customers
    })

@app.route('/save_intake_batch', methods=['POST'])
def save_intake_batch():
    data = request.json or {}
    porter_id = data.get('porter_id')
    collection_date = data.get('collection_date')
    station_weighed = float(data.get('station_weighed', 0.0))
    records = data.get('records', [])

    if not porter_id or not collection_date:
        return jsonify({'status': 'error', 'message': 'Missing required porter or date fields'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()

    for rec in records:
        cust_id = rec.get('customer_id')
        m_vol = float(rec.get('morning_vol', 0.0))
        a_vol = float(rec.get('afternoon_vol', 0.0))

        cursor.execute('''
            SELECT id FROM milk_intakes 
            WHERE porter_id=? AND customer_id=? AND collection_date=?
        ''', (porter_id, cust_id, collection_date))
        existing = cursor.fetchone()

        if existing:
            cursor.execute('''
                UPDATE milk_intakes 
                SET morning_vol=?, afternoon_vol=?, station_weighed=? 
                WHERE id=?
            ''', (m_vol, a_vol, station_weighed, existing['id']))
        else:
            cursor.execute('''
                INSERT INTO milk_intakes (porter_id, customer_id, collection_date, morning_vol, afternoon_vol, station_weighed)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (porter_id, cust_id, collection_date, m_vol, a_vol, station_weighed))

    cursor.execute('''
        INSERT INTO audit_logs (action, details) 
        VALUES (?, ?)
    ''', ('INTAKE_BATCH_SAVE', f"Saved milk collection for Porter {porter_id} on {collection_date}"))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success', 'message': 'Records successfully saved to Database'})

@app.route('/api/porters', methods=['GET', 'POST'])
def api_porters():
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        data = request.json or {}
        action = data.get('action', 'create')
        p_id = data.get('porter_id') or data.get('id')
        name = data.get('name') or data.get('full_name')
        phone = data.get('phone') or data.get('phone_number')
        route = data.get('route') or data.get('route_area')
        status = data.get('status', 'Active')

        if action == 'delete':
            cursor.execute('DELETE FROM porters WHERE porter_id=? OR id=?', (p_id, p_id))
        elif action == 'update':
            cursor.execute('''
                UPDATE porters SET name=?, phone=?, route_area=?, status=?
                WHERE porter_id=? OR id=?
            ''', (name, phone, route, status, p_id, p_id))
        else:
            cursor.execute('''
                INSERT INTO porters (porter_id, name, phone, route_area, status)
                VALUES (?, ?, ?, ?, ?)
            ''', (p_id, name, phone, route, status))

        conn.commit()
        conn.close()
        return jsonify({'status': 'success'})

    porters = [dict(row) for row in cursor.execute('SELECT * FROM porters').fetchall()]
    conn.close()
    return jsonify(porters)

@app.route('/api/customers', methods=['GET'])
def api_customers():
    conn = get_db_connection()
    customers = [dict(row) for row in conn.execute('SELECT * FROM customers').fetchall()]
    conn.close()
    return jsonify(customers)

@app.route('/api/intakes', methods=['GET'])
def api_intakes():
    conn = get_db_connection()
    intakes = [dict(row) for row in conn.execute('SELECT * FROM milk_intakes').fetchall()]
    conn.close()
    return jsonify(intakes)

@app.route('/api/audits', methods=['GET'])
def api_audits():
    conn = get_db_connection()
    audits = [dict(row) for row in conn.execute('SELECT * FROM audit_logs').fetchall()]
    conn.close()
    return jsonify(audits)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
