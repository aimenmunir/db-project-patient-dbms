
CREATE TABLE Users (
    UserID INT IDENTITY(1,1) PRIMARY KEY,
    Username NVARCHAR(50) NOT NULL UNIQUE,
    PasswordHash NVARCHAR(256) NOT NULL,
    FirstName NVARCHAR(50) NOT NULL,
    LastName NVARCHAR(50) NOT NULL,
    Email NVARCHAR(100) NOT NULL UNIQUE,
    PhoneNumber NVARCHAR(20),
    Role NVARCHAR(20) NOT NULL,
    IsActive BIT NOT NULL DEFAULT 1,
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT CK_Users_Role CHECK (Role IN ('Admin', 'Doctor', 'Nurse', 'Receptionist')),
    CONSTRAINT CK_Users_Email CHECK (Email LIKE '%@%.%')
);
CREATE NONCLUSTERED INDEX IX_Users_Email ON Users(Email);
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
CREATE NONCLUSTERED INDEX IX_Doctors_Specialization ON Doctors(SpecializationID);
ALTER TABLE Departments
ADD HeadOfDepartment INT NULL
CONSTRAINT FK_Departments_HOD FOREIGN KEY (HeadOfDepartment) REFERENCES Doctors(DoctorID) ON DELETE SET NULL;
CREATE TABLE Patients (
    PatientID INT IDENTITY(1,1) PRIMARY KEY,
    PatientCode NVARCHAR(20) NULL, 
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
CREATE NONCLUSTERED INDEX IX_Patients_Name 
ON Patients(LastName, FirstName);

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
CREATE NONCLUSTERED INDEX IX_Appointments_Date ON Appointments(AppointmentDate);
CREATE NONCLUSTERED INDEX IX_Appointments_DoctorDate ON Appointments(DoctorID, AppointmentDate);
CREATE FUNCTION dbo.fnt_CalculateBMI (
    @Weight DECIMAL(5,2),
    @Height DECIMAL(5,2)
)
RETURNS DECIMAL(5,2)
AS
BEGIN
    RETURN CASE 
               WHEN @Height > 0 THEN @Weight / POWER(@Height, 2) 
               ELSE 0 
           END;
END;
DROP FUNCTION IF EXISTS dbo.fnt_CalculateBMI;
GO

CREATE FUNCTION dbo.fnc_CalculateBMI (
    @Weight DECIMAL(5,2),
    @Height DECIMAL(5,2)
)
RETURNS DECIMAL(5,2)
WITH SCHEMABINDING
AS
BEGIN
    RETURN 
        CASE 
            WHEN @Height > 0 THEN @Weight / (@Height * @Height) 
            ELSE 0 
        END;
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
    BMI AS (dbo.fnc_CalculateBMI(Weight, Height)) PERSISTED,
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
CREATE NONCLUSTERED INDEX IX_Medicines_Stock ON Medicines(CurrentStock) WHERE IsActive = 1;
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

CREATE TABLE Prescriptions (
    PrescriptionID INT IDENTITY(1,1) PRIMARY KEY,
    AppointmentID INT NOT NULL,
    Diagnosis NVARCHAR(500),
    Instructions NVARCHAR(1000),
    CreatedDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    CreatedBy INT NOT NULL,
    CONSTRAINT FK_Prescriptions_Appointment FOREIGN KEY (AppointmentID) REFERENCES Appointments(AppointmentID) ON DELETE CASCADE,
    CONSTRAINT FK_Prescriptions_CreatedBy FOREIGN KEY (CreatedBy) REFERENCES Users(UserID)
);
CREATE TABLE PrescriptionMedicines (
    PrescriptionMedicineID INT IDENTITY(1,1) PRIMARY KEY,
    PrescriptionID INT NOT NULL,
    MedicineID INT NOT NULL,
    Dosage NVARCHAR(50) NOT NULL,
    Frequency NVARCHAR(50) NOT NULL,
    Duration NVARCHAR(50),
    Quantity INT NOT NULL,
    Notes NVARCHAR(500),
    CONSTRAINT FK_PrescriptionMedicines_Prescription FOREIGN KEY (PrescriptionID) REFERENCES Prescriptions(PrescriptionID) ON DELETE CASCADE,
    CONSTRAINT FK_PrescriptionMedicines_Medicine FOREIGN KEY (MedicineID) REFERENCES Medicines(MedicineID),
    CONSTRAINT CK_PrescriptionMedicines_Quantity CHECK (Quantity > 0)
);
CREATE TABLE MedicalTests (
    TestID INT IDENTITY(1,1) PRIMARY KEY,
    TestCode NVARCHAR(20) NOT NULL UNIQUE,
    TestName NVARCHAR(200) NOT NULL,
    DepartmentID INT,
    Cost DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    NormalRangeMin DECIMAL(10,4),
    NormalRangeMax DECIMAL(10,4),
    Unit NVARCHAR(20),
    PreparationInstructions NVARCHAR(500),
    EstimatedDuration INT,
    IsActive BIT NOT NULL DEFAULT 1,
    CONSTRAINT FK_MedicalTests_Department FOREIGN KEY (DepartmentID) REFERENCES Departments(DepartmentID) ON DELETE SET NULL,
    CONSTRAINT CK_MedicalTests_Cost CHECK (Cost >= 0)
); 
CREATE NONCLUSTERED INDEX IDX_MedicalTests_TestName
ON MedicalTests (TestName);
CREATE TABLE TestResults (
    ResultID INT IDENTITY(1,1) PRIMARY KEY,
    AppointmentID INT NOT NULL,
    TestID INT NOT NULL,
    ResultValue NVARCHAR(500),
    NumericValue DECIMAL(10,4),
    Status NVARCHAR(20) NOT NULL DEFAULT 'Pending',
    TechnicalComments NVARCHAR(500),
    DoctorComments NVARCHAR(500),
    TestDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ResultDate DATETIME2,
    TechnicianID INT,
    ReviewedBy INT,

    CONSTRAINT FK_TestResults_Appointment FOREIGN KEY (AppointmentID) 
        REFERENCES Appointments(AppointmentID) ON DELETE CASCADE,

    CONSTRAINT FK_TestResults_Test FOREIGN KEY (TestID) 
        REFERENCES MedicalTests(TestID),

    -- Fix: Only one reference to Users uses ON DELETE SET NULL
    CONSTRAINT FK_TestResults_Technician FOREIGN KEY (TechnicianID) 
        REFERENCES Users(UserID) ON DELETE SET NULL,

    CONSTRAINT FK_TestResults_ReviewedBy FOREIGN KEY (ReviewedBy) 
        REFERENCES Users(UserID) ON DELETE NO ACTION,

    CONSTRAINT CK_TestResults_Status CHECK (Status IN ('Pending', 'InProgress', 'Completed', 'Cancelled'))
);


CREATE VIEW vw_TestResultsWithAbnormalFlag AS
SELECT 
    tr.ResultID,
    tr.AppointmentID,
    tr.TestID,
    tr.ResultValue,
    tr.NumericValue,
    tr.Status,
    tr.TechnicalComments,
    tr.DoctorComments,
    tr.TestDate,
    tr.ResultDate,
    tr.TechnicianID,
    tr.ReviewedBy,
    CASE 
        WHEN tr.NumericValue IS NOT NULL AND 
             (tr.NumericValue < mt.NormalRangeMin OR tr.NumericValue > mt.NormalRangeMax)
        THEN 1 ELSE 0 
    END AS IsAbnormal
FROM TestResults tr
JOIN MedicalTests mt ON tr.TestID = mt.TestID;
CREATE TABLE Rooms (
    RoomID INT IDENTITY(1,1) PRIMARY KEY,
    RoomNumber NVARCHAR(10) NOT NULL UNIQUE,
    RoomType NVARCHAR(20) NOT NULL,
    DepartmentID INT,
    Capacity INT NOT NULL DEFAULT 1,
    CurrentOccupancy INT NOT NULL DEFAULT 0,
    DailyRate DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    IsOccupied AS (CASE WHEN CurrentOccupancy >= Capacity THEN 1 ELSE 0 END) PERSISTED,
    IsActive BIT NOT NULL DEFAULT 1,
    Equipment NVARCHAR(500),
    CONSTRAINT FK_Rooms_Department FOREIGN KEY (DepartmentID) 
        REFERENCES Departments(DepartmentID) ON DELETE SET NULL,
    CONSTRAINT CK_Rooms_Type CHECK (RoomType IN ('General', 'Private', 'ICU', 'Emergency', 'Surgery', 'Maternity')),
    CONSTRAINT CK_Rooms_Capacity CHECK (Capacity > 0),
    CONSTRAINT CK_Rooms_Occupancy CHECK (CurrentOccupancy >= 0 AND CurrentOccupancy <= Capacity)
);
CREATE TABLE Admissions (
    AdmissionID INT IDENTITY(1,1) PRIMARY KEY,
    AdmissionNumber NVARCHAR(20) NOT NULL UNIQUE,
    PatientID INT NOT NULL,
    RoomID INT NOT NULL,
    AdmittingDoctorID INT NOT NULL,
    AdmissionDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    DischargeDate DATETIME2,
    AdmissionReason NVARCHAR(500),
    CurrentStatus NVARCHAR(20) NOT NULL DEFAULT 'Active',
    
    TotalDays AS (
        CASE 
            WHEN DischargeDate IS NOT NULL 
            THEN DATEDIFF(DAY, AdmissionDate, DischargeDate) 
            ELSE DATEDIFF(DAY, AdmissionDate, GETDATE()) 
        END
    ),  
    
    EstimatedDischargeDate DATE,
    DischargeInstructions NVARCHAR(1000),
    DischargedBy INT,
    
    CONSTRAINT FK_Admissions_Patient FOREIGN KEY (PatientID) 
        REFERENCES Patients(PatientID) ON DELETE CASCADE,

    CONSTRAINT FK_Admissions_Room FOREIGN KEY (RoomID) 
        REFERENCES Rooms(RoomID),

    CONSTRAINT FK_Admissions_AdmittingDoctor FOREIGN KEY (AdmittingDoctorID) 
        REFERENCES Doctors(DoctorID),

    CONSTRAINT FK_Admissions_DischargedBy FOREIGN KEY (DischargedBy) 
        REFERENCES Users(UserID) ON DELETE NO ACTION,

    CONSTRAINT CK_Admissions_Status CHECK (CurrentStatus IN ('Active', 'Discharged', 'Transferred', 'Deceased')),

    CONSTRAINT CK_Admissions_Dates CHECK (DischargeDate IS NULL OR DischargeDate >= AdmissionDate)
);
CREATE TABLE Bills (
    BillID INT IDENTITY(1,1) PRIMARY KEY,
    AppointmentID INT,
    AdmissionID INT,
    BillDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    TotalAmount DECIMAL(10,2) NOT NULL,
    PaymentStatus NVARCHAR(20) NOT NULL DEFAULT 'Unpaid',
    PaymentMethod NVARCHAR(50),
    PaidAmount DECIMAL(10,2) DEFAULT 0.00,
    DueAmount AS (TotalAmount - PaidAmount) PERSISTED,
    CreatedBy INT,
    CONSTRAINT CK_Bills_Reference CHECK (
        (AppointmentID IS NOT NULL AND AdmissionID IS NULL)
        OR (AppointmentID IS NULL AND AdmissionID IS NOT NULL)
    ),
    CONSTRAINT CK_Bills_PaymentStatus CHECK (PaymentStatus IN ('Unpaid', 'PartiallyPaid', 'Paid')),
    CONSTRAINT FK_Bills_Appointment FOREIGN KEY (AppointmentID) REFERENCES Appointments(AppointmentID),
    CONSTRAINT FK_Bills_Admission FOREIGN KEY (AdmissionID) REFERENCES Admissions(AdmissionID),
    CONSTRAINT FK_Bills_CreatedBy FOREIGN KEY (CreatedBy) REFERENCES Users(UserID)
);
CREATE TABLE BillItems (
    BillItemID INT IDENTITY(1,1) PRIMARY KEY,
    BillID INT NOT NULL,
    ServiceType NVARCHAR(50) NOT NULL,
    Description NVARCHAR(200) NOT NULL,
    Quantity INT NOT NULL DEFAULT 1,
    UnitPrice DECIMAL(10,2) NOT NULL,
    Amount AS (Quantity * UnitPrice) PERSISTED,
    MedicineID INT,
    TestID INT,
    CONSTRAINT FK_BillItems_Bill FOREIGN KEY (BillID) REFERENCES Bills(BillID) ON DELETE CASCADE,
    CONSTRAINT FK_BillItems_Medicine FOREIGN KEY (MedicineID) REFERENCES Medicines(MedicineID),
    CONSTRAINT FK_BillItems_Test FOREIGN KEY (TestID) REFERENCES MedicalTests(TestID),
    CONSTRAINT CK_BillItems_Quantity CHECK (Quantity > 0),
    CONSTRAINT CK_BillItems_UnitPrice CHECK (UnitPrice >= 0)
);

CREATE TABLE InventoryTransactions (
    TransactionID INT IDENTITY(1,1) PRIMARY KEY,
    MedicineID INT NOT NULL,
    TransactionType NVARCHAR(20) NOT NULL,
    Quantity INT NOT NULL,
    UnitCost DECIMAL(10,2),
    TotalCost AS (Quantity * UnitCost) PERSISTED,
    TransactionDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    ReferenceNumber NVARCHAR(50),
    Supplier NVARCHAR(200),
    ExpiryDate DATE,
    BatchNumber NVARCHAR(50),
    PerformedBy INT,
    Reason NVARCHAR(500),
    CONSTRAINT FK_InventoryTrans_Medicine FOREIGN KEY (MedicineID) REFERENCES Medicines(MedicineID) ON DELETE CASCADE,
    CONSTRAINT FK_InventoryTrans_User FOREIGN KEY (PerformedBy) REFERENCES Users(UserID) ON DELETE SET NULL,
    CONSTRAINT CK_InventoryTrans_Type CHECK (TransactionType IN ('Purchase', 'Sale', 'Adjustment', 'Wastage', 'Return', 'Transfer')),
    CONSTRAINT CK_InventoryTrans_Quantity CHECK (
        (TransactionType IN ('Purchase', 'Return') AND Quantity > 0) OR
        (TransactionType IN ('Sale', 'Wastage', 'Adjustment') AND Quantity != 0)
    )
);


CREATE TABLE ActivityLog (
    LogID INT IDENTITY(1,1) PRIMARY KEY,
    UserID INT,
    ActivityType NVARCHAR(50) NOT NULL,
    TableName NVARCHAR(50),
    RecordID INT,
    Action NVARCHAR(20) NOT NULL,
    Description NVARCHAR(1000),
    LogDate DATETIME2 NOT NULL DEFAULT GETDATE(),
    CONSTRAINT FK_ActivityLog_User FOREIGN KEY (UserID) REFERENCES Users(UserID),
    CONSTRAINT CK_ActivityLog_Action CHECK (Action IN ('INSERT', 'UPDATE', 'DELETE'))
);
CREATE VIEW vw_RoomOccupancy AS
SELECT 
    r.RoomID,
    r.RoomNumber,
    r.RoomType,
    d.DepartmentName,
    r.Capacity,
    r.CurrentOccupancy,
    (r.Capacity - r.CurrentOccupancy) AS AvailableBeds,
    CAST(
        CASE 
            WHEN r.Capacity = 0 THEN 0 
            ELSE (r.CurrentOccupancy * 100.0 / r.Capacity) 
        END AS DECIMAL(5,2)
    ) AS OccupancyRate,
    r.DailyRate
FROM Rooms r
LEFT JOIN Departments d ON r.DepartmentID = d.DepartmentID
WHERE r.IsActive = 1;

CREATE VIEW vw_DoctorAppointmentsEnhanced AS
WITH StatusValues AS (
    SELECT 
        (SELECT StatusID FROM AppointmentStatuses WHERE StatusName = 'Completed') AS CompletedStatus,
        (SELECT StatusID FROM AppointmentStatuses WHERE StatusName = 'Scheduled') AS ScheduledStatus
)
SELECT 
    d.DoctorID,
    u.FirstName,
    u.LastName,
    u.FirstName + ' ' + u.LastName AS DoctorName,
    s.Name AS Specialization,
    COUNT(a.AppointmentID) AS TotalAppointments,
    SUM(CASE WHEN a.StatusID = sv.CompletedStatus THEN 1 ELSE 0 END) AS CompletedAppointments,
    SUM(CASE WHEN a.StatusID = sv.ScheduledStatus 
             AND a.AppointmentDate >= CAST(GETDATE() AS DATE) THEN 1 ELSE 0 END) AS UpcomingAppointments
FROM Doctors d
JOIN Users u ON d.UserID = u.UserID
JOIN Specializations s ON d.SpecializationID = s.SpecializationID
CROSS JOIN StatusValues sv
LEFT JOIN Appointments a ON d.DoctorID = a.DoctorID
GROUP BY 
    d.DoctorID, 
    u.FirstName, 
    u.LastName, 
    s.Name;
CREATE VIEW vw_PatientBilling AS
SELECT 
    p.PatientID,
    CONCAT(p.FirstName, ' ', p.LastName) AS PatientName,
    p.PatientCode,
    COUNT(b.BillID) AS TotalBills,
    ISNULL(SUM(b.TotalAmount), 0) AS TotalCharges,
    ISNULL(SUM(b.PaidAmount), 0) AS TotalPaid,
    ISNULL(SUM(b.DueAmount), 0) AS TotalDue
FROM Patients p
LEFT JOIN Bills b ON p.PatientID = b.PatientID
GROUP BY p.PatientID, p.FirstName, p.LastName, p.PatientCode;


--STUDY CONTINU IDR SAY

CREATE PROCEDURE sp_GetDoctorSchedule
    @DoctorID INT,
    @StartDate DATE,
    @EndDate DATE
AS
BEGIN
    SELECT 
        a.AppointmentID,
        a.AppointmentDate,
        a.AppointmentTime,
        p.PatientID,
        p.FirstName + ' ' + p.LastName AS PatientName,
        s.StatusName,
        a.Notes
    FROM Appointments a
    JOIN Patients p ON a.PatientID = p.PatientID
    JOIN AppointmentStatuses s ON a.StatusID = s.StatusID
    WHERE a.DoctorID = @DoctorID
        AND a.AppointmentDate BETWEEN @StartDate AND @EndDate
    ORDER BY a.AppointmentDate, a.AppointmentTime;
END;
CREATE OR ALTER PROCEDURE sp_RecordPayment
    @BillID INT,
    @Amount DECIMAL(10,2),
    @PaymentMethod NVARCHAR(50),
    @ReceivedBy INT
AS
BEGIN
    BEGIN TRY
        BEGIN TRANSACTION;
        
        DECLARE @CurrentPaid DECIMAL(10,2);
        DECLARE @TotalAmount DECIMAL(10,2);
        DECLARE @ErrorMessage NVARCHAR(4000);
        
        -- Check if bill exists
        IF NOT EXISTS (SELECT 1 FROM Bills WHERE BillID = @BillID)
        BEGIN
            SET @ErrorMessage = CONCAT('Bill with ID ', @BillID, ' does not exist');
            RAISERROR(@ErrorMessage, 16, 1);
            RETURN;
        END
        
        -- Get current payment status
        SELECT 
            @CurrentPaid = PaidAmount,
            @TotalAmount = TotalAmount
        FROM Bills
        WHERE BillID = @BillID;
        
        -- Validate payment amount
        IF (@CurrentPaid + @Amount) > @TotalAmount
        BEGIN
            SET @ErrorMessage = CONCAT('Payment amount $', CAST(@Amount AS NVARCHAR(20)), 
                             ' exceeds bill total. Current paid: $', CAST(@CurrentPaid AS NVARCHAR(20)), 
                             ', Bill total: $', CAST(@TotalAmount AS NVARCHAR(20)));
            RAISERROR(@ErrorMessage, 16, 1);
            RETURN;
        END
        
        -- Update bill payment
        UPDATE Bills
        SET 
            PaidAmount = PaidAmount + @Amount,
            PaymentStatus = CASE 
                WHEN (PaidAmount + @Amount) = TotalAmount THEN 'Paid'
                WHEN (PaidAmount + @Amount) > 0 THEN 'PartiallyPaid'
                ELSE 'Unpaid'
            END,
            PaymentMethod = @PaymentMethod
        WHERE BillID = @BillID;
        
        -- Log payment activity
        INSERT INTO ActivityLog (
            UserID,
            ActivityType,
            TableName,
            RecordID,
            Action,
            Description
        )
        VALUES (
            @ReceivedBy,
            'Payment',
            'Bills',
            @BillID,
            'UPDATE',
            CONCAT('Amount: $', CAST(@Amount AS NVARCHAR(20)), 
                  ', Method: ', @PaymentMethod, 
                  ', New PaidAmount: $', CAST((@CurrentPaid + @Amount) AS NVARCHAR(20)), 
                  ', New Status: ', CASE 
                                      WHEN (@CurrentPaid + @Amount) = @TotalAmount THEN 'Paid'
                                      WHEN (@CurrentPaid + @Amount) > 0 THEN 'PartiallyPaid'
                                      ELSE 'Unpaid'
                                    END)
        );
        
        COMMIT TRANSACTION;
        
        SELECT 'Payment recorded successfully' AS Message;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0
            ROLLBACK TRANSACTION;
            
        -- Return detailed error information
        SELECT 
            ERROR_MESSAGE() AS ErrorMessage,
            ERROR_NUMBER() AS ErrorNumber,
            ERROR_SEVERITY() AS ErrorSeverity,
            ERROR_STATE() AS ErrorState,
            ERROR_PROCEDURE() AS ErrorProcedure,
            ERROR_LINE() AS ErrorLine;
    END CATCH
END;
CREATE OR ALTER TRIGGER tr_UpdateRoomOccupancy
ON Admissions
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    -- Update CurrentOccupancy of each affected room
    UPDATE r
    SET r.CurrentOccupancy = updatedCounts.ActiveAdmissions
    FROM Rooms r
    INNER JOIN (
        SELECT 
            i.RoomID,
            COUNT(*) AS ActiveAdmissions
        FROM inserted i
        INNER JOIN Admissions a ON a.RoomID = i.RoomID
        WHERE a.CurrentStatus = 'Active'
        GROUP BY i.RoomID
    ) AS updatedCounts
    ON r.RoomID = updatedCounts.RoomID;
END;
INSERT INTO AppointmentStatuses (StatusName, Description) VALUES 
('Scheduled', 'Appointment is booked'),
('Completed', 'Appointment was completed'),
('Cancelled', 'Appointment was cancelled'),
('No Show', 'Patient did not arrive');

INSERT INTO MedicineCategories (CategoryName, Description) VALUES
('Antibiotics', 'Medications that fight bacterial infections'),
('Analgesics', 'Pain relieving medications'),
('Antipyretics', 'Fever reducing medications'),
('Antihistamines', 'Allergy medications');

-- Sample user data
INSERT INTO Users (Username, PasswordHash, FirstName, LastName, Email, PhoneNumber, Role) VALUES
('admin', 'admin-1234', 'System', 'Admin', 'admin@hospital.com', '1234567890', 'Admin'),
('dr.smith', 'am-2476', 'Aimen', 'Munir', 'aimenmunir001@gmail.com', '1234567891', 'Doctor'),
('nurse.jones', 'f047-nb', 'faryal', 'nayyar', 'faryal123@gmail.com', '1234567892', 'Nurse');

-- Sample specialization data
INSERT INTO Specializations (Name, Description) VALUES
('Cardiology', 'Heart and cardiovascular system'),
('Neurology', 'Brain and nervous system'),
('General Practice', 'Primary care physician');

-- Sample department data
INSERT INTO Departments (DepartmentName, Description, Location) VALUES
('Cardiology', 'Heart care unit', 'Building A, Floor 2'),
('Emergency', 'Emergency services', 'Building A, Floor 1'),
('Pharmacy', 'Medication dispensing', 'Building B, Floor 1');

-- Sample room data
INSERT INTO Rooms (RoomNumber, RoomType, DepartmentID, Capacity, DailyRate) VALUES
('101', 'General', 1, 2, 100.00),
('201', 'Private', 1, 1, 200.00),
('ER1', 'Emergency', 2, 1, 150.00);
UPDATE Users
SET 
   
    PasswordHash = 'admin-1234'
WHERE Username = 'admin';
UPDATE Users
SET 
    Username = 'aimenmnr',
    PasswordHash = 'am2476'
WHERE Username = 'dr.smith';

UPDATE Users
SET 
    Username = 'faryaln',
    PasswordHash = 'f047-nb'
WHERE Username = 'nurse.jones';

-- Database creation complete
PRINT 'Database for Adults and Adolescents Medicines Clinic,PLLC, Memphis. created successfully';
