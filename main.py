import argparse
from datetime import datetime, timezone
from dotenv import load_dotenv, find_dotenv
import os
import praw
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.application import get_app
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import NestedCompleter
import psycopg
from rich.console import Console
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
import shlex
import shutil
import textwrap
from typing import Any
import time


console = Console()


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
            cur.execute("SET search_path TO reddit;")
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
            cur.execute("SET search_path TO reddit;")
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
        with console.status("Fetching comments...", spinner="dots"):
            comments.replace_more(limit=limit, threshold=threshold)
        return comments.list()

    def format_comment(self, comment: Any) -> dict[str, str | int | float | bool]:
        formatted_comment = {
            "name": getattr(comment, "name", None),
            "author": format(getattr(comment, "author", None)),
            "body": getattr(comment, "body", None),
            "created_utc": datetime.fromtimestamp(
                getattr(comment, "created_utc", 0), tz=timezone.utc
            ),
            "edited": bool(getattr(comment, "edited", None)),
            "ups": getattr(comment, "ups", None),
            "parent_id": getattr(comment, "parent_id", None),
            "submission_id": (
                getattr(comment, "link_id", None)
                or getattr(getattr(comment, "submission", None), "id", None)
                or format(getattr(comment, "submission", None))
            ),
            "subreddit": getattr(comment, "subreddit_name_prefixed", None),
        }
        return formatted_comment

    def scrape_comments_in_thread(
        self,
        post_id=None,
        post_url=None,
        limit: int | None = None,
        threshold=0,
        overwrite: bool = False,
    ):
        """Scrape all comments in a thread and insert into DB.

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
            cur.execute("SET search_path TO reddit;")
            inserted = 0
            skipped = 0
            with Progress(
                TextColumn("{task.description}"),
                BarColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("Inserting comments", total=total)
                for comment in comments:
                    formatted_comment = self.format_comment(comment)
                    cur.execute(
                        f"""
                INSERT INTO comments {cols}
                VALUES ({placeholders})
                {conflict_clause}
                """,
                        list(formatted_comment.values()),
                    )
                    result = cur.fetchone()
                    if result:
                        inserted += 1
                    else:
                        skipped += 1
                    progress.advance(task)
        if overwrite:
            msg = (
                f"Fetched {total} comments — inserted/updated {inserted}, "
                f"skipped {skipped}."
            )
        else:
            msg = (
                f"Fetched {total} comments — inserted {inserted}, "
                f"skipped {skipped} (duplicates)."
            )
        console.print(msg)

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
    ):
        """Scrape submissions from a subreddit.

        - sort: one of 'new', 'hot', 'top', 'rising', 'controversial'
        - limit: number of submissions to fetch (None = PRAW default)
        - overwrite: if True, update existing submissions/threads
        - subs_only: if True, only store the submission row (no comments)

        Skips submissions already present in the DB unless overwrite is
        requested.
        """
        start_time = time.perf_counter()
        sub = self.reddit.subreddit(subreddit_name)
        sorter = sort.lower() if sort else "new"
        if sorter == "hot":
            iterator = sub.hot() if limit is None else sub.hot(limit=limit)
        elif sorter == "top":
            iterator = sub.top() if limit is None else sub.top(limit=limit)
        elif sorter == "rising":
            if limit is None:
                iterator = sub.rising()
            else:
                iterator = sub.rising(limit=limit)
        elif sorter == "controversial":
            if limit is None:
                iterator = sub.controversial()
            else:
                iterator = sub.controversial(limit=limit)
        else:
            iterator = sub.new() if limit is None else sub.new(limit=limit)

        processed = 0
        skipped = 0
        scraped = 0
        with self.conn.cursor() as cur:
            cur.execute("SET search_path TO reddit;")
            with console.status(
                f"Fetching submissions from r/{subreddit_name} ({sorter})...",
                spinner="dots",
            ):
                for index, submission in enumerate(iterator, 1):
                    processed += 1
                    sname = getattr(submission, "name", None)
                    cur.execute(
                        "SELECT 1 FROM submissions WHERE name = %s;",
                        (sname,),
                    )
                    exists = cur.fetchone() is not None
                    if exists and not overwrite:
                        skipped += 1
                        continue
                    if subs_only:
                        try:
                            self.scrape_submission(
                                post_id=submission.id,
                                overwrite=overwrite,
                                index=index,
                                total=limit,
                            )
                        except Exception as e:
                            console.print("Error scraping submission:")
                            console.print(sname)
                            console.print(str(e))
                            continue
                    else:
                        try:
                            self.scrape_entire_thread(
                                post_id=submission.id,
                                overwrite=overwrite,
                                index=index,
                                limit=limit,
                            )
                        except Exception as e:
                            console.print("Error scraping thread:")
                            console.print(sname)
                            console.print(str(e))
                            continue
                    scraped += 1

        # end of work for subreddit scraping
        elapsed = time.perf_counter() - start_time
        hrs = int(elapsed // 3600)
        mins = int((elapsed % 3600) // 60)
        secs = int(elapsed % 60)
        duration = f"{hrs:02d}:{mins:02d}:{secs:02d}"
        console.print(
            "r/"
            + subreddit_name
            + ": processed="
            + str(processed)
            + ", scraped="
            + str(scraped)
            + ", skipped="
            + str(skipped)
            + f" — took {duration}"
        )

    def db_execute(self, sql_str):
        with self.conn.cursor() as cur:
            try:
                cur.execute("SET search_path TO reddit;")
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
            cur.execute("SET search_path TO reddit;")
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
            "clear": {
                "submissions": None,
                "comments": None,
                "all": None,
            },
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

        if not tokens:
            return HTML(
                "Commands: <b>scrape</b>, <b>db</b>, <b>clear</b>, " "<b>exit</b>"
            )

        cmd = tokens[0].lower()

        if cmd == "scrape":
            # brief usage when only 'scrape' typed
            if len(tokens) == 1:
                base = (
                    "Usage: <b>scrape &lt;target&gt; &lt;id_or_url&gt;</b>"
                    " [--overwrite|-o] [--limit N] [--threshold N]"
                )
                try:
                    cols = get_app().output.get_size().columns
                except Exception:
                    cols = shutil.get_terminal_size().columns
                parts = textwrap.wrap(base, width=max(20, cols - 10))
                return HTML("<br/>".join(parts))

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
                    "--overwrite/-o"
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

            try:
                cols = get_app().output.get_size().columns
            except Exception:
                cols = shutil.get_terminal_size().columns
            wrapped = textwrap.wrap(s, width=max(20, cols - 10))
            return HTML("<br/>".join(wrapped))

        if cmd == "clear":
            # TODO get rid of this mess
            s = (
                "clear: remove rows from tables. Usage: clear "
                "&lt;submissions|comments|all&gt;. "
                "This prompts for confirmation."
            )
            try:
                cols = get_app().output.get_size().columns
            except Exception:
                cols = shutil.get_terminal_size().columns
            wrapped = textwrap.wrap(s, width=max(20, cols - 10))
            return HTML("<br/>".join(wrapped))

        if cmd == "db":
            return HTML("<b>db &lt;SQL&gt;</b>: run SQL against DB")

        return HTML("Unknown command. Try <b>scrape</b>, <b>db</b> or " "<b>exit</b>")

    while True:
        try:
            user_input = session.prompt(
                "scrapeddit> ", bottom_toolbar=bottom_toolbar
            ).strip()
            if not user_input:
                continue
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
                        "[--overwrite] [--limit N] [--threshold N]"
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
                try:
                    ns, unknown = parser.parse_known_args(flags)
                except Exception as e:
                    print("Error parsing flags:", e)
                    continue
                overwrite = bool(ns.overwrite)
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
                # support clear command: handled below
                # thread synonyms
                # TODO clear up limit handling here and above
                if target in ("thread", "t", "entire", "entire_thread"):
                    if arg.startswith("http"):
                        bot.scrape_entire_thread(
                            post_url=arg,
                            limit=limit,
                            threshold=threshold,
                            overwrite=overwrite,
                        )
                    else:
                        bot.scrape_entire_thread(
                            post_id=arg,
                            limit=limit,
                            threshold=threshold,
                            overwrite=overwrite,
                        )
                # submission synonyms
                elif target in ("submission", "post", "s"):
                    if arg.startswith("http"):
                        bot.scrape_submission(
                            post_url=arg,
                            overwrite=overwrite,
                        )
                    else:
                        bot.scrape_submission(
                            post_id=arg,
                            overwrite=overwrite,
                        )
                # comment
                elif target in ("comment", "c"):
                    bot.scrape_comment(arg, overwrite=overwrite)
                # subreddit (collection of submissions)
                elif target in ("subreddit", "r"):
                    # arg should be subreddit name, e.g. 'python' or 'r/python'
                    bot.scrape_subreddit(
                        arg,
                        sort=sort,
                        limit=limit,
                        overwrite=overwrite,
                        subs_only=subs_only,
                    )
                else:
                    print("Unknown target; use thread, submission or comment.")
            # clear command
            elif user_input.startswith("clear ") or user_input == "clear":
                tokens = shlex.split(user_input)
                if len(tokens) < 2:
                    print("Usage: clear <submissions|comments|all>")
                    continue
                target = tokens[1].lower()
                if target in ("subs", "submission", "submissions"):
                    target = "submissions"
                elif target in ("c", "comment", "comments"):
                    target = "comments"
                elif target == "all":
                    target = "all"
                else:
                    print("Unknown clear target. Use submissions, " "comments or all.")
                    continue
                confirm = session.prompt(
                    "Type 'Yes' to confirm deletion (THIS CANNOT BE UNDONE): "
                ).strip()
                if confirm != "Yes":
                    print("Aborted: confirmation not provided.")
                    continue
                subs_del, comm_del = bot.clear_tables(target)
                console.print(
                    f"Cleared: submissions={subs_del}, " f"comments={comm_del}"
                )
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
