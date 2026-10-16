import sqlite3

def setup_accountant_database(db_name="gakuri_dairy.db"):
    # Connect to SQLite database (creates it if it doesn't exist)
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # Enforce foreign key constraints to keep modules connected properly
    cursor.execute("PRAGMA foreign_keys = ON;")

    # =================================================================
    # 1. FOUNDATIONAL MODULES (Required for Accountant Foreign Keys)
    # =================================================================
    
    # Porters Table (Accepts IDs like 'P001')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS porters (
            porter_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            route TEXT,
            status TEXT DEFAULT 'Active',
            payment_method TEXT,
            mpesa_phone TEXT,
            account_name TEXT,
            account_number TEXT
        )
    ''')

    # Customers Table (Accepts IDs like 'C001')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id TEXT PRIMARY KEY,
            full_name TEXT NOT NULL,
            national_id TEXT,
            phone TEXT,
            collection_point TEXT,
            ward TEXT,
            status TEXT DEFAULT 'Active',
            assigned_porter_id TEXT,
            payment_method TEXT,
            FOREIGN KEY (assigned_porter_id) REFERENCES porters(porter_id)
        )
    ''')

    # =================================================================
    # 2. ACCOUNTANT MODULE: SESSION TOTALS & RECONCILIATION
    # =================================================================
    
    # Tracks the overall daily weighbridge performance for each porter
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intake_sessions (
            session_id INTEGER PRIMARY KEY AUTOINCREMENT,
            porter_id TEXT NOT NULL,
            collection_date DATE NOT NULL,
            station_weighed REAL NOT NULL,
            variance REAL NOT NULL,
            status TEXT NOT NULL,  -- 'GAIN', 'LOSS', or 'BALANCED'
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (porter_id) REFERENCES porters(porter_id)
        )
    ''')

    # =================================================================
    # 3. ACCOUNTANT MODULE: INDIVIDUAL CUSTOMER INTAKES
    # =================================================================
    
    # Tracks the specific morning/afternoon split for payouts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS intake_records (
            record_id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            porter_id TEXT NOT NULL,
            cust_id TEXT NOT NULL,
            collection_date DATE NOT NULL,
            morning_vol REAL DEFAULT 0.0,
            afternoon_vol REAL DEFAULT 0.0,
            total_day REAL DEFAULT 0.0,
            FOREIGN KEY (session_id) REFERENCES intake_sessions(session_id) ON DELETE CASCADE,
            FOREIGN KEY (porter_id) REFERENCES porters(porter_id),
            FOREIGN KEY (cust_id) REFERENCES customers(id)
        )
    ''')

    # =================================================================
    # 4. ACCOUNTANT MODULE: AUDIT LOGS
    # =================================================================
    
    # Security tracking for the Accountant module
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accountant_audit_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user TEXT DEFAULT 'Admin',
            action TEXT NOT NULL,
            details TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()
    print("Accountant Module Database schema initialized cleanly.")

if __name__ == '__main__':
    setup_accountant_database()