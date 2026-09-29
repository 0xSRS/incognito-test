CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL
);

CREATE TABLE user_gets (
    ugets_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    magic_link TEXT NOT NULL,
    magic_link_hash TEXT NOT NULL,
    encoding TEXT
);

CREATE TABLE user_flags (
    flag_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    flag TEXT NOT NULL,
    flag_hash TEXT,
    is_used BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE pastes (
    paste_id SERIAL PRIMARY KEY,
    flag_id INTEGER NOT NULL REFERENCES user_flags(flag_id),
    directory TEXT,
    encoded_str TEXT,
    encoding_type TEXT,
    pastebin_url TEXT
);


CREATE TABLE tickets (
    ticket_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    flag_id INTEGER NOT NULL REFERENCES user_flags(flag_id),
    jwt_token TEXT NOT NULL,
    qr_path TEXT,
    is_used BOOLEAN NOT NULL DEFAULT FALSE,
    issued_at TIMESTAMP NOT NULL DEFAULT NOW()
);