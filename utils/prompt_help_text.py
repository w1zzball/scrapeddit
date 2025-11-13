"""Help text for prompt commands."""

# TODO add exit-after flag help
# TODO add skip-existing flag help
prompt_data = {
    "scrape": {
        "base_desc": (
            "Usage: <b>scrape &lt;target&gt; &lt;id_or_url&gt;</b>\n"
            " [--overwrite|-o] [--limit N] "
            "[--threshold N] [--max-workers N]"
        ),
        "error_desc": (
            "Error: Invalid scrape command. "
            "Unknown scrape target. Use thread, submission, "
            "comment, redditor or subreddit"
        ),
        "thread": {
            "targets": ("thread", "t", "entire", "entire_thread"),
            "desc": (
                "thread: scrape submission + comments. Flags: \n"
                "--overwrite/-o, --limit N (None=all), --threshold N"
            ),
        },
        "submission": {
            "targets": ("submission", "s", "post"),
            "desc": (
                "submission: scrape submission only. Flags:\n "
                "--overwrite/-o, --limit N (None=all), --threshold N"
            ),
        },
        "comment": {
            "targets": ("comment", "c"),
            "desc": (
                "comment: scrape single comment only. Flags:\n "
                "--overwrite/-o"
            ),
        },
        "redditor": {
            "targets": ("redditor", "user", "u"),
            "desc": (
                "redditor: scrape comments from a redditor. Flags:\n "
                "--overwrite/-o, --limit N (None=all), --threshold N,\n "
                "--sort (new/top/hot/controversial)"
            ),
        },
        "subreddit": {
            "targets": ("subreddit", "sub", "r"),
            "desc": (
                "subreddit: scrape redditors from a subreddit.\n "
                "Flags: --redditor-limit N, --comment-limit N,\n "
                "--depth N, --sort (new/top/hot/controversial)"
            ),
        },
    },
    "delete": (
        "delete: remove rows from tables. Usage: delete "
        "&lt;submissions|comments|all&gt;. "
        "This prompts for confirmation."
    ),
    "db": "<b>db &lt;SQL&gt;</b>: run SQL against DB",
    "unknown": (
        "Error: Unknown command. Available commands:"
        " scrape, delete, db, help",
    ),
}
