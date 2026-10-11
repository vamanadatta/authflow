import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash, 
    session, send_from_directory, send_file, jsonify
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import database as db
import excel_generator

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "super-secret-dev-key-7f9a2b4e8c1d")

# Upload configurations
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if os.environ.get("VERCEL"):
    UPLOAD_FOLDER = "/tmp/uploads"
else:
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024  # 32 MB max

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'xlsx', 'xls', 'csv', 'pdf', 'txt', 'docx'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_file_type(filename):
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    if ext in ['png', 'jpg', 'jpeg', 'gif', 'webp']:
        return 'image'
    elif ext in ['xlsx', 'xls']:
        return 'excel'
    elif ext == 'csv':
        return 'csv'
    elif ext == 'pdf':
        return 'pdf'
    return 'other'

# Ensure database is initialized
db.init_db()

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

# --- Authentication Routes ---

@app.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "client")

        if not full_name or not username or not email or not password:
            flash("Please fill in all required fields.", "danger")
            return render_template("register.html", full_name=full_name, username=username, email=email)

        if len(username) < 3:
            flash("Username must be at least 3 characters long.", "danger")
            return render_template("register.html", full_name=full_name, username=username, email=email)

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("register.html", full_name=full_name, username=username, email=email)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("register.html", full_name=full_name, username=username, email=email)

        if db.get_user_by_identifier(username):
            flash("Username is already taken. Please choose another.", "danger")
            return render_template("register.html", full_name=full_name, username=username, email=email)

        if db.get_user_by_email(email):
            flash("An account with this email already exists.", "danger")
            return render_template("register.html", full_name=full_name, username=username, email=email)

        password_hash = generate_password_hash(password)
        user_id = db.create_user(full_name, username, email, password_hash, role=role)

        if user_id:
            session["user_id"] = user_id
            session["user_name"] = full_name
            session["username"] = username
            session["user_email"] = email
            session["role"] = role
            flash("Account created successfully! Welcome to AuthFlow.", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Could not create account. Please try again.", "danger")

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip()
        password = request.form.get("password", "")
        remember_me = request.form.get("remember_me")

        if not identifier or not password:
            flash("Please enter both username/email and password.", "danger")
            return render_template("login.html", identifier=identifier)

        user = db.get_user_by_identifier(identifier)
        if user and check_password_hash(user["password_hash"], password):
            session.permanent = bool(remember_me)
            session["user_id"] = user["id"]
            session["user_name"] = user["full_name"]
            session["username"] = user["username"]
            session["user_email"] = user["email"]
            session["role"] = user["role"] if "role" in user.keys() else "admin"
            flash(f"Welcome back, {user['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid username/email or password.", "danger")
            return render_template("login.html", identifier=identifier)

    return render_template("login.html")

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    reset_link = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()

        if not email:
            flash("Please enter your registered email address.", "danger")
            return render_template("forgot_password.html")

        user = db.get_user_by_email(email)
        if user:
            token = secrets.token_urlsafe(32)
            expiry = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
            db.set_reset_token(user["id"], token, expiry)
            reset_link = url_for("reset_password", token=token, _external=True)
            flash("Password reset link generated! In production this is sent via email.", "info")
        else:
            flash("If an account exists with this email, a reset link will be sent.", "info")

    return render_template("forgot_password.html", reset_link=reset_link)

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if "user_id" in session:
        return redirect(url_for("dashboard"))

    user = db.get_user_by_reset_token(token)
    if not user:
        flash("Password reset link is invalid or has expired.", "danger")
        return redirect(url_for("forgot_password"))

    if request.method == "POST":
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "danger")
            return render_template("reset_password.html", token=token)

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("reset_password.html", token=token)

        new_password_hash = generate_password_hash(password)
        db.update_password(user["id"], new_password_hash)
        flash("Password reset successfully! You can now log in with your new password.", "success")
        return redirect(url_for("login"))

    return render_template("reset_password.html", token=token, user_email=user["email"])

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("login"))

@app.route("/toggle-role")
@login_required
def toggle_role():
    current_role = session.get("role", "client")
    new_role = "admin" if current_role == "client" else "client"
    session["role"] = new_role
    flash(f"Switched view mode to: {new_role.upper()}", "info")
    return redirect(url_for("dashboard"))

# --- Dashboard & Core Data Flow Routes ---

@app.route("/dashboard")
@login_required
def dashboard():
    user = db.get_user_by_id(session["user_id"])
    role = session.get("role", "admin")  # Default to admin for convenient management
    
    # Submissions
    submissions = db.get_submissions(user_id=None if role == "admin" else session["user_id"])
    
    # Master records (formatted Excel records)
    master_records = db.get_master_records()
    
    # Stats
    stats = db.get_summary_stats()
    
    return render_template(
        "dashboard.html",
        user=user,
        role=role,
        submissions=submissions,
        master_records=master_records,
        stats=stats
    )

@app.route("/upload", methods=["POST"])
@login_required
def upload_file():
    if "file" not in request.files:
        flash("No file part in the upload request.", "danger")
        return redirect(url_for("dashboard"))

    file = request.files["file"]
    if file.filename == "":
        flash("Please select a file to upload.", "danger")
        return redirect(url_for("dashboard"))

    if not allowed_file(file.filename):
        flash("File format not supported. Allowed: Excel (.xlsx, .xls, .csv), Images (.jpg, .png, .webp), PDF, Docs.", "danger")
        return redirect(url_for("dashboard"))

    title = request.form.get("title", "").strip() or file.filename
    category = request.form.get("category", "Invoices")
    notes = request.form.get("notes", "").strip()

    # Create safe unique filename
    original_filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    stored_filename = f"{timestamp}_{secrets.token_hex(4)}_{original_filename}"
    file_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)

    file.save(file_path)
    file_size = os.path.getsize(file_path)
    file_type = get_file_type(original_filename)

    db.create_submission(
        user_id=session["user_id"],
        title=title,
        category=category,
        notes=notes,
        file_path=stored_filename,
        original_filename=original_filename,
        file_type=file_type,
        file_size=file_size
    )

    flash(f"Raw data file '{original_filename}' uploaded successfully! It is queued for Excel formatting.", "success")
    return redirect(url_for("dashboard"))

@app.route("/uploads/<filename>")
@login_required
def serve_upload(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/submission/<int:submission_id>")
@login_required
def get_submission_detail(submission_id):
    sub = db.get_submission_by_id(submission_id)
    if not sub:
        return jsonify({"error": "Submission not found"}), 404

    preview_data = None
    if sub["file_type"] in ["excel", "csv"]:
        full_path = os.path.join(app.config["UPLOAD_FOLDER"], sub["file_path"])
        preview_data = excel_generator.parse_raw_file_preview(full_path)

    return jsonify({
        "id": sub["id"],
        "title": sub["title"],
        "category": sub["category"],
        "notes": sub["notes"],
        "client_name": sub["client_name"],
        "original_filename": sub["original_filename"],
        "file_type": sub["file_type"],
        "file_url": url_for("serve_upload", filename=sub["file_path"]),
        "status": sub["status"],
        "created_at": sub["created_at"],
        "preview_data": preview_data
    })

@app.route("/submission/<int:submission_id>/status", methods=["POST"])
@login_required
def update_status(submission_id):
    status = request.form.get("status", "Pending")
    db.update_submission_status(submission_id, status)
    flash(f"Submission #{submission_id} status updated to {status}.", "info")
    return redirect(url_for("dashboard"))

@app.route("/submission/<int:submission_id>/delete", methods=["POST"])
@login_required
def delete_submission(submission_id):
    sub = db.get_submission_by_id(submission_id)
    if sub:
        try:
            full_path = os.path.join(app.config["UPLOAD_FOLDER"], sub["file_path"])
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception:
            pass
        db.delete_submission(submission_id)
        flash("Submission deleted successfully.", "info")
    return redirect(url_for("dashboard"))

# --- Master Record Formatted Data Routes ---

@app.route("/master-record/add", methods=["POST"])
@login_required
def add_master_record():
    entry_date = request.form.get("entry_date", datetime.now().strftime("%Y-%m-%d"))
    vendor_client = request.form.get("vendor_client", "").strip()
    invoice_no = request.form.get("invoice_no", "").strip()
    description = request.form.get("description", "").strip()
    category = request.form.get("category", "General")
    subtotal = float(request.form.get("subtotal", 0.0) or 0.0)
    tax_amount = float(request.form.get("tax_amount", 0.0) or 0.0)
    total_amount = float(request.form.get("total_amount", 0.0) or (subtotal + tax_amount))
    payment_status = request.form.get("payment_status", "Paid")
    submission_id = request.form.get("submission_id") or None

    if submission_id:
        try:
            submission_id = int(submission_id)
        except ValueError:
            submission_id = None

    if not vendor_client or not description:
        flash("Vendor/Client and Description are required to record formatted data.", "danger")
        return redirect(url_for("dashboard"))

    record_id = db.create_master_record(
        submission_id=submission_id,
        entry_date=entry_date,
        vendor_client=vendor_client,
        invoice_no=invoice_no,
        description=description,
        category=category,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total_amount=total_amount,
        payment_status=payment_status,
        created_by_user_id=session["user_id"]
    )

    flash(f"Record #{record_id} successfully added to Master Excel Sheet!", "success")
    return redirect(url_for("dashboard"))

@app.route("/master-record/<int:record_id>/delete", methods=["POST"])
@login_required
def delete_record(record_id):
    db.delete_master_record(record_id)
    flash(f"Record #{record_id} removed from Master Sheet.", "info")
    return redirect(url_for("dashboard"))

@app.route("/export-excel")
@login_required
def export_excel():
    records = db.get_master_records()
    excel_stream = excel_generator.generate_formatted_excel(records)
    filename = f"Master_Accounting_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    
    return send_file(
        excel_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

# --- Sample Required Forms Configuration ---
SAMPLE_REQUIRED_FORMS = [
    {
        "key": "form_charter",
        "title": "Form 1: Articles of Incorporation / Founding Charter",
        "description": "Founding document specifying legal company name, purpose, share capital, and board regulations.",
        "required": True,
        "badge": "Required Form"
    },
    {
        "key": "form_directors_id",
        "title": "Form 2: Directors & Officers Identity Proof",
        "description": "Government Photo ID (Passport / National ID / Drivers License) and Address Proof for company directors.",
        "required": True,
        "badge": "Required Form"
    },
    {
        "key": "form_name_approval",
        "title": "Form 3: Business Name Reservation & Consent Declaration",
        "description": "Official company name availability clearance, trade registry consent, and founder sign-off.",
        "required": True,
        "badge": "Required Form"
    },
    {
        "key": "form_registered_office",
        "title": "Form 4: Registered Office Proof & Address Verification",
        "description": "Lease agreement, commercial deed, or utility bill for the registered business address.",
        "required": False,
        "badge": "Optional / Supporting"
    },
    {
        "key": "form_tax_declaration",
        "title": "Form 5: Initial Tax Identification Application (TIN / GST / EIN)",
        "description": "Initial revenue authority tax registration declaration and bank opening authorization.",
        "required": False,
        "badge": "Optional / Supporting"
    }
]

# --- Company Registration / Formation Routes ---

@app.route("/company-formation")
@login_required
def company_formation():
    user = db.get_user_by_id(session["user_id"])
    role = session.get("role", "admin")
    
    # Get applications
    applications = db.get_company_applications(user_id=None if role == "admin" else session["user_id"])
    stats = db.get_company_stats()

    return render_template(
        "company_formation.html",
        user=user,
        role=role,
        applications=applications,
        stats=stats,
        required_forms=SAMPLE_REQUIRED_FORMS
    )

@app.route("/company-formation/submit", methods=["POST"])
@login_required
def submit_company_formation():
    company_name = request.form.get("company_name", "").strip()
    business_type = request.form.get("business_type", "Private Limited / LLC").strip()
    industry = request.form.get("industry", "General").strip()
    registered_address = request.form.get("registered_address", "").strip()
    contact_person = request.form.get("contact_person", "").strip() or session.get("user_name", "")
    contact_email = request.form.get("contact_email", "").strip() or session.get("user_email", "")
    contact_phone = request.form.get("contact_phone", "").strip()

    if not company_name or not business_type:
        flash("Company Name and Business Structure are required.", "danger")
        return redirect(url_for("company_formation"))

    # Create company application record
    app_id = db.create_company_application(
        user_id=session["user_id"],
        company_name=company_name,
        business_type=business_type,
        industry=industry,
        registered_address=registered_address,
        contact_person=contact_person,
        contact_email=contact_email,
        contact_phone=contact_phone
    )

    # Process uploaded sample required forms
    uploaded_count = 0
    for form_meta in SAMPLE_REQUIRED_FORMS:
        file = request.files.get(form_meta["key"])
        if file and file.filename:
            if allowed_file(file.filename):
                original_filename = secure_filename(file.filename)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                stored_filename = f"comp_{app_id}_{form_meta['key']}_{timestamp}_{original_filename}"
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
                
                file.save(file_path)
                file_size = os.path.getsize(file_path)
                
                db.add_company_document(
                    application_id=app_id,
                    form_key=form_meta["key"],
                    form_title=form_meta["title"],
                    file_path=stored_filename,
                    original_filename=original_filename,
                    file_size=file_size
                )
                uploaded_count += 1

    # Check for custom extra file
    custom_file = request.files.get("custom_file")
    if custom_file and custom_file.filename and allowed_file(custom_file.filename):
        custom_title = request.form.get("custom_title", "").strip() or "Custom Form Attachment"
        original_filename = secure_filename(custom_file.filename)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        stored_filename = f"comp_{app_id}_custom_{timestamp}_{original_filename}"
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], stored_filename)
        
        custom_file.save(file_path)
        file_size = os.path.getsize(file_path)
        
        db.add_company_document(
            application_id=app_id,
            form_key="custom_form",
            form_title=custom_title,
            file_path=stored_filename,
            original_filename=original_filename,
            file_size=file_size
        )
        uploaded_count += 1

    flash(f"Application for '{company_name}' submitted successfully with {uploaded_count} uploaded required forms!", "success")
    return redirect(url_for("company_formation"))

@app.route("/company-formation/<int:app_id>")
@login_required
def get_company_detail(app_id):
    app_data = db.get_company_application_by_id(app_id)
    if not app_data:
        return jsonify({"error": "Application not found"}), 404

    docs = db.get_company_documents(app_id)
    docs_list = []
    for d in docs:
        docs_list.append({
            "id": d["id"],
            "form_key": d["form_key"],
            "form_title": d["form_title"],
            "original_filename": d["original_filename"],
            "file_size": d["file_size"],
            "uploaded_at": d["uploaded_at"],
            "file_url": url_for("serve_upload", filename=d["file_path"])
        })

    return jsonify({
        "id": app_data["id"],
        "company_name": app_data["company_name"],
        "business_type": app_data["business_type"],
        "industry": app_data["industry"],
        "registered_address": app_data["registered_address"],
        "contact_person": app_data["contact_person"],
        "contact_email": app_data["contact_email"],
        "contact_phone": app_data["contact_phone"],
        "status": app_data["status"],
        "admin_notes": app_data["admin_notes"],
        "created_at": app_data["created_at"],
        "documents": docs_list
    })

@app.route("/company-formation/<int:app_id>/status", methods=["POST"])
@login_required
def update_company_status(app_id):
    status = request.form.get("status", "Under Review")
    admin_notes = request.form.get("admin_notes", "")
    db.update_company_application_status(app_id, status, admin_notes)
    flash(f"Application #{app_id} status updated to '{status}'.", "info")
    return redirect(url_for("company_formation"))

@app.route("/company-formation/<int:app_id>/delete", methods=["POST"])
@login_required
def delete_company(app_id):
    docs = db.get_company_documents(app_id)
    for d in docs:
        try:
            full_path = os.path.join(app.config["UPLOAD_FOLDER"], d["file_path"])
            if os.path.exists(full_path):
                os.remove(full_path)
        except Exception:
            pass
    db.delete_company_application(app_id)
    flash("Company application removed.", "info")
    return redirect(url_for("company_formation"))

@app.route("/company-formation/export-excel")
@login_required
def export_companies_excel():
    companies = db.get_company_applications()
    excel_stream = excel_generator.generate_companies_excel(companies)
    filename = f"Company_Registrations_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    
    return send_file(
        excel_stream,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=filename
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)

