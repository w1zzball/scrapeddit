CREATE TABLE comments (
    name TEXT PRIMARY KEY,             -- Fully-qualified Reddit ID, e.g. 't1_nn428xe'
    author TEXT,                       -- Comment author username
    body TEXT,                         -- Plain text body
    created_utc TIMESTAMPTZ NOT NULL,  -- UTC timestamp of creation
    edited BOOLEAN DEFAULT FALSE,      -- Whether comment was edited
    ups INT DEFAULT 0,                 -- Upvotes (fuzzy)
    parent_id TEXT,                    -- e.g. 't3_1oohc4a' (post) or 't1_abcd123' (comment)
    submission_id TEXT NOT NULL,       -- Post ID (base36 or prefixed)
    subreddit TEXT NOT NULL           -- e.g. 'r/python'
    )
    
    
CREATE TABLE submissions (
    name TEXT PRIMARY KEY,               -- e.g. 't3_1oohc4a'
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