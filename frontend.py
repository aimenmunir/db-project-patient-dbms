import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime, date
import re
import hashlib
import json
from tkcalendar import DateEntry  # pip install tkcalendar


class ClinicDatabase:
    """Handles all database operations with your exact schema (SQLite)"""

    def __init__(self, db_path="clinic.db"):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()
        self.insert_sample_data()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript('''
        CREATE TABLE IF NOT EXISTS Users (
            UserID INTEGER PRIMARY KEY AUTOINCREMENT,
            Username TEXT NOT NULL UNIQUE,
            PasswordHash TEXT NOT NULL,
            FirstName TEXT NOT NULL,
            LastName TEXT NOT NULL,
            Email TEXT NOT NULL UNIQUE,
            PhoneNumber TEXT,
            Role TEXT NOT NULL CHECK (Role IN ('Admin', 'Doctor', 'Nurse', 'Receptionist')),
            IsActive INTEGER NOT NULL DEFAULT 1,
            CreatedDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS Specializations (
            SpecializationID INTEGER PRIMARY KEY AUTOINCREMENT,
            Name TEXT NOT NULL,
            Description TEXT,
            IsActive INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS Departments (
            DepartmentID INTEGER PRIMARY KEY AUTOINCREMENT,
            DepartmentName TEXT NOT NULL,
            Description TEXT,
            Location TEXT,
            ExtensionNumber TEXT,
            IsActive INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS Doctors (
            DoctorID INTEGER PRIMARY KEY AUTOINCREMENT,
            UserID INTEGER NOT NULL UNIQUE,
            SpecializationID INTEGER NOT NULL,
            DepartmentID INTEGER,
            LicenseNumber TEXT NOT NULL UNIQUE,
            YearsOfExperience INTEGER,
            IsActive INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (UserID) REFERENCES Users(UserID),
            FOREIGN KEY (SpecializationID) REFERENCES Specializations(SpecializationID),
            FOREIGN KEY (DepartmentID) REFERENCES Departments(DepartmentID),
            CHECK (YearsOfExperience >= 0)
        );

        CREATE TABLE IF NOT EXISTS Patients (
            PatientID INTEGER PRIMARY KEY AUTOINCREMENT,
            PatientCode TEXT UNIQUE,
            FirstName TEXT NOT NULL,
            LastName TEXT NOT NULL,
            DateOfBirth DATE NOT NULL,
            Gender TEXT NOT NULL CHECK (Gender IN ('Male', 'Female', 'Other')),
            BloodGroup TEXT CHECK (BloodGroup IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') OR BloodGroup IS NULL),
            PhoneNumber TEXT,
            Email TEXT CHECK (Email IS NULL OR Email LIKE '%@%.%'),
            Address TEXT,
            EmergencyContactName TEXT,
            EmergencyContactPhone TEXT,
            IsActive INTEGER NOT NULL DEFAULT 1,
            CreatedDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            ModifiedDate DATETIME
        );

        CREATE TABLE IF NOT EXISTS AppointmentStatuses (
            StatusID INTEGER PRIMARY KEY AUTOINCREMENT,
            StatusName TEXT NOT NULL,
            Description TEXT
        );

        CREATE TABLE IF NOT EXISTS Appointments (
            AppointmentID INTEGER PRIMARY KEY AUTOINCREMENT,
            PatientID INTEGER NOT NULL,
            DoctorID INTEGER NOT NULL,
            AppointmentDate DATE NOT NULL,
            AppointmentTime TEXT NOT NULL,
            StatusID INTEGER NOT NULL,
            Notes TEXT,
            CreatedDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (PatientID) REFERENCES Patients(PatientID),
            FOREIGN KEY (DoctorID) REFERENCES Doctors(DoctorID),
            FOREIGN KEY (StatusID) REFERENCES AppointmentStatuses(StatusID),
            UNIQUE (DoctorID, AppointmentDate, AppointmentTime)
        );

        CREATE TABLE IF NOT EXISTS Bills (
            BillID INTEGER PRIMARY KEY AUTOINCREMENT,
            AppointmentID INTEGER,
            AdmissionID INTEGER,
            BillDate DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            TotalAmount DECIMAL(10,2) NOT NULL,
            PaymentStatus TEXT NOT NULL DEFAULT 'Unpaid',
            PaymentMethod TEXT,
            PaidAmount DECIMAL(10,2) DEFAULT 0.00,
            CreatedBy INTEGER,
            FOREIGN KEY (AppointmentID) REFERENCES Appointments(AppointmentID),
            FOREIGN KEY (AdmissionID) REFERENCES Admissions(AdmissionID),
            FOREIGN KEY (CreatedBy) REFERENCES Users(UserID),
            CHECK (PaymentStatus IN ('Unpaid', 'PartiallyPaid', 'Paid'))
        );

        CREATE TABLE IF NOT EXISTS BillItems (
            BillItemID INTEGER PRIMARY KEY AUTOINCREMENT,
            BillID INTEGER NOT NULL,
            ServiceType TEXT NOT NULL,
            Description TEXT NOT NULL,
            Quantity INTEGER NOT NULL DEFAULT 1,
            UnitPrice DECIMAL(10,2) NOT NULL,
            MedicineID INTEGER,
            TestID INTEGER,
            FOREIGN KEY (BillID) REFERENCES Bills(BillID),
            FOREIGN KEY (MedicineID) REFERENCES Medicines(MedicineID),
            FOREIGN KEY (TestID) REFERENCES MedicalTests(TestID),
            CHECK (Quantity > 0),
            CHECK (UnitPrice >= 0)
        );

        CREATE TABLE IF NOT EXISTS MedicalTests (
            TestID INTEGER PRIMARY KEY AUTOINCREMENT,
            TestCode TEXT NOT NULL UNIQUE,
            TestName TEXT NOT NULL,
            DepartmentID INTEGER,
            Cost DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            NormalRangeMin REAL,
            NormalRangeMax REAL,
            Unit TEXT,
            PreparationInstructions TEXT,
            EstimatedDuration INTEGER,
            IsActive INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (DepartmentID) REFERENCES Departments(DepartmentID),
            CHECK (Cost >= 0)
        );

        -- For brevity, some tables (e.g., Rooms, Admissions, Inventory, ActivityLog) are not included here
        -- but can be added similarly if needed.

        CREATE TRIGGER IF NOT EXISTS trg_GeneratePatientCode
        AFTER INSERT ON Patients
        BEGIN
            UPDATE Patients 
            SET PatientCode = 'PAT-' || substr('0000' || NEW.PatientID, -4, 4) 
            WHERE PatientID = NEW.PatientID;
        END;
        ''')
        self.conn.commit()

    def insert_sample_data(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Users")
        if cursor.fetchone()[0] > 0:
            return

        # Insert users
        cursor.executemany('''
        INSERT INTO Users (Username, PasswordHash, FirstName, LastName, Email, PhoneNumber, Role)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', [
            ('admin', self.hash_password('admin123'), 'System', 'Admin', 'admin@hospital.com', '1234567890', 'Admin'),
            ('aimenmnr', self.hash_password('am2476'), 'Aimen', 'Munir', 'aimenmunir001@gmail.com', '1234567891',
             'Doctor'),
            ('faryaln', self.hash_password('f047-nb'), 'faryal', 'nayyar', 'faryal123@gmail.com', '1234567892', 'Nurse')
        ])

        # Insert specializations
        cursor.executemany('''
        INSERT INTO Specializations (Name, Description)
        VALUES (?, ?)
        ''', [
            ('Cardiology', 'Heart and cardiovascular system'),
            ('Neurology', 'Brain and nervous system'),
            ('General Practice', 'Primary care physician')
        ])

        # Insert departments
        cursor.executemany('''
        INSERT INTO Departments (DepartmentName, Description, Location)
        VALUES (?, ?, ?)
        ''', [
            ('Cardiology', 'Heart care unit', 'Building A, Floor 2'),
            ('Emergency', 'Emergency services', 'Building A, Floor 1'),
            ('Pharmacy', 'Medication dispensing', 'Building B, Floor 1')
        ])

        # Insert appointment statuses
        cursor.executemany('''
        INSERT INTO AppointmentStatuses (StatusName, Description)
        VALUES (?, ?)
        ''', [
            ('Scheduled', 'Appointment is booked'),
            ('Completed', 'Appointment was completed'),
            ('Cancelled', 'Appointment was cancelled'),
            ('No Show', 'Patient did not arrive')
        ])

        # Insert doctors (after users and specializations exist)
        cursor.executemany('''
        INSERT INTO Doctors (UserID, SpecializationID, DepartmentID, LicenseNumber, YearsOfExperience)
        VALUES (?, ?, ?, ?, ?)
        ''', [
            (2, 1, 1, 'MD12345', 5)  # Dr. Aimen Munir
        ])

        # Insert medicine categories
        cursor.executemany('''
        INSERT INTO MedicineCategories (CategoryName, Description)
        VALUES (?, ?)
        ''', [
            ('Antibiotics', 'Medications that fight bacterial infections'),
            ('Analgesics', 'Pain relieving medications'),
            ('Antipyretics', 'Fever reducing medications'),
            ('Antihistamines', 'Allergy medications')
        ])

        self.conn.commit()
    @staticmethod
    def hash_password(password):
        """Simple password hashing (use bcrypt in production)"""
        return hashlib.sha256(password.encode()).hexdigest()

    def export_data(self, filename):
        """Export data to JSON file for backup/transfer"""
        data = {}
        cursor = self.conn.cursor()
        tables = ['Users', 'Patients', 'Doctors', 'Appointments', 'Bills', 'BillItems', 'MedicalTests']
        for table in tables:
            cursor.execute(f"SELECT * FROM {table}")
            data[table] = cursor.fetchall()
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)

    def import_data(self, filename):
        """Import data from JSON file"""
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            cursor = self.conn.cursor()
            for table, rows in data.items():
                cursor.execute(f"DELETE FROM {table}")
                for row in rows:
                    columns = ', '.join([col for col in row.keys() if col != 'rowid'])
                    placeholders = ', '.join(['?'] * len(row))
                    cursor.execute(f"INSERT INTO {table} ({columns}) VALUES ({placeholders})", tuple(row.values()))
            self.conn.commit()
            return True
        except Exception as e:
            messagebox.showerror("Error", f"Failed to import data: {str(e)}")
            return False


class LoginFrame(ttk.Frame):
    """Secure login screen"""

    def __init__(self, parent, db, on_login_success):
        super().__init__(parent, padding="20")
        self.db = db
        self.on_login_success = on_login_success

        ttk.Label(self, text="Clinic Management System", font=('Helvetica', 16)).grid(row=0, column=0, columnspan=2,
                                                                                      pady=10)

        ttk.Label(self, text="Username:").grid(row=1, column=0, sticky="w", pady=5)
        self.username = ttk.Entry(self)
        self.username.grid(row=1, column=1, pady=5)

        ttk.Label(self, text="Password:").grid(row=2, column=0, sticky="w", pady=5)
        self.password = ttk.Entry(self, show="*")
        self.password.grid(row=2, column=1, pady=5)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Login", command=self.authenticate).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Exit", command=parent.quit).pack(side="left", padx=5)

        self.password.bind('<Return>', lambda e: self.authenticate())

    def authenticate(self):
        username = self.username.get()
        password = self.password.get()

        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT UserID, PasswordHash, Role FROM Users 
        WHERE Username = ? AND IsActive = 1
        ''', (username,))

        result = cursor.fetchone()
        if result and result[1] == self.db.hash_password(password):
            self.on_login_success(result[0], result[2])  # user_id, role
        else:
            messagebox.showerror("Error", "Invalid credentials")


class MainApplication(tk.Tk):
    """Main clinic management application"""

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.user_id = None
        self.user_role = None

        self.title("Clinic Management System")
        self.geometry("1200x800")
        self.state('zoomed')

        self.style = ttk.Style()
        self.style.configure('TFrame', background='#f0f0f0')
        self.style.configure('TButton', padding=5)
        self.style.configure('Header.TLabel', font=('Helvetica', 14, 'bold'))

        self.show_login()

    def show_login(self):
        for widget in self.winfo_children():
            widget.destroy()
        LoginFrame(self, self.db, self.on_login_success).pack(expand=True)

    def on_login_success(self, user_id, role):
        self.user_id = user_id
        self.user_role = role
        self.show_main_interface()

    def show_main_interface(self):
        for widget in self.winfo_children():
            widget.destroy()

        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True)

        sidebar = ttk.Frame(main_container, width=200)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        ttk.Label(sidebar, text="Clinic CMS", style='Header.TLabel').pack(pady=20)
        ttk.Label(sidebar, text=f"Logged in as:\n{self.user_role}").pack(pady=10)
        ttk.Separator(sidebar).pack(fill="x", pady=10)

        nav_buttons = [
            ("Dashboard", self.show_dashboard),
            ("Patients", self.show_patient_management),
            ("Appointments", self.show_appointment_management),
            ("Doctors", self.show_doctor_management),
            ("Billing", self.show_billing),
            ("Logout", self.show_login)
        ]

        for text, command in nav_buttons:
            ttk.Button(sidebar, text=text, command=command).pack(fill="x", padx=10, pady=5)

        self.content_area = ttk.Frame(main_container)
        self.content_area.pack(side="right", fill="both", expand=True)

        self.show_dashboard()

    def clear_content(self):
        for widget in self.content_area.winfo_children():
            widget.destroy()

    def show_dashboard(self):
        self.clear_content()

        ttk.Label(self.content_area, text="Clinic Dashboard", style='Header.TLabel').pack(pady=10)

        stats_frame = ttk.Frame(self.content_area)
        stats_frame.pack(fill="x", padx=20, pady=10)

        stats = [
            ("Patients", "👥", "SELECT COUNT(*) FROM Patients WHERE IsActive=1"),
            ("Doctors", "👨‍⚕", "SELECT COUNT(*) FROM Doctors WHERE IsActive=1"),
            ("Today's Appointments", "📅", f"SELECT COUNT(*) FROM Appointments WHERE AppointmentDate='{date.today()}'"),
            ("Departments", "🏥", "SELECT COUNT(*) FROM Departments WHERE IsActive=1")
        ]

        for i, (title, icon, query) in enumerate(stats):
            card = ttk.Frame(stats_frame, relief="groove", borderwidth=1)
            card.grid(row=0, column=i, padx=10, sticky="nsew")
            stats_frame.columnconfigure(i, weight=1)

            cursor = self.db.conn.cursor()
            cursor.execute(query)
            count = cursor.fetchone()[0]

            ttk.Label(card, text=icon, font=("Arial", 24)).pack(pady=5)
            ttk.Label(card, text=str(count), font=("Arial", 18, "bold")).pack()
            ttk.Label(card, text=title).pack(pady=5)

        ttk.Label(self.content_area, text="Recent Appointments").pack(pady=10)

        columns = ("ID", "Patient", "Doctor", "Date", "Time", "Status")
        tree = ttk.Treeview(self.content_area, columns=columns, show="headings", height=8)

        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120)

        scrollbar = ttk.Scrollbar(self.content_area, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.pack(side="left", fill="both", expand=True, padx=20)
        scrollbar.pack(side="right", fill="y")

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT a.AppointmentID, 
               p.FirstName || ' ' || p.LastName,
               u.FirstName || ' ' || u.LastName,
               a.AppointmentDate, a.AppointmentTime, 
               s.StatusName
        FROM Appointments a
        JOIN Patients p ON a.PatientID = p.PatientID
        JOIN Doctors d ON a.DoctorID = d.DoctorID
        JOIN Users u ON d.UserID = u.UserID
        JOIN AppointmentStatuses s ON a.StatusID = s.StatusID
        ORDER BY a.AppointmentDate DESC, a.AppointmentTime DESC
        LIMIT 10
        ''')

        for row in cursor.fetchall():
            tree.insert("", "end", values=row)

    def show_patient_management(self):
        self.clear_content()
        PatientManagementFrame(self.content_area, self.db).pack(fill="both", expand=True)

    def show_appointment_management(self):
        self.clear_content()
        AppointmentManagementFrame(self.content_area, self.db).pack(fill="both", expand=True)

    def show_doctor_management(self):
        self.clear_content()
        DoctorManagementFrame(self.content_area, self.db).pack(fill="both", expand=True)

    def show_billing(self):
        self.clear_content()
        BillingManagementFrame(self.content_area, self.db, self.user_id).pack(fill="both", expand=True)


class PatientManagementFrame(ttk.Frame):
    """Comprehensive patient management"""

    def __init__(self, parent, db):
        super().__init__(parent, padding="10")
        self.db = db
        self.current_patient = None

        form_frame = ttk.LabelFrame(self, text="Patient Information", padding="10")
        form_frame.pack(fill="x", padx=5, pady=5)

        fields = [
            ("First Name", "first_name", 0, 0),
            ("Last Name", "last_name", 0, 2),
            ("Date of Birth", "dob", 1, 0),
            ("Gender", "gender", 1, 2),
            ("Blood Group", "blood_group", 2, 0),
            ("Phone", "phone", 2, 2),
            ("Email", "email", 3, 0, 3),
            ("Address", "address", 4, 0, 3),
            ("Emergency Contact", "emergency_contact", 5, 0),
            ("Emergency Phone", "emergency_phone", 5, 2)
        ]

        self.vars = {}
        for field in fields:
            label_text, var_name, row, col, *colspan = field
            ttk.Label(form_frame, text=label_text + ":").grid(row=row, column=col, sticky="w", padx=5, pady=2)

            if var_name == "gender":
                self.vars[var_name] = tk.StringVar()
                ttk.Combobox(form_frame, textvariable=self.vars[var_name],
                             values=["Male", "Female", "Other"], state="readonly").grid(
                    row=row, column=col + 1, padx=5, pady=2)
            elif var_name == "blood_group":
                self.vars[var_name] = tk.StringVar()
                ttk.Combobox(form_frame, textvariable=self.vars[var_name],
                             values=["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"],
                             state="readonly").grid(row=row, column=col + 1, padx=5, pady=2)
            elif var_name == "dob":
                self.vars[var_name] = tk.StringVar()
                DateEntry(form_frame, textvariable=self.vars[var_name],
                          date_pattern='y-mm-dd').grid(row=row, column=col + 1, padx=5, pady=2)
            else:
                self.vars[var_name] = tk.StringVar()
                ttk.Entry(form_frame, textvariable=self.vars[var_name]).grid(
                    row=row, column=col + 1, columnspan=colspan[0] if colspan else 1,
                    sticky="ew", padx=5, pady=2)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=6, column=0, columnspan=4, pady=10)

        ttk.Button(btn_frame, text="New", command=self.new_patient).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_patient).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_patient).pack(side="left", padx=5)

        list_frame = ttk.LabelFrame(self, text="Patient List", padding="10")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(search_frame, text="Search", command=self.search_patients).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Refresh", command=self.load_patients).pack(side="left")

        columns = ("ID", "Code", "Name", "Gender", "Age", "Phone", "Email")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        self.tree.bind("<<TreeviewSelect>>", self.on_patient_select)

        self.load_patients()
        self.new_patient()

    def load_patients(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT PatientID, PatientCode, 
               FirstName || ' ' || LastName, 
               Gender, 
               strftime('%Y', 'now') - strftime('%Y', DateOfBirth),
               PhoneNumber, Email
        FROM Patients
        WHERE IsActive = 1
        ORDER BY LastName, FirstName
        ''')

        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def search_patients(self):
        search_term = f"%{self.search_var.get()}%"

        for item in self.tree.get_children():
            self.tree.delete(item)

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT PatientID, PatientCode, 
               FirstName || ' ' || LastName, 
               Gender, 
               strftime('%Y', 'now') - strftime('%Y', DateOfBirth),
               PhoneNumber, Email
        FROM Patients
        WHERE IsActive = 1 
        AND (FirstName LIKE ? OR LastName LIKE ? OR PatientCode LIKE ?)
        ORDER BY LastName, FirstName
        ''', (search_term, search_term, search_term))

        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def new_patient(self):
        self.current_patient = None
        for var in self.vars.values():
            var.set("")
        self.vars["gender"].set("Male")
        self.focus_set()

    def on_patient_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        patient_id = item['values'][0]

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT PatientID, FirstName, LastName, DateOfBirth, Gender, 
               BloodGroup, PhoneNumber, Email, Address, 
               EmergencyContactName, EmergencyContactPhone
        FROM Patients
        WHERE PatientID = ?
        ''', (patient_id,))

        patient = cursor.fetchone()
        if patient:
            self.current_patient = patient[0]
            self.vars["first_name"].set(patient[1])
            self.vars["last_name"].set(patient[2])
            self.vars["dob"].set(patient[3])
            self.vars["gender"].set(patient[4])
            self.vars["blood_group"].set(patient[5] if patient[5] else "")
            self.vars["phone"].set(patient[6] if patient[6] else "")
            self.vars["email"].set(patient[7] if patient[7] else "")
            self.vars["address"].set(patient[8] if patient[8] else "")
            self.vars["emergency_contact"].set(patient[9] if patient[9] else "")
            self.vars["emergency_phone"].set(patient[10] if patient[10] else "")

    def save_patient(self):
        if not self.validate_form():
            return

        data = {
            'first_name': self.vars["first_name"].get(),
            'last_name': self.vars["last_name"].get(),
            'dob': self.vars["dob"].get(),
            'gender': self.vars["gender"].get(),
            'blood_group': self.vars["blood_group"].get() or None,
            'phone': self.vars["phone"].get() or None,
            'email': self.vars["email"].get() or None,
            'address': self.vars["address"].get() or None,
            'emergency_contact': self.vars["emergency_contact"].get() or None,
            'emergency_phone': self.vars["emergency_phone"].get() or None
        }

        try:
            cursor = self.db.conn.cursor()
            if self.current_patient:
                cursor.execute('''
                UPDATE Patients 
                SET FirstName=?, LastName=?, DateOfBirth=?, Gender=?, 
                    BloodGroup=?, PhoneNumber=?, Email=?, Address=?, 
                    EmergencyContactName=?, EmergencyContactPhone=?,
                    ModifiedDate=CURRENT_TIMESTAMP
                WHERE PatientID=?
                ''', (*data.values(), self.current_patient))
                message = "Patient updated successfully"
            else:
                cursor.execute('''
                INSERT INTO Patients (
                    FirstName, LastName, DateOfBirth, Gender, 
                    BloodGroup, PhoneNumber, Email, Address, 
                    EmergencyContactName, EmergencyContactPhone
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', tuple(data.values()))
                message = "Patient added successfully"

            self.db.conn.commit()
            messagebox.showinfo("Success", message)
            self.load_patients()
            self.new_patient()

        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")

    def delete_patient(self):
        if not self.current_patient:
            messagebox.showwarning("Warning", "No patient selected")
            return

        if messagebox.askyesno("Confirm", "Delete this patient record?"):
            cursor = self.db.conn.cursor()
            cursor.execute('''
            UPDATE Patients 
            SET IsActive=0, ModifiedDate=CURRENT_TIMESTAMP
            WHERE PatientID=?
            ''', (self.current_patient,))

            self.db.conn.commit()
            messagebox.showinfo("Success", "Patient deleted")
            self.load_patients()
            self.new_patient()

    def validate_form(self):
        errors = []
        if not self.vars["first_name"].get():
            errors.append("First name is required")
        if not self.vars["last_name"].get():
            errors.append("Last name is required")
        if not self.vars["dob"].get():
            errors.append("Date of birth is required")

        email = self.vars["email"].get()
        if email and not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            errors.append("Invalid email format")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False
        return True


class AppointmentManagementFrame(ttk.Frame):
    """Appointment scheduling and management"""

    def __init__(self, parent, db):
        super().__init__(parent, padding="10")
        self.db = db
        self.current_appointment = None

        form_frame = ttk.LabelFrame(self, text="Appointment Details", padding="10")
        form_frame.pack(fill="x", padx=5, pady=5)

        fields = [
            ("Patient", "patient", 0, 0),
            ("Doctor", "doctor", 1, 0),
            ("Date", "date", 2, 0),
            ("Time", "time", 2, 2),
            ("Status", "status", 3, 0),
            ("Notes", "notes", 4, 0, 3)
        ]

        self.vars = {}
        for field in fields:
            label_text, var_name, row, col, *colspan = field
            ttk.Label(form_frame, text=label_text + ":").grid(row=row, column=col, sticky="w", padx=5, pady=2)

            if var_name in ["patient", "doctor", "status"]:
                self.vars[var_name] = tk.StringVar()
                combo = ttk.Combobox(form_frame, textvariable=self.vars[var_name], state="readonly")
                combo.grid(row=row, column=col + 1, columnspan=colspan[0] if colspan else 1,
                           sticky="ew", padx=5, pady=2)

                if var_name == "patient":
                    self.patient_combo = combo
                    self.load_patients()
                elif var_name == "doctor":
                    self.doctor_combo = combo
                    self.load_doctors()
                elif var_name == "status":
                    self.status_combo = combo
                    self.load_statuses()

            elif var_name == "date":
                self.vars[var_name] = tk.StringVar()
                DateEntry(form_frame, textvariable=self.vars[var_name],
                          date_pattern='y-mm-dd').grid(row=row, column=col + 1, padx=5, pady=2)

            elif var_name == "time":
                self.vars[var_name] = tk.StringVar()
                ttk.Combobox(form_frame, textvariable=self.vars[var_name],
                             values=[f"{h:02d}:{m:02d}" for h in range(8, 18) for m in [0, 15, 30, 45]],
                             state="normal").grid(row=row, column=col + 1, padx=5, pady=2)

            else:
                self.vars[var_name] = tk.StringVar()
                ttk.Entry(form_frame, textvariable=self.vars[var_name]).grid(
                    row=row, column=col + 1, columnspan=colspan[0] if colspan else 1,
                    sticky="ew", padx=5, pady=2)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=4, pady=10)

        ttk.Button(btn_frame, text="New", command=self.new_appointment).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_appointment).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.cancel_appointment).pack(side="left", padx=5)

        list_frame = ttk.LabelFrame(self, text="Appointment List", padding="10")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        filter_frame = ttk.Frame(list_frame)
        filter_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(filter_frame, text="Filter by Date:").pack(side="left")
        self.filter_date_var = tk.StringVar()
        DateEntry(filter_frame, textvariable=self.filter_date_var,
                  date_pattern='y-mm-dd').pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Filter", command=self.filter_appointments).pack(side="left", padx=5)
        ttk.Button(filter_frame, text="Show All", command=self.load_appointments).pack(side="left")

        columns = ("ID", "Patient", "Doctor", "Date", "Time", "Status", "Notes")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        self.tree.bind("<<TreeviewSelect>>", self.on_appointment_select)

        self.load_appointments()
        self.new_appointment()

    def load_patients(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT PatientID, FirstName || ' ' || LastName || ' (' || PatientCode || ')'
        FROM Patients
        WHERE IsActive = 1
        ORDER BY LastName, FirstName
        ''')

        patients = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        self.patient_combo['values'] = patients

    def load_doctors(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT d.DoctorID, u.FirstName || ' ' || u.LastName || ' (' || s.Name || ')'
        FROM Doctors d
        JOIN Users u ON d.UserID = u.UserID
        JOIN Specializations s ON d.SpecializationID = s.SpecializationID
        WHERE d.IsActive = 1
        ORDER BY u.LastName, u.FirstName
        ''')

        doctors = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        self.doctor_combo['values'] = doctors

    def load_statuses(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT StatusID, StatusName
        FROM AppointmentStatuses
        ORDER BY StatusName
        ''')

        statuses = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        self.status_combo['values'] = statuses

    def load_appointments(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT a.AppointmentID, 
               p.FirstName || ' ' || p.LastName,
               u.FirstName || ' ' || u.LastName,
               a.AppointmentDate, a.AppointmentTime, 
               s.StatusName, a.Notes
        FROM Appointments a
        JOIN Patients p ON a.PatientID = p.PatientID
        JOIN Doctors d ON a.DoctorID = d.DoctorID
        JOIN Users u ON d.UserID = u.UserID
        JOIN AppointmentStatuses s ON a.StatusID = s.StatusID
        ORDER BY a.AppointmentDate DESC, a.AppointmentTime DESC
        ''')

        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def filter_appointments(self):
        filter_date = self.filter_date_var.get()
        if not filter_date:
            messagebox.showwarning("Warning", "Please select a date to filter")
            return

        for item in self.tree.get_children():
            self.tree.delete(item)

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT a.AppointmentID, 
               p.FirstName || ' ' || p.LastName,
               u.FirstName || ' ' || u.LastName,
               a.AppointmentDate, a.AppointmentTime, 
               s.StatusName, a.Notes
        FROM Appointments a
        JOIN Patients p ON a.PatientID = p.PatientID
        JOIN Doctors d ON a.DoctorID = d.DoctorID
        JOIN Users u ON d.UserID = u.UserID
        JOIN AppointmentStatuses s ON a.StatusID = s.StatusID
        WHERE a.AppointmentDate = ?
        ORDER BY a.AppointmentDate DESC, a.AppointmentTime DESC
        ''', (filter_date,))

        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def new_appointment(self):
        self.current_appointment = None
        for var in self.vars.values():
            var.set("")
        self.vars["status"].set("1:Scheduled")

    def on_appointment_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        appt_id = item['values'][0]

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT a.AppointmentID, a.PatientID, a.DoctorID, a.AppointmentDate, 
               a.AppointmentTime, a.StatusID, a.Notes
        FROM Appointments a
        WHERE a.AppointmentID = ?
        ''', (appt_id,))

        appt = cursor.fetchone()
        if appt:
            self.current_appointment = appt[0]
            self.vars["patient"].set(f"{appt[1]}:")
            self.vars["doctor"].set(f"{appt[2]}:")
            self.vars["date"].set(appt[3])
            self.vars["time"].set(appt[4])
            self.vars["status"].set(f"{appt[5]}:")
            self.vars["notes"].set(appt[6] if appt[6] else "")

    def save_appointment(self):
        if not self.validate_form():
            return

        patient_id = int(self.vars["patient"].get().split(':')[0])
        doctor_id = int(self.vars["doctor"].get().split(':')[0])
        status_id = int(self.vars["status"].get().split(':')[0])
        appt_date = self.vars["date"].get()
        appt_time = self.vars["time"].get()
        notes = self.vars["notes"].get()

        try:
            cursor = self.db.conn.cursor()
            if self.current_appointment:
                cursor.execute('''
                UPDATE Appointments 
                SET PatientID=?, DoctorID=?, AppointmentDate=?, AppointmentTime=?, 
                    StatusID=?, Notes=?
                WHERE AppointmentID=?
                ''', (patient_id, doctor_id, appt_date, appt_time, status_id, notes, self.current_appointment))
                message = "Appointment updated successfully"
            else:
                cursor.execute('''
                INSERT INTO Appointments (
                    PatientID, DoctorID, AppointmentDate, AppointmentTime, StatusID, Notes
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (patient_id, doctor_id, appt_date, appt_time, status_id, notes))
                message = "Appointment added successfully"

            self.db.conn.commit()
            messagebox.showinfo("Success", message)
            self.load_appointments()
            self.new_appointment()

        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")

    def cancel_appointment(self):
        if not self.current_appointment:
            messagebox.showwarning("Warning", "No appointment selected")
            return

        if messagebox.askyesno("Confirm", "Cancel this appointment?"):
            try:
                cursor = self.db.conn.cursor()
                cursor.execute('''
                DELETE FROM Appointments WHERE AppointmentID=?
                ''', (self.current_appointment,))
                self.db.conn.commit()
                messagebox.showinfo("Success", "Appointment cancelled")
                self.load_appointments()
                self.new_appointment()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Database error: {str(e)}")

    def validate_form(self):
        errors = []
        if not self.vars["patient"].get():
            errors.append("Patient is required")
        if not self.vars["doctor"].get():
            errors.append("Doctor is required")
        if not self.vars["date"].get():
            errors.append("Date is required")
        if not self.vars["time"].get():
            errors.append("Time is required")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False
        return True


class DoctorManagementFrame(ttk.Frame):
    """Doctor management screen"""

    def __init__(self, parent, db):
        super().__init__(parent, padding="10")
        self.db = db
        self.current_doctor = None

        # Doctor Information Form
        form_frame = ttk.LabelFrame(self, text="Doctor Information", padding="10")
        form_frame.pack(fill="x", padx=5, pady=5)

        # Fields: user, specialization, department, license, experience
        fields = [
            ("User", "user", 0, 0),
            ("Specialization", "specialization", 1, 0),
            ("Department", "department", 2, 0),
            ("License Number", "license", 3, 0),
            ("Years of Experience", "experience", 4, 0)
        ]

        self.vars = {}
        for label_text, var_name, row, col in fields:
            ttk.Label(form_frame, text=label_text + ":").grid(row=row, column=col, sticky="w", padx=5, pady=2)

            if var_name in ["user", "specialization", "department"]:
                self.vars[var_name] = tk.StringVar()
                combo = ttk.Combobox(form_frame, textvariable=self.vars[var_name], state="readonly")
                combo.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=2)

                if var_name == "user":
                    self.user_combo = combo
                elif var_name == "specialization":
                    self.spec_combo = combo
                elif var_name == "department":
                    self.dept_combo = combo
            else:
                self.vars[var_name] = tk.StringVar()
                ttk.Entry(form_frame, textvariable=self.vars[var_name]).grid(
                    row=row, column=col + 1, sticky="ew", padx=5, pady=2)

        # Buttons
        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="New", command=self.new_doctor).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_doctor).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_doctor).pack(side="left", padx=5)

        # Doctor List
        list_frame = ttk.LabelFrame(self, text="Doctor List", padding="10")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Search Frame
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(search_frame, text="Search", command=self.search_doctors).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Refresh", command=self.load_doctors).pack(side="left")

        # Treeview
        columns = ("ID", "Name", "Specialization", "Department", "License", "Experience")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        # Bind selection
        self.tree.bind("<<TreeviewSelect>>", self.on_doctor_select)

        # Load initial data
        self.load_doctors()
        self.new_doctor()
        self.load_users()
        self.load_specializations()
        self.load_departments()

    def load_users(self):
        """Load users (doctors only) into combobox"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT UserID, FirstName || ' ' || LastName || ' (' || Role || ')'
        FROM Users
        WHERE Role = 'Doctor' AND IsActive = 1
        ORDER BY LastName, FirstName
        ''')
        users = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        self.user_combo['values'] = users

    def load_specializations(self):
        """Load specializations into combobox"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT SpecializationID, Name
        FROM Specializations
        WHERE IsActive = 1
        ORDER BY Name
        ''')
        specializations = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        self.spec_combo['values'] = specializations

    def load_departments(self):
        """Load departments into combobox"""
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT DepartmentID, DepartmentName
        FROM Departments
        WHERE IsActive = 1
        ORDER BY DepartmentName
        ''')
        departments = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        self.dept_combo['values'] = departments

    def load_doctors(self):
        """Load doctors into treeview"""
        for item in self.tree.get_children():
            self.tree.delete(item)

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT d.DoctorID, u.FirstName || ' ' || u.LastName, s.Name, 
               dept.DepartmentName, d.LicenseNumber, d.YearsOfExperience
        FROM Doctors d
        JOIN Users u ON d.UserID = u.UserID
        JOIN Specializations s ON d.SpecializationID = s.SpecializationID
        LEFT JOIN Departments dept ON d.DepartmentID = dept.DepartmentID
        WHERE d.IsActive = 1
        ORDER BY u.LastName, u.FirstName
        ''')

        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def search_doctors(self):
        """Search doctors by name or license"""
        search_term = f"%{self.search_var.get()}%"

        for item in self.tree.get_children():
            self.tree.delete(item)

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT d.DoctorID, u.FirstName || ' ' || u.LastName, s.Name, 
               dept.DepartmentName, d.LicenseNumber, d.YearsOfExperience
        FROM Doctors d
        JOIN Users u ON d.UserID = u.UserID
        JOIN Specializations s ON d.SpecializationID = s.SpecializationID
        LEFT JOIN Departments dept ON d.DepartmentID = dept.DepartmentID
        WHERE d.IsActive = 1
        AND (u.FirstName LIKE ? OR u.LastName LIKE ? OR d.LicenseNumber LIKE ?)
        ORDER BY u.LastName, u.FirstName
        ''', (search_term, search_term, search_term))

        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def new_doctor(self):
        """Clear form for new doctor"""
        self.current_doctor = None
        for var in self.vars.values():
            var.set("")

    def on_doctor_select(self, event):
        """Load selected doctor into form"""
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        doctor_id = item['values'][0]

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT d.DoctorID, d.UserID, d.SpecializationID, d.DepartmentID, 
               d.LicenseNumber, d.YearsOfExperience
        FROM Doctors d
        WHERE d.DoctorID = ?
        ''', (doctor_id,))

        doctor = cursor.fetchone()
        if doctor:
            self.current_doctor = doctor[0]
            self.vars["user"].set(f"{doctor[1]}:")
            self.vars["specialization"].set(f"{doctor[2]}:")
            self.vars["department"].set(f"{doctor[3] or ''}:")
            self.vars["license"].set(doctor[4])
            self.vars["experience"].set(str(doctor[5]) if doctor[5] is not None else "")

    def save_doctor(self):
        """Save current doctor (new or existing)"""
        if not self.validate_form():
            return

        user_id = int(self.vars["user"].get().split(':')[0]) if self.vars["user"].get() else None
        spec_id = int(self.vars["specialization"].get().split(':')[0]) if self.vars["specialization"].get() else None
        dept_id = self.vars["department"].get().split(':')[0]
        dept_id = int(dept_id) if dept_id.strip() else None
        license_num = self.vars["license"].get()
        experience = int(self.vars["experience"].get()) if self.vars["experience"].get() else 0

        try:
            cursor = self.db.conn.cursor()
            if self.current_doctor:
                # Update existing doctor
                cursor.execute('''
                UPDATE Doctors 
                SET UserID=?, SpecializationID=?, DepartmentID=?, 
                    LicenseNumber=?, YearsOfExperience=?
                WHERE DoctorID=?
                ''', (user_id, spec_id, dept_id, license_num, experience, self.current_doctor))
                message = "Doctor updated successfully"
            else:
                # Insert new doctor
                cursor.execute('''
                INSERT INTO Doctors (
                    UserID, SpecializationID, DepartmentID, LicenseNumber, YearsOfExperience
                )
                VALUES (?, ?, ?, ?, ?)
                ''', (user_id, spec_id, dept_id, license_num, experience))
                message = "Doctor added successfully"

            self.db.conn.commit()
            messagebox.showinfo("Success", message)
            self.load_doctors()
            self.new_doctor()

        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")

    def delete_doctor(self):
        """Mark doctor as inactive (soft delete)"""
        if not self.current_doctor:
            messagebox.showwarning("Warning", "No doctor selected")
            return

        if messagebox.askyesno("Confirm", "Delete this doctor record?"):
            try:
                cursor = self.db.conn.cursor()
                cursor.execute('''
                UPDATE Doctors 
                SET IsActive=0 
                WHERE DoctorID=?
                ''', (self.current_doctor,))
                self.db.conn.commit()
                messagebox.showinfo("Success", "Doctor deleted")
                self.load_doctors()
                self.new_doctor()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Database error: {str(e)}")

    def validate_form(self):
        """Validate doctor form data"""
        errors = []
        if not self.vars["user"].get():
            errors.append("User is required")
        if not self.vars["specialization"].get():
            errors.append("Specialization is required")
        if not self.vars["license"].get():
            errors.append("License number is required")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False
        return True
class DoctorManagementFrame(ttk.Frame):
    """Doctor management screen"""

    def __init__(self, parent, db):
        super().__init__(parent, padding="10")
        self.db = db
        self.current_doctor = None

        form_frame = ttk.LabelFrame(self, text="Doctor Information", padding="10")
        form_frame.pack(fill="x", padx=5, pady=5)

        fields = [
            ("User", "user", 0, 0),
            ("Specialization", "specialization", 1, 0),
            ("Department", "department", 2, 0),
            ("License Number", "license", 3, 0),
            ("Years of Experience", "experience", 4, 0)
        ]

        self.vars = {}
        for field in fields:
            label_text, var_name, row, col = field
            ttk.Label(form_frame, text=label_text + ":").grid(row=row, column=col, sticky="w", padx=5, pady=2)

            if var_name in ["user", "specialization", "department"]:
                self.vars[var_name] = tk.StringVar()
                combo = ttk.Combobox(form_frame, textvariable=self.vars[var_name], state="readonly")
                combo.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=2)

                if var_name == "user":
                    self.user_combo = combo
                    self.load_users()
                elif var_name == "specialization":
                    self.spec_combo = combo
                    self.load_specializations()
                elif var_name == "department":
                    self.dept_combo = combo
                    self.load_departments()
            else:
                self.vars[var_name] = tk.StringVar()
                ttk.Entry(form_frame, textvariable=self.vars[var_name]).grid(
                    row=row, column=col + 1, sticky="ew", padx=5, pady=2)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="New", command=self.new_doctor).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_doctor).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_doctor).pack(side="left", padx=5)

        list_frame = ttk.LabelFrame(self, text="Doctor List", padding="10")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(search_frame, text="Search:").pack(side="left")
        self.search_var = tk.StringVar()
        ttk.Entry(search_frame, textvariable=self.search_var).pack(side="left", padx=5, expand=True, fill="x")
        ttk.Button(search_frame, text="Search", command=self.search_doctors).pack(side="left", padx=5)
        ttk.Button(search_frame, text="Refresh", command=self.load_doctors).pack(side="left")

        columns = ("ID", "Name", "Specialization", "Department", "License", "Experience")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)

        scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        self.tree.bind("<<TreeviewSelect>>", self.on_doctor_select)

        self.load_doctors()
        self.new_doctor()

    def load_users(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT UserID, FirstName || ' ' || LastName || ' (' || Role || ')'
        FROM Users
        WHERE Role = 'Doctor' AND IsActive = 1
        ORDER BY LastName, FirstName
        ''')
        users = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        self.user_combo['values'] = users

    def load_specializations(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT SpecializationID, Name
        FROM Specializations
        WHERE IsActive = 1
        ORDER BY Name
        ''')
        specializations = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        self.spec_combo['values'] = specializations

    def load_departments(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT DepartmentID, DepartmentName
        FROM Departments
        WHERE IsActive = 1
        ORDER BY DepartmentName
        ''')
        departments = [f"{row[0]}:{row[1]}" for row in cursor.fetchall()]
        self.dept_combo['values'] = departments

    def load_doctors(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT d.DoctorID, u.FirstName || ' ' || u.LastName, s.Name, 
               dept.DepartmentName, d.LicenseNumber, d.YearsOfExperience
        FROM Doctors d
        JOIN Users u ON d.UserID = u.UserID
        JOIN Specializations s ON d.SpecializationID = s.SpecializationID
        LEFT JOIN Departments dept ON d.DepartmentID = dept.DepartmentID
        WHERE d.IsActive = 1
        ORDER BY u.LastName, u.FirstName
        ''')

        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def search_doctors(self):
        search_term = f"%{self.search_var.get()}%"

        for item in self.tree.get_children():
            self.tree.delete(item)

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT d.DoctorID, u.FirstName || ' ' || u.LastName, s.Name, 
               dept.DepartmentName, d.LicenseNumber, d.YearsOfExperience
        FROM Doctors d
        JOIN Users u ON d.UserID = u.UserID
        JOIN Specializations s ON d.SpecializationID = s.SpecializationID
        LEFT JOIN Departments dept ON d.DepartmentID = dept.DepartmentID
        WHERE d.IsActive = 1
        AND (u.FirstName LIKE ? OR u.LastName LIKE ? OR d.LicenseNumber LIKE ?)
        ORDER BY u.LastName, u.FirstName
        ''', (search_term, search_term, search_term))

        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def new_doctor(self):
        self.current_doctor = None
        for var in self.vars.values():
            var.set("")

    def on_doctor_select(self, event):
        selection = self.ttree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        doctor_id = item['values'][0]

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT d.DoctorID, d.UserID, d.SpecializationID, d.DepartmentID, 
               d.LicenseNumber, d.YearsOfExperience
        FROM Doctors d
        WHERE d.DoctorID = ?
        ''', (doctor_id,))

        doctor = cursor.fetchone()
        if doctor:
            self.current_doctor = doctor[0]
            self.vars["user"].set(f"{doctor[1]}:")
            self.vars["specialization"].set(f"{doctor[2]}:")
            self.vars["department"].set(f"{doctor[3] or ''}:")
            self.vars["license"].set(doctor[4])
            self.vars["experience"].set(str(doctor[5]))

    def save_doctor(self):
        if not self.validate_form():
            return

        user_id = int(self.vars["user"].get().split(':')[0])
        spec_id = int(self.vars["specialization"].get().split(':')[0])
        dept_id = self.vars["department"].get().split(':')[0]
        if not dept_id.strip():
            dept_id = None
        else:
            dept_id = int(dept_id)
        license_num = self.vars["license"].get()
        experience = int(self.vars["experience"].get()) if self.vars["experience"].get() else 0

        try:
            cursor = self.db.conn.cursor()
            if self.current_doctor:
                cursor.execute('''
                UPDATE Doctors 
                SET UserID=?, SpecializationID=?, DepartmentID=?, 
                    LicenseNumber=?, YearsOfExperience=?
                WHERE DoctorID=?
                ''', (user_id, spec_id, dept_id, license_num, experience, self.current_doctor))
                message = "Doctor updated successfully"
            else:
                cursor.execute('''
                INSERT INTO Doctors (
                    UserID, SpecializationID, DepartmentID, LicenseNumber, YearsOfExperience
                )
                VALUES (?, ?, ?, ?, ?)
                ''', (user_id, spec_id, dept_id, license_num, experience))
                message = "Doctor added successfully"

            self.db.conn.commit()
            messagebox.showinfo("Success", message)
            self.load_doctors()
            self.new_doctor()

        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")

    def delete_doctor(self):
        if not self.current_doctor:
            messagebox.showwarning("Warning", "No doctor selected")
            return

        if messagebox.askyesno("Confirm", "Delete this doctor record?"):
            try:
                cursor = self.db.conn.cursor()
                cursor.execute('''
                UPDATE Doctors SET IsActive=0 WHERE DoctorID=?
                ''', (self.current_doctor,))
                self.db.conn.commit()
                messagebox.showinfo("Success", "Doctor deleted")
                self.load_doctors()
                self.new_doctor()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Database error: {str(e)}")

    def validate_form(self):
        errors = []
        if not self.vars["user"].get():
            errors.append("User is required")
        if not self.vars["specialization"].get():
            errors.append("Specialization is required")
        if not self.vars["license"].get():
            errors.append("License number is required")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False
        return True


class BillingManagementFrame(ttk.Frame):
    """Billing and payment management"""

    def __init__(self, parent, db, user_id):
        super().__init__(parent, padding="10")
        self.db = db
        self.user_id = user_id
        self.current_bill = None

        form_frame = ttk.LabelFrame(self, text="Bill Information", padding="10")
        form_frame.pack(fill="x", padx=5, pady=5)

        fields = [
            ("Appointment", "appointment", 0, 0),
            ("Total Amount", "total", 1, 0),
            ("Payment Status", "status", 2, 0),
            ("Payment Method", "method", 3, 0),
            ("Paid Amount", "paid", 4, 0)
        ]

        self.vars = {}
        for field in fields:
            label_text, var_name, row, col = field
            ttk.Label(form_frame, text=label_text + ":").grid(row=row, column=col, sticky="w", padx=5, pady=2)

            if var_name == "appointment":
                self.vars[var_name] = tk.StringVar()
                self.appointment_combo = ttk.Combobox(form_frame, textvariable=self.vars[var_name], state="readonly")
                self.appointment_combo.grid(row=row, column=col + 1, sticky="ew", padx=5, pady=2)
                self.load_appointments()
            elif var_name == "status":
                self.vars[var_name] = tk.StringVar()
                ttk.Combobox(form_frame, textvariable=self.vars[var_name],
                             values=["Unpaid", "PartiallyPaid", "Paid"], state="readonly").grid(
                    row=row, column=col + 1, sticky="ew", padx=5, pady=2)
            elif var_name == "method":
                self.vars[var_name] = tk.StringVar()
                ttk.Combobox(form_frame, textvariable=self.vars[var_name],
                             values=["Cash", "Credit Card", "Bank Transfer"], state="readonly").grid(
                    row=row, column=col + 1, sticky="ew", padx=5, pady=2)
            else:
                self.vars[var_name] = tk.StringVar()
                ttk.Entry(form_frame, textvariable=self.vars[var_name]).grid(
                    row=row, column=col + 1, sticky="ew", padx=5, pady=2)

        btn_frame = ttk.Frame(form_frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="New", command=self.new_bill).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save", command=self.save_bill).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Delete", command=self.delete_bill).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Add Item", command=self.add_bill_item).pack(side="left", padx=5)

        list_frame = ttk.LabelFrame(self, text="Bill List", padding="10")
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("ID", "Appointment", "Total", "Paid", "Due", "Status", "Method")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", selectmode="browse")

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        scroll_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")

        self.tree.bind("<<TreeviewSelect>>", self.on_bill_select)

        self.load_bills()
        self.new_bill()

    def load_appointments(self):
        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT a.AppointmentID, p.FirstName || ' ' || p.LastName, a.AppointmentDate
        FROM Appointments a
        JOIN Patients p ON a.PatientID = p.PatientID
        ORDER BY a.AppointmentDate DESC
        ''')
        appointments = [f"{row[0]}:{row[1]} ({row[2]})" for row in cursor.fetchall()]
        self.appointment_combo['values'] = appointments

    def load_bills(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT b.BillID, 
               a.AppointmentID || ': ' || p.FirstName || ' ' || p.LastName,
               b.TotalAmount, b.PaidAmount, 
               b.TotalAmount - b.PaidAmount, b.PaymentStatus, b.PaymentMethod
        FROM Bills b
        JOIN Appointments a ON b.AppointmentID = a.AppointmentID
        JOIN Patients p ON a.PatientID = p.PatientID
        ORDER BY b.BillDate DESC
        ''')

        for row in cursor.fetchall():
            self.tree.insert("", "end", values=row)

    def new_bill(self):
        self.current_bill = None
        for var in self.vars.values():
            var.set("")
        self.vars["status"].set("Unpaid")
        self.vars["method"].set("Cash")

    def on_bill_select(self, event):
        selection = self.tree.selection()
        if not selection:
            return

        item = self.tree.item(selection[0])
        bill_id = item['values'][0]

        cursor = self.db.conn.cursor()
        cursor.execute('''
        SELECT b.BillID, b.AppointmentID, b.TotalAmount, b.PaymentStatus, 
               b.PaymentMethod, b.PaidAmount
        FROM Bills b
        WHERE b.BillID = ?
        ''', (bill_id,))

        bill = cursor.fetchone()
        if bill:
            self.current_bill = bill[0]
            self.vars["appointment"].set(f"{bill[1]}:")
            self.vars["total"].set(str(bill[2]))
            self.vars["status"].set(bill[3])
            self.vars["method"].set(bill[4])
            self.vars["paid"].set(str(bill[5]))

    def save_bill(self):
        if not self.validate_form():
            return

        appointment_id = int(self.vars["appointment"].get().split(':')[0])
        total = float(self.vars["total"].get())
        status = self.vars["status"].get()
        method = self.vars["method"].get()
        paid = float(self.vars["paid"].get()) if self.vars["paid"].get() else 0.0

        try:
            cursor = self.db.conn.cursor()
            if self.current_bill:
                cursor.execute('''
                UPDATE Bills 
                SET AppointmentID=?, TotalAmount=?, PaymentStatus=?, 
                    PaymentMethod=?, PaidAmount=?
                WHERE BillID=?
                ''', (appointment_id, total, status, method, paid, self.current_bill))
                message = "Bill updated successfully"
            else:
                cursor.execute('''
                INSERT INTO Bills (
                    AppointmentID, TotalAmount, PaymentStatus, PaymentMethod, PaidAmount, CreatedBy
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (appointment_id, total, status, method, paid, self.user_id))
                message = "Bill added successfully"

            self.db.conn.commit()
            messagebox.showinfo("Success", message)
            self.load_bills()
            self.new_bill()

        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")

    def delete_bill(self):
        if not self.current_bill:
            messagebox.showwarning("Warning", "No bill selected")
            return

        if messagebox.askyesno("Confirm", "Delete this bill record?"):
            try:
                cursor = self.db.conn.cursor()
                cursor.execute('''
                DELETE FROM Bills WHERE BillID=?
                ''', (self.current_bill,))
                self.db.conn.commit()
                messagebox.showinfo("Success", "Bill deleted")
                self.load_bills()
                self.new_bill()
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Database error: {str(e)}")

    def add_bill_item(self):
        if not self.current_bill:
            messagebox.showwarning("Warning", "No bill selected")
            return

        dialog = BillItemDialog(self, self.db, self.current_bill)
        self.wait_window(dialog)
        self.load_bills()

    def validate_form(self):
        errors = []
        if not self.vars["appointment"].get():
            errors.append("Appointment is required")
        if not self.vars["total"].get():
            errors.append("Total amount is required")

        if errors:
            messagebox.showerror("Validation Error", "\n".join(errors))
            return False
        return True


class BillItemDialog(tk.Toplevel):
    """Dialog for adding bill items"""

    def __init__(self, parent, db, bill_id):
        super().__init__(parent)
        self.db = db
        self.bill_id = bill_id

        self.title("Add Bill Item")
        self.geometry("400x250")

        ttk.Label(self, text="Service Type:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.service_type = ttk.Combobox(self, values=["Consultation", "Test", "Medicine"])
        self.service_type.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self, text="Description:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.description = ttk.Entry(self)
        self.description.grid(row=1, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self, text="Quantity:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.quantity = ttk.Spinbox(self, from_=1, to=999)
        self.quantity.grid(row=2, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self, text="Unit Price:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.unit_price = ttk.Entry(self)
        self.unit_price.grid(row=3, column=1, padx=5, pady=5, sticky="ew")

        ttk.Label(self, text="Medicine/Test ID (optional):").grid(row=4, column=0, padx=5, pady=5, sticky="w")
        self.ref_id = ttk.Entry(self)
        self.ref_id.grid(row=4, column=1, padx=5, pady=5, sticky="ew")

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Add", command=self.add_item).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

    def add_item(self):
        service_type = self.service_type.get()
        description = self.description.get()
        quantity = int(self.quantity.get())
        unit_price = float(self.unit_price.get())
        ref_id = self.ref_id.get()

        if not service_type or not description or quantity <= 0 or unit_price <= 0:
            messagebox.showerror("Error", "All fields except reference ID are required and must be positive")
            return

        med_id = None
        test_id = None
        if ref_id:
            if service_type == "Medicine":
                med_id = int(ref_id)
            elif service_type == "Test":
                test_id = int(ref_id)

        try:
            cursor = self.db.conn.cursor()
            cursor.execute('''
            INSERT INTO BillItems (
                BillID, ServiceType, Description, Quantity, UnitPrice, MedicineID, TestID
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (self.bill_id, service_type, description, quantity, unit_price, med_id, test_id))
            self.db.conn.commit()
            messagebox.showinfo("Success", "Bill item added")
            self.destroy()
        except sqlite3.Error as e:
            messagebox.showerror("Error", f"Database error: {str(e)}")



if __name__ == "__main__":
    db = ClinicDatabase()
    app = MainApplication(db)
    app.mainloop()
