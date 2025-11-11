import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv, find_dotenv
import os
import praw
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.application import get_app
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import NestedCompleter
import psycopg
from rich.console import Console
import shlex
from typing import Any
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
import sys


# TODO add threshold flag
# TODO fix limit arg drilling and general mess regarding limit passing
def load_auth_data_from_env() -> dict[str, str | None]:
    env_path = find_dotenv()
    if not env_path:
        raise Exception(
            "failed to import environment variables,"
            " does a .env exist in repo top level?"
        )
    load_dotenv(env_path, override=True)

    return {
        "username": os.getenv("USERNAME"),
        "password": os.getenv("PASSWORD"),
        "client_id": os.getenv("CLIENT_ID"),
        # REDIRECT_URI = os.getenv("REDIRECT_URI")
        "client_secret": os.getenv("SECRET_KEY"),
        "user_agent": os.getenv("USER_AGENT"),
        "db_string": os.getenv("DB_STRING"),
    }


# TODO add logging
# TODO consider connection pooling with psycopg pool
class Bot:

    def __init__(
        self,
        *,
        username,
        password,
        client_id,
        client_secret,
        user_agent,
        db_string,
        database="reddit",
    ) -> None:
        # reddit API
        self.reddit = praw.Reddit(
            username=username,
            password=password,
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        # db connection
        self.conn = psycopg.connect(db_string)
        self.conn.autocommit = True
        # target schema
        self.database = database
        self.set_path_sql = psycopg.sql.SQL(f"SET search_path TO {self.database};")
        with self.conn.cursor() as cur:
            cur.execute("SELECT version();")
            db_version = cur.fetchone()
            if db_version:
                print(f"Connected to database, version: {db_version[0]}")
            else:
                print("Connected to database (version unknown)")

    def get_submission(
        self,
        post_id=None,
        post_url=None,
    ) -> Any:
        if post_id:
            submission = self.reddit.submission(post_id)
        elif post_url:
            submission = self.reddit.submission(post_url)
        else:
            raise Exception("provide either a post_id or post_url")
        return submission

    def format_submission(self, submission: Any) -> dict[str, str | int | float | bool]:
        formatted_submission = {
            "name": getattr(submission, "name", None),
            "author": format(getattr(submission, "author", None)),
            "title": getattr(submission, "title", None),
            "selftext": getattr(submission, "selftext", None),
            "url": getattr(submission, "url", None),
            "created_utc": datetime.fromtimestamp(
                getattr(submission, "created_utc", 0), tz=timezone.utc
            ),
            "edited": bool(getattr(submission, "edited", None)),
            "ups": getattr(submission, "ups", None),
            "subreddit": format(getattr(submission, "subreddit", None)),
            "permalink": format(getattr(submission, "permalink", None)),
        }
        return formatted_submission

    def scrape_submission(
        self,
        post_id=None,
        post_url=None,
        overwrite: bool = False,
        index=None,
        total: int | None = None,
    ):
        """Fetch a submission and insert it into the DB.

        If overwrite is True, existing rows will be updated on conflict.
        """
        submission = self.get_submission(post_id, post_url)
        formatted_submission = self.format_submission(submission)
        cols = (
            "(name, author, title, selftext, url, created_utc, "
            "edited, ups, subreddit, permalink)"
        )
        placeholders = "%s,%s,%s,%s,%s,%s,%s,%s,%s,%s"
        if overwrite:
            conflict_clause = (
                "ON CONFLICT (name) DO UPDATE SET "
                "author=EXCLUDED.author, "
                "title=EXCLUDED.title, "
                "selftext=EXCLUDED.selftext, "
                "url=EXCLUDED.url, "
                "created_utc=EXCLUDED.created_utc, "
                "edited=EXCLUDED.edited, "
                "ups=EXCLUDED.ups, "
                "subreddit=EXCLUDED.subreddit, "
                "permalink=EXCLUDED.permalink "
                "RETURNING name;"
            )
        else:
            conflict_clause = "ON CONFLICT (name) DO NOTHING RETURNING name;"

        with self.conn.cursor() as cur:
            cur.execute(self.set_path_sql)
            cur.execute(
                f"""
                INSERT INTO submissions {cols}
                VALUES ({placeholders})
                {conflict_clause}
                """,
                list(formatted_submission.values()),
            )
            res = cur.fetchone()
        if res:
            prefix = ""
            if index is not None and total is not None:
                prefix = f"[{index}/{total}] "
            elif index is not None:
                prefix = f"[{index}] "
            console.print(f"{prefix}Inserted/updated submission {res[0]}")
        else:
            console.print("No change to submission (conflict and skipped)")

    def get_comment(self, comment_id: str) -> Any:
        """
        Get a single comment by its ID.
        """
        comment = self.reddit.comment(comment_id)
        return comment

    def scrape_comment(self, comment_id: str, overwrite: bool = False):
        """
        Fetch a single comment and insert into DB.

        If overwrite=True update on conflict.
        """
        comment = self.get_comment(comment_id)
        formatted_comment = self.format_comment(comment)
        cols = (
            "(name, author, body, created_utc, edited, ups, "
            "parent_id, submission_id, subreddit)"
        )
        placeholders = "%s,%s,%s,%s,%s,%s,%s,%s,%s"
        if overwrite:
            conflict_clause = (
                "ON CONFLICT (name) DO UPDATE SET "
                "author=EXCLUDED.author, body=EXCLUDED.body, "
                "created_utc=EXCLUDED.created_utc, edited=EXCLUDED.edited, "
                "ups=EXCLUDED.ups, parent_id=EXCLUDED.parent_id, "
                "submission_id=EXCLUDED.submission_id, "
                "subreddit=EXCLUDED.subreddit RETURNING name;"
            )
        else:
            conflict_clause = "ON CONFLICT (name) DO NOTHING RETURNING name;"

        with self.conn.cursor() as cur:
            cur.execute(self.set_path_sql)
            cur.execute(
                f"""
                INSERT INTO comments {cols}
                VALUES ({placeholders})
                {conflict_clause}
                """,
                list(formatted_comment.values()),
            )
            res = cur.fetchone()
        if res:
            console.print(f"Inserted/updated comment {res[0]}")
        else:
            console.print("No change to comment (conflict and skipped)")

    def get_comments_in_thread(
        self,
        post_id=None,
        post_url=None,
        limit: int | None = None,
        threshold=0,
    ) -> list[Any]:
        """Get all comments in a thread, returns a CommentForest object."""
        submission = self.get_submission(post_id, post_url)
        comments = submission.comments
        # with console.status("Fetching comments...", spinner="dots"):
        comments.replace_more(limit=limit, threshold=threshold)
        return comments.list()

    def format_comment(
        self, comment: Any
    ) -> Any:  # dict[str, str | int | float | bool]:
        formatted_comment = (
            getattr(comment, "name", None),
            format(getattr(comment, "author", None)),
            getattr(comment, "body", None),
            datetime.fromtimestamp(getattr(comment, "created_utc", 0), tz=timezone.utc),
            bool(getattr(comment, "edited", None)),
            getattr(comment, "ups", None),
            getattr(comment, "parent_id", None),
            (
                getattr(comment, "link_id", None)
                or getattr(getattr(comment, "submission", None), "id", None)
                or format(getattr(comment, "submission", None))
            ),
            getattr(comment, "subreddit_name_prefixed", None),
        )
        return formatted_comment

    def scrape_comments_in_thread(
        self,
        post_id=None,
        post_url=None,
        limit: int | None = None,
        threshold=0,
        overwrite: bool = False,
    ):
        """Scrape all comments in a thread and insert/update into DB.

        If overwrite=True, existing comments will be updated.
        """
        comments = self.get_comments_in_thread(
            post_id=post_id,
            post_url=post_url,
            limit=limit,
            threshold=threshold,
        )
        total = len(comments)

        cols = (
            "(name, author, body, created_utc, edited, ups, "
            "parent_id, submission_id, subreddit)"
        )
        placeholders = "%s,%s,%s,%s,%s,%s,%s,%s,%s"

        with self.conn.cursor() as cur:
            cur.execute(self.set_path_sql)

            cur.execute(
                """
                SELECT name, COALESCE(edited, FALSE), COALESCE(ups, 0)
                FROM comments
                WHERE submission_id = %s;
                """,
                ("t3_" + str(post_id),),
            )
            existing = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

            formatted_comments = list(map(self.format_comment, comments))

            new_rows = []
            changed_rows = []

            for row in formatted_comments:
                (
                    name,
                    author,
                    body,
                    created_utc,
                    edited,
                    ups,
                    parent_id,
                    submission_id,
                    subreddit,
                ) = row

                # set defaults for comparison
                prev = existing.get(name)
                prev_edited = False
                prev_ups = 0
                if prev is not None:
                    prev_edited, prev_ups = prev

                if name not in existing:
                    new_rows.append(row)
                else:
                    if overwrite:
                        changed_rows.append(row)
                    else:
                        # update if edited changed from False to True,
                        # or ups changed by >=5
                        if bool(edited) and not bool(prev_edited):
                            changed_rows.append(row)
                        elif ups is not None and abs(ups - prev_ups) >= 5:
                            changed_rows.append(row)

            # insert new ones
            if new_rows:
                cur.executemany(
                    f"""
                    INSERT INTO comments {cols}
                    VALUES ({placeholders})
                    ON CONFLICT (name) DO NOTHING
                    """,
                    new_rows,
                )

            # update changed ones
            if changed_rows:
                # reorder params so name is last for WHERE clause
                update_params = [
                    (
                        c[1],  # author
                        c[2],  # body
                        c[3],  # created_utc
                        c[4],  # edited
                        c[5],  # ups
                        c[6],  # parent_id
                        c[7],  # submission_id
                        c[8],  # subreddit
                        c[0],  # name
                    )
                    for c in changed_rows
                ]
                cur.executemany(
                    """
                    UPDATE comments
                    SET author=%s, body=%s, created_utc=%s,
                        edited=%s, ups=%s, parent_id=%s,
                        submission_id=%s, subreddit=%s
                    WHERE name=%s;
                    """,
                    update_params,
                )

        # commit if necessary
        if not self.conn.autocommit:
            self.conn.commit()
        return (
            len(new_rows),
            len(changed_rows),
            total - len(changed_rows) - len(new_rows),
        )

    def scrape_entire_thread(
        self,
        post_id=None,
        post_url=None,
        limit: int | None = None,
        threshold=0,
        overwrite: bool = False,
        index: int | None = None,
    ):
        with console.status("Scraping submission...", spinner="dots"):
            self.scrape_submission(
                post_id=post_id,
                post_url=post_url,
                overwrite=overwrite,
                index=index,
                total=limit,
            )
        with console.status("Scraping comments...", spinner="dots"):
            self.scrape_comments_in_thread(
                post_id=post_id,
                post_url=post_url,
                threshold=threshold,
                overwrite=overwrite,
            )

    def scrape_subreddit(
        self,
        subreddit_name: str,
        sort: str = "new",
        limit: int | None = 10,
        overwrite: bool = False,
        subs_only: bool = False,
        max_workers: int = 5,  # set to respect rate limits
        skip_existing: bool = False,
    ):
        start_time = time.perf_counter()
        sub = self.reddit.subreddit(subreddit_name)
        sorter = sort.lower()
        fetchers = {
            "new": sub.new,
            "hot": sub.hot,
            "top": sub.top,
            "rising": sub.rising,
            "controversial": sub.controversial,
        }
        iterator = fetchers.get(sorter, sub.new)(limit=limit)
        with console.status(
            f"Fetching submissions from r/{subreddit_name}...", spinner="dots"
        ):
            submissions = list(iterator)
        if not submissions:
            console.print("No submissions found.")
            return
        skipped_count = 0
        if skip_existing:
            # filter out existing submissions
            with self.conn.cursor() as cur:
                cur.execute(self.set_path_sql)
                cur.execute(
                    """
                    SELECT name FROM submissions
                    WHERE name = ANY(%s);
                    """,
                    ([s.name for s in submissions],),
                )
                existing = {r[0] for r in cur.fetchall()}
            before_count = len(submissions)
            submissions = [s for s in submissions if s.name not in existing]
            skipped_count = before_count - len(submissions)
            if skipped_count > 0:
                console.print(f"Skipped {skipped_count} existing submissions.")

        # formatted submissions batch
        formatted_rows = [
            tuple(self.format_submission(s).values()) for s in submissions
        ]
        cols = [
            "name",
            "author",
            "title",
            "selftext",
            "url",
            "created_utc",
            "edited",
            "ups",
            "subreddit",
            "permalink",
        ]
        placeholders = ", ".join(["%s"] * len(cols))
        sql_stmt = f"""
            INSERT INTO submissions ({', '.join(cols)})
            VALUES ({placeholders})
            {'ON CONFLICT (name) DO NOTHING' if not overwrite else
            'ON CONFLICT (name) DO UPDATE SET author=EXCLUDED.author, title=EXCLUDED.title'}
        """

        with self.conn.cursor() as cur:
            cur.execute(self.set_path_sql)
            cur.executemany(sql_stmt, formatted_rows)
        self.conn.commit()

        console.print(f"Inserted {len(submissions)} submissions.")

        # threaded comment scraping
        if not subs_only:
            total_new = 0
            total_updated = 0
            total_skipped = 0
            submissions_scraped = 0
            total_errors = 0
            console.print(
                f"Fetching comments for {len(submissions)} threads (max {max_workers} workers)..."
            )

            def scrape_one(submission):
                """Worker: scrape and insert all comments for one submission.

                Always return a tuple (info_tuple, err) where info_tuple is
                (new, updated, skipped, submission_id).
                """
                try:
                    new, updated, skipped = self.scrape_comments_in_thread(
                        submission.id, overwrite=overwrite
                    )
                    return (new, updated, skipped, submission.id), None
                except Exception as e:
                    return (0, 0, 0, submission.id), str(e)

            # progress state for toolbar
            self._subreddit_progress = {
                "enabled": True,
                "current": 0,
                "total": len(submissions),
            }

            # rich progress bar for main scraping loop
            with Progress(
                "Scraping threads...",
                BarColumn(),
                TextColumn("{task.completed}/{task.total}"),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("comments", total=len(submissions))

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {
                        executor.submit(scrape_one, s): s.id for s in submissions
                    }
                    for future in as_completed(futures):
                        info, err = future.result()
                        # advance the rich progress bar and our shared state
                        progress.advance(task)
                        self._subreddit_progress["current"] += 1

                        if err:
                            total_errors += 1
                            console.print(f"[red]Error scraping {info[3]}: {err}[/red]")
                        else:
                            console.print(
                                f"[green]✔ {info[3]} done[/green] {info[0]} new, {info[1]} updated, {info[2]} skipped",
                            )
                            total_new += info[0]
                            total_updated += info[1]
                            total_skipped += info[2]
                            submissions_scraped += 1

            # disable the toolbar progress after scraping finishes
            self._subreddit_progress["enabled"] = False

        elapsed = time.perf_counter() - start_time
        total_ms = int(elapsed * 1000)
        hh = total_ms // 3600000
        rem = total_ms % 3600000
        mm = rem // 60000
        rem = rem % 60000
        ss = rem // 1000
        ms = rem % 1000
        elapsed_str = f"[green]{hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}[/green]"
        comment_summary = f" \nComments: [green]{total_new} new[/green], [yellow]{total_updated} updated[/yellow], [red]{total_skipped} skipped[/red]"
        error_summary = f"{'[red]' if total_errors > 0 else '[white]'}{total_errors} errors{'[/red]' if total_errors > 0 else '[/white]'}"
        # TODO change colour based on count as above
        console.print(
            f"\nDone in {elapsed_str}. with {error_summary}."
            f"\nSubmissions: [green]{submissions_scraped} scraped[/green], [red]{skipped_count} skipped[/red]."
            f"{comment_summary if submissions_scraped>0 else ''}",
            markup=True,
        )

    def db_execute(self, sql_str):
        with self.conn.cursor() as cur:
            try:
                cur.execute(self.set_path_sql)
                cur.execute(sql_str)
                # If the statement returned rows, fetch and print them.
                # Otherwise print how many rows were affected.
                if cur.description is not None:
                    rows = cur.fetchall()
                    console.print(rows)
                else:
                    console.print(f"Query OK, {cur.rowcount} rows affected.")
            except Exception as e:
                # Print a concise psycopg error message instead of
                # the full traceback.
                ename = f"{e.__class__.__module__}.{e.__class__.__name__}"
                console.print(f"{ename}: {e}")

    def clear_tables(self, target: str = "all") -> tuple[int, int]:
        """Delete rows from comments and/or submissions.

        target: 'comments', 'submissions', or 'all'. Returns a tuple of
        deleted counts (submissions_deleted, comments_deleted).
        This does NOT drop tables—only deletes rows.
        """
        submissions_deleted = 0
        comments_deleted = 0
        with self.conn.cursor() as cur:
            cur.execute(self.set_path_sql)
            if target in ("comments", "all"):
                cur.execute("DELETE FROM comments;")
                comments_deleted = cur.rowcount
            if target in ("submissions", "all"):
                cur.execute("DELETE FROM submissions;")
                submissions_deleted = cur.rowcount
        return submissions_deleted, comments_deleted


def main():
    auth_data = load_auth_data_from_env()
    bot = Bot(**auth_data)
    # Autocompletion for top-level commands and scrape targets.
    completer = NestedCompleter.from_nested_dict(
        {
            "scrape": {
                "thread": None,
                "submission": None,
                "comment": None,
                "subreddit": None,
                # short aliases
                "t": None,
                "s": None,
                "c": None,
                "r": None,
            },
            "delete": {
                "submissions": None,
                "comments": None,
                "all": None,
            },
            "help": None,
            "db": None,
            "exit": None,
            "quit": None,
        }
    )
    # create/load persistent prompt history in the project directory
    project_dir = os.path.dirname(os.path.abspath(__file__))
    history_file = os.path.join(project_dir, ".scrapeddit_history")
    # ensure the file exists (try project dir first, then fall back to
    # home, then CWD)
    try:
        open(history_file, "a", encoding="utf-8").close()
    except OSError:
        try:
            history_file = os.path.expanduser("~/.scrapeddit_history")
            open(history_file, "a", encoding="utf-8").close()
            console.print("Note: project dir not writable; using home dir")
        except OSError:
            history_file = ".scrapeddit_history"
            open(history_file, "a", encoding="utf-8").close()
            console.print(
                "Warning: could not create history in project or home; "
                "using CWD file."
            )

    history = FileHistory(history_file)
    session = PromptSession(history=history, completer=completer)

    def bottom_toolbar() -> HTML:
        """Return a small, fast context-sensitive help string for the
        bottom toolbar based on the current buffer contents.
        """
        buf = get_app().current_buffer
        txt = buf.document.text or ""
        try:
            tokens = shlex.split(txt)
        except ValueError:
            tokens = txt.split()

        # show subreddit scraping progress if active
        try:
            prog = getattr(bot, "_subreddit_progress", None)
            if prog and prog.get("enabled") and prog.get("total", 0) > 0:
                cur = int(prog.get("current", 0))
                tot = int(prog.get("total", 0))
                width = 30
                filled = int((cur / tot) * width) if tot else 0
                bar = "█" * filled + "─" * (width - filled)
                perc = int((cur / tot) * 100) if tot else 0
                return HTML(f"Scraping: {cur}/{tot} [{bar}] {perc}%")
        except Exception:
            # fail silently on any error
            pass

        if not tokens:
            return HTML(
                "Commands: <b>scrape</b>, <b>db</b>, " "<b>delete</b>, <b>exit</b>"
            )

        cmd = tokens[0].lower()

        if cmd == "scrape":
            # brief usage when only 'scrape' typed
            if len(tokens) == 1:
                base = (
                    "Usage: <b>scrape &lt;target&gt; &lt;id_or_url&gt;</b>"
                    " [--overwrite|-o] [--limit N] [--threshold N] [--max-workers N]"
                )
                return HTML(base)

            target = tokens[1].lower()
            if target in ("thread", "t", "entire", "entire_thread"):
                s = (
                    "thread: scrape submission + comments. Flags: "
                    "--overwrite/-o, --limit N (None=all), --threshold N"
                )
            elif target in ("subreddit", "r"):
                s = (
                    "subreddit: scrape many submissions "
                    "Flags: --sort (new|hot|top|rising|"
                    "controversial), --limit N (10), --subs-only, "
                    "--max-workers N (-w), --overwrite/-o [--skip-existing|-s]"
                )
            elif target in ("submission", "post", "s"):
                s = "submission: scrape only submission. Flags: --overwrite/-o"
            elif target in ("comment", "c"):
                s = "comment: scrape a single comment. Flags: --overwrite/-o"
            else:
                s = (
                    "Unknown scrape target. Use thread, submission, "
                    "comment or subreddit"
                )

            return HTML(s)

        if cmd == "delete":
            # quick help for delete command shown in bottom toolbar
            s = (
                "delete: remove rows from tables. Usage: delete "
                "&lt;submissions|comments|all&gt;. "
                "This prompts for confirmation."
            )
            return HTML(s)

        if cmd == "db":
            return HTML("<b>db &lt;SQL&gt;</b>: run SQL against DB")

        return HTML("Unknown command. Try <b>scrape</b>, <b>db</b> or " "<b>exit</b>")

    cli_input_executed = False
    while True:
        try:
            if len(sys.argv) < 2 or cli_input_executed:
                user_input = session.prompt(
                    "scrapeddit> ",
                    bottom_toolbar=bottom_toolbar,
                    auto_suggest=AutoSuggestFromHistory(),
                ).strip()
                if not user_input:
                    continue
            # help command: `help` or `help <command>` or `help scrape <target>`
            else:
                user_input = " ".join(sys.argv[1:]).strip()
                cli_input_executed = True
            if user_input.startswith("help"):
                tokens = shlex.split(user_input)

                # Determine help target: `help scrape subreddit` -> ('scrape','subreddit')
                if len(tokens) == 1:
                    s = (
                        "Commands:\n"
                        "  scrape <target> <id_or_url> [flags] - "
                        "scrape a thread/submission/comment/subreddit\n"
                        "  db <SQL> - run raw SQL against the DB\n"
                        "  delete <submissions|comments|all> - "
                        "delete rows from tables\n"
                        "  exit/quit - leave the prompt\n\n"
                        "Use `help <command>` for more details, e.g. `help scrape` or "
                        "`help delete`."
                    )
                    console.print(s)
                    continue

                # token 1 is either a top-level command or 'scrape'
                if tokens[1].lower() == "scrape":
                    # help for scrape or a specific scrape target
                    sub = tokens[2].lower() if len(tokens) > 2 else None
                    if sub in ("subreddit", "r"):
                        s = (
                            "scrape subreddit <name> [flags]: Scrape many submissions from a subreddit.\n"
                            "Flags:\n"
                            "  --sort <new|hot|top|rising|controversial>  (default: new)\n"
                            "  --limit N  (number of submissions to fetch; default 10)\n"
                            "  --subs-only  (only insert submissions, skip comments)\n"
                            "  --max-workers N, -w  (concurrency for comment scraping; default 5)\n"
                            "  --overwrite, -o  (update existing rows on conflict)\n"
                            "  --skip-existing, -s  (do not touch submissions already in DB)\n"
                        )
                    elif sub in ("thread", "t", "entire", "entire_thread"):
                        s = (
                            "scrape thread <id|url> [flags]: Scrape a submission and all its comments.\n"
                            "Flags:\n"
                            "  --limit N  (limit for fetching comments replace_more; None=all)\n"
                            "  --threshold N  (replace_more threshold; default 0)\n"
                            "  --overwrite, -o  (update existing rows on conflict)\n"
                        )
                    elif sub in ("submission", "post", "s"):
                        s = (
                            "scrape submission <id|url> [flags]: Scrape only the submission.\n"
                            "Flags:\n"
                            "  --overwrite, -o  (update existing rows on conflict)\n"
                        )
                    elif sub in ("comment", "c"):
                        s = (
                            "scrape comment <comment_id> [flags]: Scrape a single comment.\n"
                            "Flags:\n"
                            "  --overwrite, -o  (update existing rows on conflict)\n"
                        )
                    else:
                        s = (
                            "scrape <target> <id_or_url> [flags]\n"
                            "Common flags for scrape targets:\n"
                            "  --overwrite, -o  - Update existing rows on conflict.\n"
                            "  --limit N  - Integer limit (use 'None' for unlimited).\n"
                            "  --threshold N  - replace_more threshold when fetching comments.\n"
                            "  --sort <sorter>  - For subreddits: new|hot|top|rising|controversial.\n"
                            "  --subs-only  - For subreddits: skip comment scraping.\n"
                            "  --max-workers N, -w  - Concurrency for comment scraping.\n"
                            "  --skip-existing, -s  - Skip submissions already present in DB.\n"
                        )
                    console.print(s)
                    continue

                # help for other top-level commands
                t = tokens[1].lower()
                if t == "delete":
                    s = (
                        "delete <submissions|comments|all>: Remove rows from the "
                        "given tables.\n"
                        "  submissions - delete all submission rows.\n"
                        "  comments - delete all comment rows.\n"
                        "  all - delete rows from both tables.\n"
                        "This command will prompt for confirmation before deleting."
                    )
                    console.print(s)
                    continue

                if t == "db":
                    s = "db <SQL>: Execute a SQL statement against the configured DB. Use carefully."
                    console.print(s)
                    continue

                # fallback
                console.print("No help available for that command.")
                continue
            # end of help command

            # Support commands:
            #   scrape thread <id|url>
            #   scrape submission <id|url>
            #   scrape comment <comment_id>
            if user_input.startswith("scrape "):
                # allow flags after the id/url, e.g.:
                #   scrape thread <id|url> --overwrite --limit 0 --threshold 0
                tokens = shlex.split(user_input)
                if len(tokens) < 3:
                    print(
                        "Usage: scrape <target> <id_or_url> "
                        "[--overwrite] [--limit N] [--threshold N] [--skip-existing|-s]"
                    )
                    continue
                _, target = tokens[0], tokens[1]
                target = target.lower()
                arg = tokens[2]
                # defaults
                overwrite = False
                limit = None
                threshold = 0
                # parse remaining tokens as flags
                flags = tokens[3:]
                parser = argparse.ArgumentParser(add_help=False)
                parser.add_argument("-o", "--overwrite", action="store_true")
                parser.add_argument("--limit", type=str)
                parser.add_argument("--subs-only", action="store_true")
                parser.add_argument("--sort", type=str)
                parser.add_argument("--threshold", type=int)
                parser.add_argument("-w", "--max-workers", type=int)
                parser.add_argument(
                    "--exit-after", action="store_true", dest="exit_after"
                )
                parser.add_argument(
                    "-s", "--skip-existing", action="store_true", dest="skip_existing"
                )
                try:
                    ns, unknown = parser.parse_known_args(flags)
                except Exception as e:
                    print("Error parsing flags:", e)
                    continue
                overwrite = bool(ns.overwrite)
                exit_after = bool(getattr(ns, "exit_after", False))
                # limit arg may be 'None' or an integer
                if ns.limit is None:
                    limit = None
                else:
                    if ns.limit.lower() == "none":
                        limit = None
                    else:
                        try:
                            limit = int(ns.limit)
                        except ValueError:
                            print(f"Invalid limit value: {ns.limit}")
                            limit = None
                # If invoking scrape subreddit and no --limit provided, default to 10
                if target in ("subreddit", "r") and limit is None:
                    limit = 10
                threshold = ns.threshold if ns.threshold is not None else 0
                sort = ns.sort if ns.sort is not None else "new"
                subs_only = bool(getattr(ns, "subs_only", False))
                skip_existing = bool(getattr(ns, "skip_existing", False))
                max_workers = (
                    ns.max_workers
                    if getattr(ns, "max_workers", None) is not None
                    else 5
                )
                # support delete command: handled below
                # thread synonyms
                # TODO: clean up limit handling here and above
                if target in ("thread", "t", "entire", "entire_thread"):
                    if arg.startswith("http"):
                        bot.scrape_entire_thread(
                            post_url=arg,
                            limit=limit,
                            threshold=threshold,
                            overwrite=overwrite,
                        )
                    if exit_after:
                        break
                    else:
                        bot.scrape_entire_thread(
                            post_id=arg,
                            limit=limit,
                            threshold=threshold,
                            overwrite=overwrite,
                        )
                    if exit_after:
                        break
                # submission synonyms
                elif target in ("submission", "post", "s"):
                    if arg.startswith("http"):
                        bot.scrape_submission(
                            post_url=arg,
                            overwrite=overwrite,
                        )
                    if exit_after:
                        break
                    else:
                        bot.scrape_submission(
                            post_id=arg,
                            overwrite=overwrite,
                        )
                    if exit_after:
                        break
                # comment
                elif target in ("comment", "c"):
                    bot.scrape_comment(arg, overwrite=overwrite)
                    if exit_after:
                        break
                # subreddit (collection of submissions)
                elif target in ("subreddit", "r"):
                    # arg should be subreddit name, e.g. 'python' or 'r/python'
                    bot.scrape_subreddit(
                        arg,
                        sort=sort,
                        limit=limit,
                        overwrite=overwrite,
                        subs_only=subs_only,
                        max_workers=max_workers,
                        skip_existing=skip_existing,
                    )
                    if exit_after:
                        break
                else:
                    print("Unknown target; use thread, submission or comment.")
            # delete command
            elif user_input.startswith("delete ") or user_input == "delete":
                tokens = shlex.split(user_input)
                if len(tokens) < 2:
                    print("Usage: delete <submissions|comments|all>")
                    continue
                target = tokens[1].lower()
                if target in ("subs", "submission", "submissions"):
                    target = "submissions"
                elif target in ("c", "comment", "comments"):
                    target = "comments"
                elif target == "all":
                    target = "all"
                else:
                    print("Unknown delete target. Use submissions,")
                    print("comments or all.")
                    continue
                confirm = session.prompt(
                    "Type 'Yes' to confirm deletion (THIS CANNOT BE UNDONE): "
                ).strip()
                if confirm != "Yes":
                    print("Aborted: confirmation not provided.")
                    continue
                subs_del, comm_del = bot.clear_tables(target)
                console.print(f"Deleted: submissions={subs_del}, comments={comm_del}")
            elif user_input.startswith("db "):
                _, sql_str = user_input.split(" ", 1)
                bot.db_execute(sql_str)
            elif user_input in {"exit", "quit"}:
                break
            else:
                print("Unknown command. Try 'scrape', 'db', or 'exit'.")
        except KeyboardInterrupt:
            break
        except EOFError:
            break


if __name__ == "__main__":
    main()
