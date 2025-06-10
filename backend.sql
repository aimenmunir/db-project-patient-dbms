create database pdbms
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(50) NOT NULL UNIQUE,
    PasswordHash NVARCHAR(256) NOT NULL,
    FirstName NVARCHAR(50) NOT NULL,//
    LastName NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    PhoneNumber NVARCHAR(20),
    Role NVARCHAR(20) NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT CK_Users_Role CHECK (Role IN ('Admin', 'Doctor', 'Nurse', 'Receptionist')),
    CONSTRAINT CK_Users_Email CHECK (Email LIKE '%@%.%')
);
CREATE TABLE Specializations (
    SpecializationID INT IDENTITY(1,1) PRIMARY KEY,
    Name NVARCHAR(100) NOT NULL,
    Description NVARCHAR(200),
    IsActive BIT NOT NULL DEFAULT 1
);
SELECT * FROM Users;
SELECT * FROM Specializations;
CREATE TABLE Departments (
    DepartmentID INT IDENTITY(1,1) PRIMARY KEY,
    DepartmentName NVARCHAR(100) NOT NULL,
    Description NVARCHAR(200),
    Location NVARCHAR(100),
    ExtensionNumber NVARCHAR(10),
    IsActive BIT NOT NULL DEFAULT 1
);
CREATE TABLE Doctors (
    DoctorID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT NOT NULL UNIQUE,
    SpecializationID INT NOT NULL,
    DepartmentID INT,
    LicenseNumber NVARCHAR(20) NOT NULL UNIQUE,
    YearsOfExperience INT,
    IsActive BIT NOT NULL DEFAULT 1,
    CONSTRAINT FK_Doctors_User FOREIGN KEY (UserID) REFERENCES Users(UserID) ON DELETE CASCADE,
    CONSTRAINT FK_Doctors_Specialization FOREIGN KEY (SpecializationID) REFERENCES Specializations(SpecializationID),
    CONSTRAINT FK_Doctors_Department FOREIGN KEY (DepartmentID) REFERENCES Departments(DepartmentID),
    CONSTRAINT CK_Doctors_Experience CHECK (YearsOfExperience >= 0)
);
ALTER TABLE Departments
ADD HeadOfDepartment INT NULL
CONSTRAINT FK_Departments_HOD FOREIGN KEY (HeadOfDepartment) REFERENCES Doctors(DoctorID) ON DELETE SET NULL;
CREATE TABLE Patients (
    PatientID INT IDENTITY(1,1) PRIMARY KEY,
    PatientCode NVARCHAR(20) NULL, -- temporarily nullable for trigger to populate
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    DateOfBirth DATE NOT NULL,
    Gender NVARCHAR(10) NOT NULL,
    BloodGroup NVARCHAR(5),
    PhoneNumber NVARCHAR(20),
    Email NVARCHAR(100),
    Address NVARCHAR(200),
    EmergencyContactName NVARCHAR(100),
    EmergencyContactPhone NVARCHAR(20),
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ModifiedDate DATETIME2 NULL,
    
    CONSTRAINT CK_Patients_Gender CHECK (Gender IN ('Male', 'Female', 'Other')),
    CONSTRAINT CK_Patients_BloodGroup CHECK (
        BloodGroup IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-') OR BloodGroup IS NULL
    ),
    CONSTRAINT CK_Patients_Email CHECK (
        Email IS NULL OR Email LIKE '%@%.%'
    ),
    CONSTRAINT UQ_Patients_PatientCode UNIQUE (PatientCode)
);

CREATE NONCLUSTERED INDEX IDX_Patients_ModifiedDate
ON Patients(ModifiedDate);

CREATE TRIGGER trg_GeneratePatientCode
ON Patients
AFTER INSERT
AS
BEGIN
    UPDATE p
    SET p.PatientCode = 'PAT-' + RIGHT('0000' + CAST(p.PatientID AS VARCHAR(4)), 4)
    FROM Patients p
    INNER JOIN inserted i ON p.PatientID = i.PatientID;
END;
CREATE TABLE AppointmentStatuses (
    StatusID INT IDENTITY(1,1) PRIMARY KEY,
    StatusName NVARCHAR(20) NOT NULL,
    Description NVARCHAR(100)
);
CREATE TABLE Appointments (
    AppointmentID INT IDENTITY(1,1) PRIMARY KEY,
    PatientID INT NOT NULL,
    DoctorID INT NOT NULL,
    AppointmentDate DATE NOT NULL,
    AppointmentTime TIME NOT NULL,
    StatusID INT NOT NULL,
    Notes NVARCHAR(500),
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_Appointments_Patient FOREIGN KEY (PatientID) REFERENCES Patients(PatientID) ON DELETE CASCADE,
    CONSTRAINT FK_Appointments_Doctor FOREIGN KEY (DoctorID) REFERENCES Doctors(DoctorID),
    CONSTRAINT FK_Appointments_Status FOREIGN KEY (StatusID) REFERENCES AppointmentStatuses(StatusID),
    CONSTRAINT UK_Appointments_Slot UNIQUE (DoctorID, AppointmentDate, AppointmentTime),
    CONSTRAINT CK_Appointments_DateTime CHECK (AppointmentDate >= CAST(GETDATE() AS DATE) OR CreatedDate < GETDATE())
);
CREATE FUNCTION fn_CalculateBMI (
    @WeightKg DECIMAL(5,2),
    @HeightCm DECIMAL(5,2)
)
RETURNS DECIMAL(5,2)
AS
BEGIN
DECLARE @HeightM DECIMAL(5,2) = @HeightCm / 100.0;
RETURN (CASE 
WHEN @HeightM > 0 
THEN @WeightKg / (@HeightM * @HeightM)
ELSE NULL
END);
END;


CREATE TRIGGER trg_CalculateBMI_OnInsert
ON Vitals
AFTER INSERT
AS
BEGIN
    UPDATE v
    SET v.BMI = dbo.fn_CalculateBMI(i.WeightKg, i.HeightCm)
    FROM Vitals v
    INNER JOIN inserted i ON v.VitalsID = i.VitalsID;
END;
CREATE TABLE Vitals (
    VitalID INT IDENTITY(1,1) PRIMARY KEY,
    AppointmentID INT NOT NULL,
    BloodPressureSystolic INT,
    BloodPressureDiastolic INT,
    Temperature DECIMAL(4,1),
    HeartRate INT,
    Weight DECIMAL(5,2),
    Height DECIMAL(5,2),
    BMI AS (dbo.fn_CalculateBMI(Weight, Height)) PERSISTED,
    RecordedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    RecordedBy INT,
    CONSTRAINT FK_Vitals_Appointment FOREIGN KEY (AppointmentID) REFERENCES Appointments(AppointmentID) ON DELETE CASCADE,
    CONSTRAINT FK_Vitals_RecordedBy FOREIGN KEY (RecordedBy) REFERENCES Users(UserID),
    CONSTRAINT CK_Vitals_BP CHECK (BloodPressureSystolic >= 0 AND BloodPressureDiastolic >= 0),
    CONSTRAINT CK_Vitals_Temperature CHECK (Temperature BETWEEN 30.0 AND 45.0),
    CONSTRAINT CK_Vitals_HeartRate CHECK (HeartRate >= 0),
    CONSTRAINT CK_Vitals_Weight CHECK (Weight > 0),
    CONSTRAINT CK_Vitals_Height CHECK (Height > 0)
);
CREATE TABLE MedicineCategories (
    CategoryID INT IDENTITY(1,1) PRIMARY KEY,
    CategoryName NVARCHAR(100) NOT NULL UNIQUE,
    Description NVARCHAR(200),
    IsActive BIT NOT NULL DEFAULT 1
);
CREATE TABLE Medicines (
    MedicineID INT IDENTITY(1,1) PRIMARY KEY,
    MedicineCode NVARCHAR(20) NOT NULL UNIQUE,
    Name NVARCHAR(100) NOT NULL,
    CategoryID INT,
    Manufacturer NVARCHAR(100),
    UnitPrice DECIMAL(10,2) NOT NULL,
    CurrentStock INT NOT NULL DEFAULT 0,
    MinimumStock INT NOT NULL DEFAULT 0,
    MaximumStock INT NOT NULL DEFAULT 1000,
    ExpiryDate DATE,
    IsActive BIT NOT NULL DEFAULT 1,
    ModifiedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_Medicines_Category FOREIGN KEY (CategoryID) REFERENCES MedicineCategories(CategoryID),
    CONSTRAINT CK_Medicines_Price CHECK (UnitPrice >= 0),
    CONSTRAINT CK_Medicines_Stock CHECK (
        CurrentStock >= 0 AND 
        MinimumStock >= 0 AND 
        MaximumStock > MinimumStock
    )
);
CREATE TABLE LowStockAlerts (
    AlertID INT IDENTITY(1,1) PRIMARY KEY,
    MedicineID INT NOT NULL,
    MedicineCode NVARCHAR(20),
    Name NVARCHAR(100),
    CurrentStock INT,
    MinimumStock INT,
    AlertDate DATETIME2 DEFAULT GETDATE(),
    CONSTRAINT FK_LowStock_Medicine FOREIGN KEY (MedicineID) REFERENCES Medicines(MedicineID)
);
CREATE TRIGGER trg_LowStockAlert
ON Medicines
AFTER INSERT, UPDATE
AS
BEGIN
    INSERT INTO LowStockAlerts (MedicineID, MedicineCode, Name, CurrentStock, MinimumStock)
    SELECT 
        i.MedicineID,
        i.MedicineCode,
        i.Name,
        i.CurrentStock,
        i.MinimumStock
    FROM inserted i
    WHERE i.CurrentStock <= i.MinimumStock;
END;
