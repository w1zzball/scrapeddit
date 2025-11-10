# Scrapeddit

A small interactive Reddit scraper that stores submissions and comments in a PostgreSQL
database. Use the interactive prompt to run scraping commands, execute SQL, or delete
rows from the DB.

## Features

- Scrape a single submission, comment, or entire thread (submission + comments).
- Scrape many submissions from a subreddit with optional comment scraping and
	concurrency.
- Store scraped data in PostgreSQL (two schemas/tables: `submissions` and `comments`).
- Interactive prompt with history, autocompletion and a `help` command describing
	flags and usage.
- run_batch script to run multiple scrape commands from a text file/CLI.
## Commands

All commands are run inside the interactive prompt (`py main.py`).

- scrape thread <id|url> [flags]
	- Scrape a submission and all comments.
	- Flags:
		- --limit N           Limit for fetching comments (replace_more). Use `None` for
													no limit.
		- --threshold N       replace_more threshold (default 0).
		- --overwrite, -o     Update existing rows on conflict.
		- --exit-after        Exit the interactive prompt after the scrape completes.

- scrape submission <id|url> [--overwrite|-o]
	- Scrape only the submission (no comments).
	- Flags:
		- --overwrite, -o     Update existing rows on conflict.
		- --exit-after        Exit the interactive prompt after the scrape completes.

- scrape comment <comment_id> [--overwrite|-o]
	- Scrape a single comment by ID.
	- Flags:
		- --overwrite, -o     Update existing rows on conflict.
		- --exit-after        Exit the interactive prompt after the scrape completes.

- scrape subreddit <name> [flags]
	- Scrape many submissions from a subreddit.
	- Flags:
		- --sort <new|hot|top|rising|controversial> (default: new)
		- --limit N           Number of submissions to fetch (default 10 when omitted).
		- --subs-only         Insert only submissions, skip comment scraping.
		- --max-workers N, -w Concurrency level for comment scraping (default 5).
		- --overwrite, -o     Update existing rows on conflict.
		- --skip-existing, -s Skip submissions already present in DB.
		- --exit-after        Exit the interactive prompt after the scrape completes.

- delete <submissions|comments|all>
	- Delete rows from one or both tables. This command prompts for a confirmation
		string (`Yes`) before running. Note: this removes rows, it does not drop tables.

- db <SQL>
	- Execute a SQL statement directly against the configured database.

- help [command]
	- Show usage and flags for a command; e.g. `help scrape` or `help scrape subreddit`.

- exit / quit
	- Exit the interactive prompt.

## Examples

Start the prompt:

```bash
py main.py
```

Scrape an entire thread by URL:

```text
scrapeddit> scrape thread https://reddit.com/r/python/comments/abcd1234 --overwrite
```

Scrape the top 20 submissions from r/python and only insert submissions (no comments):

```text
scrapeddit> scrape subreddit python --sort top --limit 20 --subs-only
```

Delete all comments (destructive):

```text
scrapeddit> delete comments
Type 'Yes' to confirm deletion (THIS CANNOT BE UNDONE): Yes
```

Run a quick SQL query:

```text
scrapeddit> db SELECT count(*) FROM reddit.submissions;
```

## Environment (.env)

Create a `.env` file at the repository root with the following variables (example):

```ini
USERNAME=your_reddit_username
PASSWORD=your_reddit_password
CLIENT_ID=your_reddit_app_client_id
SECRET_KEY=your_reddit_app_client_secret
USER_AGENT=your_app_user_agent
DB_STRING=postgresql://user:pass@host:5432/dbname
```

- `DB_STRING` should be a valid PostgreSQL connection string used by `psycopg`.
- The app expects the `.env` file in the repo root; it will raise if it cannot be found.

## Requirements

See `requirements.txt` for exact pins. At minimum this project uses:

- Python 3.10+
- praw
- prompt_toolkit
- psycopg
- python-dotenv
- rich

Install dependencies via:

```bash
py -m pip install -r requirements.txt
```

## Notes

- The prompt stores history in `.scrapeddit_history` in the project directory (or
	in the user's home dir if the project directory isn't writable).
- The `delete` command only deletes rows (does not drop tables or schemas).
- Be careful with `db <SQL>`; it runs whatever SQL you provide against the configured DB.

## DB schema

The project expects a PostgreSQL schema named `reddit` with two tables: `submissions`
and `comments`. Below is a minimal schema that matches how the code inserts and
queries rows. Adjust types and constraints as needed for your deployment.

```sql
CREATE TABLE comments (
    name TEXT PRIMARY KEY,             
    author TEXT,                       
    body TEXT,                         
    created_utc TIMESTAMPTZ NOT NULL, 
    edited BOOLEAN DEFAULT FALSE,      
    ups INT DEFAULT 0,                 
    parent_id TEXT,                    
    submission_id TEXT NOT NULL,       
    subreddit TEXT NOT NULL           
    )
    
    
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
```

Notes:

- The code uses `ON CONFLICT (name)` clauses when inserting, so `name` must be a
	unique key (PRIMARY KEY is suitable).
- `submission_id` in `comments` is stored as the reddit full id (e.g. `t3_<id>`)
	and is used to select comments for a submission in some queries.
