"""Help text for prompt commands."""

from utils.db_utils import clear_tables, db_execute
from utils.scraping_utils import (
    scrape_comment,
    scrape_entire_thread,
    scrape_submission,
    scrape_subreddit,
    scrape_redditor,
    expand_redditors_comments,
)

# TODO add exit-after flag help
# TODO add skip-existing flag help
prompt_data = {
    "scrape": {
        "base": {
            "targets": (),
            "desc": (
                "Usage: <b>scrape &lt;target&gt; &lt;id_or_url&gt;</b>\n"
                " [--overwrite|-o] [--limit N] "
                "[--threshold N] [--max-workers N]"
            ),
            "func": None,
        },
        "error": {
            "targets": (),
            "desc": (
                "Error: Invalid scrape command. "
                "Unknown scrape target. Use thread, submission, "
                "comment, redditor or subreddit"
            ),
            "func": None,
        },
        "thread": {
            "targets": ("thread", "t", "entire", "entire_thread"),
            "desc": (
                "thread: scrape submission + comments. Flags: \n"
                "--overwrite/-o, --limit N (None=all), --threshold N"
            ),
            "func": scrape_entire_thread,
        },
        "submission": {
            "targets": ("submission", "s", "post"),
            "desc": (
                "submission: scrape submission only. Flags:\n "
                "--overwrite/-o, --limit N (None=all), --threshold N"
            ),
            "func": scrape_submission,
        },
        "comment": {
            "targets": ("comment", "c"),
            "desc": (
                "comment: scrape single comment only. Flags:\n "
                "--overwrite/-o"
            ),
            "func": scrape_comment,
        },
        "redditor": {
            "targets": ("redditor", "user", "u"),
            "desc": (
                "redditor: scrape comments from a redditor. Flags:\n "
                "--overwrite/-o, --limit N (None=all), --threshold N,\n "
                "--sort (new/top/hot/controversial)"
            ),
            "func": scrape_redditor,
        },
        "subreddit": {
            "targets": ("subreddit", "sub", "r"),
            "desc": (
                "subreddit: scrape redditors from a subreddit.\n "
                "Flags: --redditor-limit N, --comment-limit N,\n "
                "--depth N, --sort (new/top/hot/controversial)"
            ),
            "func": scrape_subreddit,
        },
    },
    "expand": {
        "targets": ("expand", "expand_redditors_comments"),
        "desc": (
            "expand: expand redditors comments with less"
            " than a threshold number of comments. "
            "Flags: --threshold N"
        ),
        "func": expand_redditors_comments,
    },
    "delete": {
        "targets": {
            "all": "all",
            "submissions": ("subs", "submission", "submissions"),
            "comments": ("c", "comment", "comments"),
        },
        "desc": (
            "delete: remove rows from tables. Usage: delete "
            "&lt;submissions|comments|all&gt;. "
            "This prompts for confirmation."
        ),
        "func": clear_tables,
    },
    # TODO wrap singleton commands in dict like scrape
    # TODO refactor unknown command handling to match (desc, func)
    "db": {
        "desc": "<b>db &lt;SQL&gt;</b>: run SQL against DB",
        "func": db_execute,
    },
    "unknown": (
        "Error: Unknown command. Available commands:"
        " scrape, delete, db, help",
    ),
}
