CREATE TABLE comments (
    -- Fully-qualified Reddit ID, e.g. 't1_nn428xe'
    name TEXT PRIMARY KEY,
    author TEXT,
    body TEXT,
    created_utc TIMESTAMPTZ NOT NULL,
    edited BOOLEAN DEFAULT FALSE,
    ups INT DEFAULT 0,
    parent_id TEXT,
    submission_id TEXT NOT NULL,
    subreddit TEXT NOT NULL
);

CREATE TABLE submissions (
    name TEXT PRIMARY KEY,
    author TEXT,
    title TEXT,
    selftext TEXT,
    url TEXT,
    created_utc TIMESTAMPTZ NOT NULL,
    edited BOOLEAN DEFAULT FALSE,
    ups INT DEFAULT 0,
    subreddit TEXT NOT NULL,
    permalink TEXT NOT NULL
);
