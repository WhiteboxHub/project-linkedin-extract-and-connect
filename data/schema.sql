-- data/schema.sql
-- DuckDB Schema for LinkedIn Contact Extraction Bot (Phase 6)
-- This provides local analytics and querying alongside API storage

-- Sequences for auto-increment IDs
CREATE SEQUENCE IF NOT EXISTS seq_run_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_contact_id START 1;
CREATE SEQUENCE IF NOT EXISTS seq_failure_id START 1;

-- Extraction runs table
CREATE TABLE IF NOT EXISTS extraction_runs (
    run_id INTEGER PRIMARY KEY DEFAULT nextval('seq_run_id'),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    employee_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    username VARCHAR NOT NULL,
    threads_discovered INTEGER DEFAULT 0,
    threads_processed INTEGER DEFAULT 0,
    contacts_extracted INTEGER DEFAULT 0,
    contacts_inserted INTEGER DEFAULT 0,
    success_rate DOUBLE DEFAULT 0.0,
    insert_rate DOUBLE DEFAULT 0.0,
    error_rate DOUBLE DEFAULT 0.0,
    skipped_no_profile INTEGER DEFAULT 0,
    skipped_invalid_name INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    max_consecutive_errors INTEGER DEFAULT 0,
    rate_limit_delays INTEGER DEFAULT 0,
    error_recoveries INTEGER DEFAULT 0,
    duration_seconds DOUBLE DEFAULT 0.0,
    status VARCHAR DEFAULT 'running' -- running, completed, failed
);

-- Extracted contacts table
CREATE TABLE IF NOT EXISTS contacts (
    contact_id INTEGER PRIMARY KEY DEFAULT nextval('seq_contact_id'),
    run_id INTEGER NOT NULL,
    extracted_at TIMESTAMP NOT NULL,
    full_name VARCHAR NOT NULL,
    source_email VARCHAR NOT NULL,
    email VARCHAR,
    phone VARCHAR,
    linkedin_id VARCHAR,
    linkedin_internal_id VARCHAR,
    company_name VARCHAR,
    location VARCHAR,
    profile_url VARCHAR,
    job_source VARCHAR DEFAULT 'Bot Linkedin Message Extraction',
    inserted_to_api BOOLEAN DEFAULT FALSE,
    api_insert_at TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id)
);

-- Extraction failures table
CREATE TABLE IF NOT EXISTS extraction_failures (
    failure_id INTEGER PRIMARY KEY DEFAULT nextval('seq_failure_id'),
    run_id INTEGER NOT NULL,
    failed_at TIMESTAMP NOT NULL,
    thread_number INTEGER,
    failure_type VARCHAR NOT NULL, -- no_profile, invalid_name, extraction_error, api_error
    error_message TEXT,
    profile_url VARCHAR,
    FOREIGN KEY (run_id) REFERENCES extraction_runs(run_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_contacts_run_id ON contacts(run_id);
CREATE INDEX IF NOT EXISTS idx_contacts_linkedin_id ON contacts(linkedin_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_extracted_at ON contacts(extracted_at);
CREATE INDEX IF NOT EXISTS idx_failures_run_id ON extraction_failures(run_id);
CREATE INDEX IF NOT EXISTS idx_runs_started_at ON extraction_runs(started_at);
CREATE INDEX IF NOT EXISTS idx_runs_status ON extraction_runs(status);
