-- LandGuard Full Operational Database Schema (Version 5.0)
-- Target: PostgreSQL / Neon (compatible with SQLite3 syntax where standard)
-- Supports all 10 table groups defined in LandGuard SRS v5.0 Section 14

-- 1. Identity, Roles and Sessions
CREATE TABLE IF NOT EXISTS roles (
    role_id VARCHAR(50) PRIMARY KEY,
    role_name VARCHAR(100) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(100) PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL REFERENCES roles(role_id),
    national_id VARCHAR(50),
    digital_identity_id VARCHAR(100),
    phone VARCHAR(50),
    division VARCHAR(100),
    district VARCHAR(100),
    upazila VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sessions (
    session_id VARCHAR(128) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    user_agent TEXT,
    ip_address VARCHAR(50)
);

-- 2. Parcels and Cadastral History
CREATE TABLE IF NOT EXISTS parcels (
    parcel_id VARCHAR(100) PRIMARY KEY,
    dag_plot_number VARCHAR(50) NOT NULL,
    khatian_number VARCHAR(50),
    mouza VARCHAR(100),
    jl_number VARCHAR(50),
    upazila VARCHAR(100),
    district VARCHAR(100),
    division VARCHAR(100),
    total_area_decimal NUMERIC(10, 2) NOT NULL,
    land_classification VARCHAR(100),
    cs_plot VARCHAR(50),
    sa_plot VARCHAR(50),
    rs_plot VARCHAR(50),
    bs_plot VARCHAR(50),
    provenance VARCHAR(100) DEFAULT 'SYNTHETIC_CADASTRAL_DATASET',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ownership_events (
    event_id VARCHAR(100) PRIMARY KEY,
    parcel_id VARCHAR(100) NOT NULL REFERENCES parcels(parcel_id),
    event_type VARCHAR(50) NOT NULL, -- CS_SURVEY, SA_SURVEY, RS_SURVEY, BS_MUTATION, CONVEYANCE_DEED
    record_date DATE,
    owner_name VARCHAR(255),
    owner_nid VARCHAR(50),
    area_decimal NUMERIC(10, 2),
    document_ref VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Deeds, Registrations, Mutations, and Tax Records
CREATE TABLE IF NOT EXISTS deeds (
    deed_id VARCHAR(100) PRIMARY KEY,
    deed_number VARCHAR(100) UNIQUE NOT NULL,
    sub_registry_office VARCHAR(100),
    execution_date DATE NOT NULL,
    dag_plot_number VARCHAR(50) NOT NULL,
    transferred_area_decimal NUMERIC(10, 2) NOT NULL,
    seller_nid VARCHAR(50) NOT NULL,
    buyer_nid VARCHAR(50) NOT NULL,
    consideration_bdt NUMERIC(15, 2),
    previous_deed_ref VARCHAR(100),
    is_synthetic BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS mutations (
    mutation_id VARCHAR(100) PRIMARY KEY,
    mutation_case_no VARCHAR(100) UNIQUE NOT NULL,
    parcel_id VARCHAR(100),
    dag_plot_number VARCHAR(50) NOT NULL,
    khatian_number VARCHAR(50),
    new_owner_id VARCHAR(50),
    transferred_area_decimal NUMERIC(10, 2),
    approval_date DATE,
    status VARCHAR(50) DEFAULT 'APPROVED',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tax_records (
    tax_id VARCHAR(100) PRIMARY KEY,
    parcel_id VARCHAR(100) NOT NULL REFERENCES parcels(parcel_id),
    holding_number VARCHAR(50),
    last_paid_year INT,
    annual_dues_bdt NUMERIC(10, 2),
    clearance_status VARCHAR(50) DEFAULT 'PAID',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Documents, Hashes, and Evidence Items
CREATE TABLE IF NOT EXISTS documents (
    document_id VARCHAR(100) PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    mime_type VARCHAR(100),
    byte_size BIGINT,
    sha256_hash VARCHAR(64) NOT NULL,
    uploaded_by VARCHAR(100) REFERENCES users(user_id),
    is_synthetic BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Verification Runs, Extracted Fields, and Findings
CREATE TABLE IF NOT EXISTS verification_runs (
    verification_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) REFERENCES users(user_id),
    document_id VARCHAR(100) REFERENCES documents(document_id),
    deed_number VARCHAR(100),
    dag_plot_number VARCHAR(50),
    transferred_area_decimal NUMERIC(10, 2),
    overall_status VARCHAR(50) NOT NULL,
    rule_engine_flagged BOOLEAN DEFAULT FALSE,
    ml_risk_score NUMERIC(5, 4),
    ml_risk_tier VARCHAR(50),
    recommended_action VARCHAR(100),
    sha256_report_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verification_findings (
    finding_id VARCHAR(100) PRIMARY KEY,
    verification_id VARCHAR(100) NOT NULL REFERENCES verification_runs(verification_id) ON DELETE CASCADE,
    finding_code VARCHAR(100) NOT NULL,
    category VARCHAR(50) NOT NULL,
    severity VARCHAR(50) NOT NULL,
    explanation TEXT NOT NULL,
    source_reference VARCHAR(255),
    statutory_reference VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 6. Citizen Complaints and Evidence
CREATE TABLE IF NOT EXISTS complaints (
    complaint_id VARCHAR(100) PRIMARY KEY,
    citizen_user_id VARCHAR(100) NOT NULL REFERENCES users(user_id),
    category VARCHAR(100) NOT NULL,
    dag_plot_number VARCHAR(50),
    deed_number VARCHAR(100),
    title VARCHAR(255) NOT NULL,
    narrative_description TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'SUBMITTED',
    is_expedited BOOLEAN DEFAULT FALSE,
    expedite_reason TEXT,
    expedite_status VARCHAR(50) DEFAULT 'NONE',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. Case Management, Notes, and Status History
CREATE TABLE IF NOT EXISTS cases (
    case_id VARCHAR(100) PRIMARY KEY,
    complaint_id VARCHAR(100) REFERENCES complaints(complaint_id),
    verification_id VARCHAR(100) REFERENCES verification_runs(verification_id),
    title VARCHAR(255) NOT NULL,
    dag_plot_number VARCHAR(50),
    deed_number VARCHAR(100),
    priority VARCHAR(50) DEFAULT 'HIGH', -- CRITICAL, HIGH, NORMAL, LOW
    status VARCHAR(50) DEFAULT 'OPEN', -- SUBMITTED, UNDER_REVIEW, AWAITING_INFORMATION, ESCALATED, RESOLVED, CLOSED, REOPENED
    assigned_officer_id VARCHAR(100) REFERENCES users(user_id),
    statutory_finding VARCHAR(100),
    ml_risk_score NUMERIC(5, 4),
    evidence_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS case_notes (
    note_id VARCHAR(100) PRIMARY KEY,
    case_id VARCHAR(100) NOT NULL REFERENCES cases(case_id) ON DELETE CASCADE,
    author_id VARCHAR(100) NOT NULL REFERENCES users(user_id),
    note_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 8. Notifications and Expedite Requests
CREATE TABLE IF NOT EXISTS notifications (
    notification_id VARCHAR(100) PRIMARY KEY,
    recipient_user_id VARCHAR(100) NOT NULL REFERENCES users(user_id),
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    link_url VARCHAR(255),
    is_read BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. Immutable Audit Events
CREATE TABLE IF NOT EXISTS audit_events (
    event_id VARCHAR(100) PRIMARY KEY,
    actor_id VARCHAR(100) NOT NULL,
    action_type VARCHAR(100) NOT NULL,
    target_entity VARCHAR(100) NOT NULL,
    target_id VARCHAR(100),
    details JSON,
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for high-throughput lookup
CREATE INDEX IF NOT EXISTS idx_parcels_dag ON parcels(dag_plot_number);
CREATE INDEX IF NOT EXISTS idx_deeds_dag ON deeds(dag_plot_number);
CREATE INDEX IF NOT EXISTS idx_deeds_number ON deeds(deed_number);
CREATE INDEX IF NOT EXISTS idx_mutations_dag ON mutations(dag_plot_number);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_complaints_citizen ON complaints(citizen_user_id);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_events(created_at);
