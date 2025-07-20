CREATE TABLE general (
    id SERIAL PRIMARY KEY,
    timestamp BIGINT NOT NULL,
    source_mac VARCHAR NOT NULL,
    source_ip VARCHAR NOT NULL,
    source_name VARCHAR,
    value INTEGER DEFAULT 1,
    data_field_index INTEGER,
    product VARCHAR,
    zone VARCHAR,
    machine VARCHAR,
    machine_stage VARCHAR,
    event_type VARCHAR,
    units VARCHAR,
    pieces VARCHAR,
    estimated_pieces VARCHAR,
    rfid VARCHAR,
    dry_time_seconds VARCHAR
);

