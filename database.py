import sqlite3
import os
from datetime import datetime, timezone

if os.environ.get("VERCEL"):
    DB_PATH = "/tmp/app.db"
else:
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        cursor = conn.cursor()
        # Users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'client',
                reset_token TEXT,
                reset_token_expiry TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add role column if upgrading existing database
        cursor.execute("PRAGMA table_info(users)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "role" not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'client'")

        # Raw Submissions table (Client uploads)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                category TEXT DEFAULT 'Invoices',
                notes TEXT,
                file_path TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_type TEXT DEFAULT 'other',
                file_size INTEGER DEFAULT 0,
                status TEXT DEFAULT 'Pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Formatted Master Accounting / Expense Records
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS master_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER,
                entry_date TEXT NOT NULL,
                vendor_client TEXT NOT NULL,
                invoice_no TEXT,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                subtotal REAL NOT NULL DEFAULT 0.0,
                tax_amount REAL NOT NULL DEFAULT 0.0,
                total_amount REAL NOT NULL DEFAULT 0.0,
                payment_status TEXT NOT NULL DEFAULT 'Paid',
                created_by_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (submission_id) REFERENCES submissions(id),
                FOREIGN KEY (created_by_user_id) REFERENCES users(id)
            )
        """)

        # New Company Registration Applications
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                company_name TEXT NOT NULL,
                business_type TEXT NOT NULL,
                industry TEXT,
                registered_address TEXT,
                contact_person TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                status TEXT DEFAULT 'Under Review',
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)

        # Uploaded Required Forms for Company Registration
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS company_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                application_id INTEGER NOT NULL,
                form_key TEXT NOT NULL,
                form_title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                original_filename TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (application_id) REFERENCES company_applications(id)
            )
        """)
        conn.commit()

# --- User Functions ---

def create_user(full_name, username, email, password_hash, role='client'):
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (full_name, username, email, password_hash, role) VALUES (?, ?, ?, ?, ?)",
                (full_name.strip(), username.strip().lower(), email.strip().lower(), password_hash, role)
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None

def get_user_by_identifier(identifier):
    clean_id = identifier.strip().lower()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE LOWER(username) = ? OR LOWER(email) = ?",
            (clean_id, clean_id)
        )
        return cursor.fetchone()

def get_user_by_id(user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return cursor.fetchone()

def get_user_by_email(email):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email.strip().lower(),))
        return cursor.fetchone()

def set_reset_token(user_id, token, expiry_iso):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?",
            (token, expiry_iso, user_id)
        )
        conn.commit()

def get_user_by_reset_token(token):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE reset_token = ?", (token,))
        user = cursor.fetchone()
        if not user:
            return None
        
        expiry_str = user["reset_token_expiry"]
        if expiry_str:
            try:
                expiry_time = datetime.fromisoformat(expiry_str)
                now = datetime.now(timezone.utc)
                if expiry_time.tzinfo is None:
                    expiry_time = expiry_time.replace(tzinfo=timezone.utc)
                if now > expiry_time:
                    return None
            except ValueError:
                return None
        return user

def update_password(user_id, new_password_hash):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE users SET password_hash = ?, reset_token = NULL, reset_token_expiry = NULL WHERE id = ?",
            (new_password_hash, user_id)
        )
        conn.commit()

# --- Submissions Functions ---

def create_submission(user_id, title, category, notes, file_path, original_filename, file_type, file_size):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO submissions (user_id, title, category, notes, file_path, original_filename, file_type, file_size, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Pending')
        """, (user_id, title.strip(), category, notes.strip() if notes else "", file_path, original_filename, file_type, file_size))
        conn.commit()
        return cursor.lastrowid

def get_submissions(user_id=None):
    with get_db() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT s.*, COALESCE(u.full_name, 'Client') as client_name, COALESCE(u.email, '') as client_email
                FROM submissions s
                LEFT JOIN users u ON s.user_id = u.id
                WHERE s.user_id = ?
                ORDER BY s.created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT s.*, COALESCE(u.full_name, 'Client') as client_name, COALESCE(u.email, '') as client_email
                FROM submissions s
                LEFT JOIN users u ON s.user_id = u.id
                ORDER BY s.created_at DESC
            """)
        return cursor.fetchall()

def get_submission_by_id(submission_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT s.*, COALESCE(u.full_name, 'Client') as client_name, COALESCE(u.email, '') as client_email
            FROM submissions s
            LEFT JOIN users u ON s.user_id = u.id
            WHERE s.id = ?
        """, (submission_id,))
        return cursor.fetchone()

def update_submission_status(submission_id, status):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE submissions SET status = ? WHERE id = ?", (status, submission_id))
        conn.commit()

def delete_submission(submission_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
        conn.commit()

# --- Formatted Master Records Functions ---

def create_master_record(submission_id, entry_date, vendor_client, invoice_no, description, category, subtotal, tax_amount, total_amount, payment_status, created_by_user_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO master_records 
            (submission_id, entry_date, vendor_client, invoice_no, description, category, subtotal, tax_amount, total_amount, payment_status, created_by_user_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (submission_id, entry_date, vendor_client.strip(), invoice_no.strip() if invoice_no else "", description.strip(), category, float(subtotal), float(tax_amount), float(total_amount), payment_status, created_by_user_id))
        
        # Mark linked submission as Completed
        if submission_id:
            cursor.execute("UPDATE submissions SET status = 'Completed' WHERE id = ?", (submission_id,))
        
        conn.commit()
        return cursor.lastrowid

def get_master_records():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.*, s.original_filename, s.file_type, s.file_path, u.full_name as creator_name
            FROM master_records m
            LEFT JOIN submissions s ON m.submission_id = s.id
            LEFT JOIN users u ON m.created_by_user_id = u.id
            ORDER BY m.entry_date DESC, m.id DESC
        """)
        return cursor.fetchall()

def get_master_record_by_id(record_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM master_records WHERE id = ?", (record_id,))
        return cursor.fetchone()

def update_master_record(record_id, entry_date, vendor_client, invoice_no, description, category, subtotal, tax_amount, total_amount, payment_status):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE master_records
            SET entry_date = ?, vendor_client = ?, invoice_no = ?, description = ?, category = ?, subtotal = ?, tax_amount = ?, total_amount = ?, payment_status = ?
            WHERE id = ?
        """, (entry_date, vendor_client.strip(), invoice_no.strip() if invoice_no else "", description.strip(), category, float(subtotal), float(tax_amount), float(total_amount), payment_status, record_id))
        conn.commit()

def delete_master_record(record_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM master_records WHERE id = ?", (record_id,))
        conn.commit()

def get_summary_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM submissions")
        total_submissions = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count FROM submissions WHERE status = 'Pending'")
        pending_submissions = cursor.fetchone()["count"]

        cursor.execute("SELECT COUNT(*) as count, COALESCE(SUM(total_amount), 0) as total_val, COALESCE(SUM(tax_amount), 0) as total_tax FROM master_records")
        row = cursor.fetchone()
        total_records = row["count"]
        total_expenditure = row["total_val"]
        total_tax = row["total_tax"]

        return {
            "total_submissions": total_submissions,
            "pending_submissions": pending_submissions,
            "total_records": total_records,
            "total_expenditure": round(total_expenditure, 2),
            "total_tax": round(total_tax, 2)
        }

# --- Company Registration Functions ---

def create_company_application(user_id, company_name, business_type, industry, registered_address, contact_person, contact_email, contact_phone):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO company_applications 
            (user_id, company_name, business_type, industry, registered_address, contact_person, contact_email, contact_phone, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Under Review')
        """, (user_id, company_name.strip(), business_type.strip(), industry.strip(), registered_address.strip(), contact_person.strip(), contact_email.strip(), contact_phone.strip()))
        conn.commit()
        return cursor.lastrowid

def add_company_document(application_id, form_key, form_title, file_path, original_filename, file_size):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO company_documents (application_id, form_key, form_title, file_path, original_filename, file_size)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (application_id, form_key, form_title, file_path, original_filename, file_size))
        conn.commit()
        return cursor.lastrowid

def get_company_applications(user_id=None):
    with get_db() as conn:
        cursor = conn.cursor()
        if user_id:
            cursor.execute("""
                SELECT c.*, COALESCE(u.full_name, 'Client') as applicant_name, COALESCE(u.email, '') as applicant_email,
                       (SELECT COUNT(*) FROM company_documents d WHERE d.application_id = c.id) as doc_count
                FROM company_applications c
                LEFT JOIN users u ON c.user_id = u.id
                WHERE c.user_id = ?
                ORDER BY c.created_at DESC
            """, (user_id,))
        else:
            cursor.execute("""
                SELECT c.*, COALESCE(u.full_name, 'Client') as applicant_name, COALESCE(u.email, '') as applicant_email,
                       (SELECT COUNT(*) FROM company_documents d WHERE d.application_id = c.id) as doc_count
                FROM company_applications c
                LEFT JOIN users u ON c.user_id = u.id
                ORDER BY c.created_at DESC
            """)
        return cursor.fetchall()

def get_company_application_by_id(app_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT c.*, COALESCE(u.full_name, 'Client') as applicant_name, COALESCE(u.email, '') as applicant_email
            FROM company_applications c
            LEFT JOIN users u ON c.user_id = u.id
            WHERE c.id = ?
        """, (app_id,))
        return cursor.fetchone()

def get_company_documents(application_id):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM company_documents 
            WHERE application_id = ? 
            ORDER BY id ASC
        """, (application_id,))
        return cursor.fetchall()

def update_company_application_status(app_id, status, admin_notes=""):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE company_applications 
            SET status = ?, admin_notes = ? 
            WHERE id = ?
        """, (status, admin_notes.strip() if admin_notes else "", app_id))
        conn.commit()

def delete_company_application(app_id):
    with get_db() as conn:
        cursor = conn.cursor()
        # Delete documents
        cursor.execute("DELETE FROM company_documents WHERE application_id = ?", (app_id,))
        cursor.execute("DELETE FROM company_applications WHERE id = ?", (app_id,))
        conn.commit()

def get_company_stats():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM company_applications")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT COUNT(*) as pending FROM company_applications WHERE status = 'Under Review'")
        pending = cursor.fetchone()["pending"]

        cursor.execute("SELECT COUNT(*) as approved FROM company_applications WHERE status = 'Approved'")
        approved = cursor.fetchone()["approved"]

        cursor.execute("SELECT COUNT(*) as total_docs FROM company_documents")
        total_docs = cursor.fetchone()["total_docs"]

        return {
            "total_companies": total,
            "pending_review": pending,
            "approved_companies": approved,
            "total_documents": total_docs
        }

