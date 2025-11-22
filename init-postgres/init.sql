CREATE TABLE general (
    id SERIAL PRIMARY KEY,
    timestamp BIGINT NOT NULL,
    source_mac VARCHAR NOT NULL,
    source_ip VARCHAR NOT NULL,
    value INTEGER DEFAULT 1,
    factor REAL,
    reading REAL,
    measurement REAL,
    metric INTEGER,
    data_field_index INTEGER
);

