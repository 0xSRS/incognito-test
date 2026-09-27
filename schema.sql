CREATE TABLE users (
  user_id   SERIAL PRIMARY KEY,
  name      TEXT NOT NULL,
  email     TEXT UNIQUE NOT NULL
);

CREATE TABLE user_flags (
  flag_id   SERIAL PRIMARY KEY,
  user_id   INTEGER NOT NULL REFERENCES users(user_id),
  flag      TEXT NOT NULL
);

CREATE TABLE user_gets (
  ugets_id  SERIAL PRIMARY KEY,
  user_id   INTEGER NOT NULL REFERENCES users(user_id),
  magic_link TEXT NOT NULL
);

CREATE TABLE pastes (
  paste_id      SERIAL PRIMARY KEY,
  flag_id       INTEGER NOT NULL REFERENCES user_flags(flag_id),
  directory     TEXT UNIQUE,
  encoded_str   TEXT,
  encoding_type TEXT,
  gist_url      TEXT,
  active        BOOLEAN NOT NULL DEFAULT TRUE
);
