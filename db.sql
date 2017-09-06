CREATE TABLE user (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    f_name TEXT,
    l_name TEXT,
    password TEXT,
    msisdn TEXT,
    PIN TEXT
);

CREATE TABLE contact (
    contact_id  INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    f_name  TEXT,
    l_name  TEXT,
    full_name   TEXT    NOT NULL,
    g_id    TEXT    NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(user_id)
);

CREATE TABLE contact_phone_number (
    contact_id  INTEGER NOT NULL,
    type    TEXT NOT NULL,
    number  TEXT NOT NULL,
    FOREIGN KEY(contact_id) REFERENCES contact(contact_id)
);

CREATE TABLE call (
    call_id INTEGER PRIMARY KEY,
    call_from TEXT NOT NULL,
    call_to TEXT NOT NULL,
    duration INTEGER DEFAULT NULL,
    status TEXT DEFAULT NULL,
    direction INTEGER NOT NULL,
    ts timestamp,
    parent_call_id INTEGER,
    FOREIGN KEY(parent_call_id) REFERENCES call(call_id)
);

CREATE TABLE twilio_call (
    call_sid TEXT PRIMARY KEY,
    account_sid TEXT NOT NULL,
    call_id INTEGER NOT NULL,
    FOREIGN KEY(call_id) REFERENCES call(call_id)
);

CREATE TABLE asterisk_call (
    call_uid TEXT PRIMARY KEY,
    context TEXT TEXt NOT NULL,
    call_id INTEGER NOT NULL,
    FOREIGN KEY(call_id) REFERENCES call(call_id)
);

CREATE TABLE user_auth_attempt (
    msisdn TEXT NOT NULL,
    call_id INTEGER NOT NULL,
    ts timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP,
    auth_code INTEGER NOT NULL,
    user_id INTEGER,
    FOREIGN KEY(call_id) REFERENCES call(call_id),
    FOREIGN KEY(user_id) REFERENCES user(user_id)
);

CREATE TABLE authenticated_call (
    user_id INTEGER NOT NULL,
    call_id INTEGER NOT NULL,
    FOREIGN KEY(user_id) REFERENCES user(user_id),
    FOREIGN KEY(call_id) REFERENCES call(call_id)
);

CREATE TABLE call_auth_msisdn (
    call_id INTEGER NOT NULL,
    msisdn TEXT NOT NULL,
    FOREIGN KEY(call_id) REFERENCES call(call_id)
);

CREATE TABLE user_auth_blacklist (
    msisdn TEXT NOT NULL,
    expiry timestamp NOT NULL
);

CREATE TABLE call_matched_contact (
    call_id INTEGER NOT NULL,
    contact_id INTEGER NOT NULL,
    selected INTEGER NULL,
    FOREIGN KEY(call_id) REFERENCES call(call_id),
    FOREIGN KEY(contact_id) REFERENCES contact(contact_id)
);
