<<<<<<< HEAD
# AuthFlow - Client Intake, Company Formation & Master Excel Portal

A full-stack web application designed for **Client Raw Data Intake**, **Master Excel Generation**, and **New Company Formation & Required Forms Intake** with **Authentication** built with **Python (Flask)**, **openpyxl**, **SQLite**, and **Glassmorphism UI**.

---

## 🌟 Modules & Features

### 🏢 1. New Company Formation & Required Forms Intake (`/company-formation`)
Designed specifically for clients who want to open a new company and submit required statutory forms.

- **Part 1: Company Profile Particulars**:
  - Proposed Company Name
  - Business Entity Type (*Private Limited Company, LLC, Corporation, Partnership, Sole Proprietorship*)
  - Industry Sector (*Tech, Finance, Retail, Healthcare, Manufacturing, etc.*)
  - Registered Business Address
  - Contact Person, Official Email, Phone Number

- **Part 2: Upload Required Forms (Sample Slots)**:
  *Currently configured with sample required forms — ready to update with your exact form names anytime:*
  1. **Form 1: Articles of Incorporation / Founding Charter** *(Required)*
  2. **Form 2: Directors & Officers Identity Proof** *(Required - Passport / National ID / Utility Bill)*
  3. **Form 3: Business Name Reservation & Consent Declaration** *(Required)*
  4. **Form 4: Registered Office Proof & Address Verification** *(Optional / Supporting)*
  5. **Form 5: Initial Tax Identification Application (TIN / GST / EIN)** *(Optional / Supporting)*
  6. **Custom Slot: Additional Supporting Documents** *(Custom title upload)*

- **Admin Review & Approval Modal**:
  - Side-by-side inspection of company profile details.
  - One-click view/download of all attached forms.
  - Status updates: `Under Review`, `Approved`, `Needs Revision` with reviewer feedback notes.
- **Export Companies Register (`.xlsx`)**:
  - 1-Click Excel export of all company applications and documents count.

---

### 📂 2. Raw Data Intake & Master Formatted Excel (`/dashboard`)
Designed for raw accounting inputs (receipts, bills, raw `.xlsx` / `.csv` sheets):
- **Raw Upload Dropzone**: Drag-and-drop raw receipts pictures and raw spreadsheets.
- **Inspect & Format Modal**: High-res picture preview or raw sheet table preview on the left; structured data entry form on the right.
- **Master Excel Generator**: Produces professionally styled `.xlsx` workbooks with `=SUM()` formulas and currency formats.

---

### 🔐 3. Authentication & Security
- **Registration** with live 4-level **Password Strength Meter**.
- **Login** with username or email, "Remember me" session persistence.
- **Password Recovery** with expiring tokens and on-screen demo simulator.
- **Dark & Light Mode** toggle with persistent storage.
- **Role Switcher**: Seamlessly switch between Client View and Admin View in 1 click.

---

## 🏃 Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Flask web application
python app.py
```

Open in your web browser: **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 📁 Project Structure

```text
d:\vamsi anna new project\
├── app.py                 # Flask routes, form config & controllers
├── database.py            # SQLite schema (users, submissions, master_records, company_applications, company_documents)
├── excel_generator.py     # openpyxl styling engine for accounting and companies registers
├── requirements.txt       # Dependencies
├── README.md              # Documentation
├── uploads/               # Secure file store for uploaded forms and receipts
├── static/
│   ├── css/
│   │   └── style.css      # Glassmorphism, dropzone, forms upload cards & modals
│   └── js/
│       └── main.js        # Theme toggle, password meter & validation
└── templates/
    ├── base.html          # Navigation header with portal links
    ├── login.html         # User sign-in
    ├── register.html      # User registration
    ├── forgot_password.html # Password recovery
    ├── reset_password.html  # Set new password
    ├── dashboard.html     # Raw Data Intake & Accounting Excel Register
    └── company_formation.html # New Company Formation & Required Forms Wizard
```
=======
# authflow
A modern Flask authentication web application featuring login, registration, password reset, and a responsive glassmorphic UI.
>>>>>>> d29997c088ec93e398ea4173e87e506a45ac8094
