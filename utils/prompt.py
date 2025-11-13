import argparse
import os
import shlex
import sys
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.application import get_app
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.completion import NestedCompleter
from .scraping_utils import (
    scrape_entire_thread,
    scrape_submission,
    scrape_comment,
    scrape_subreddit,
)
from .state import subreddit_progress
from .db_utils import db_execute, clear_tables
from .console import console
from .prompt_help_text import prompt_data

# pylint: disable=locally-disabled, line-too-long


# TODO add unit tests for prompt loop (mocking input/output)
# TODO add scrape redditor command
# TODO add recursive subreddit scraper command
def prompt_loop():
    """Interactive prompt loop for scrapeddit CLI."""
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
            prog = subreddit_progress
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
                "Commands: <b>scrape</b>, <b>db</b>, "
                "<b>delete</b>, <b>exit</b>"
            )

        cmd = tokens[0].lower()

        if cmd == "scrape":
            # brief usage when only 'scrape' typed
            if len(tokens) == 1:
                return HTML(prompt_data["scrape"]["base_desc"])

            target = tokens[1].lower()
            # help for thread
            if target in prompt_data["scrape"]["thread"]["targets"]:
                s = prompt_data["scrape"]["thread"]["desc"]
            # help for subreddit
            elif target in prompt_data["scrape"]["subreddit"]["targets"]:
                s = prompt_data["scrape"]["subreddit"]["desc"]
            # help for submission
            elif target in prompt_data["scrape"]["submission"]["targets"]:
                s = prompt_data["scrape"]["submission"]["desc"]
            # help for comment
            elif target in prompt_data["scrape"]["comment"]["targets"]:
                s = prompt_data["scrape"]["comment"]["desc"]
            # unknown target
            else:
                s = prompt_data["scrape"]["error_desc"]

            return HTML(s)

        if cmd == "delete":
            # quick help for delete command shown in bottom toolbar
            return HTML(prompt_data["delete"])

        if cmd == "db":
            return HTML(prompt_data["db"])
        return HTML(prompt_data["unknown"])

    cli_input_executed = False
    while True:
        try:
            if len(sys.argv) < 2 or cli_input_executed:
                user_input = session.prompt(
                    "scrapeddit> ",
                    bottom_toolbar=bottom_toolbar,
                    auto_suggest=AutoSuggestFromHistory(),
                    wrap_lines=True,
                ).strip()
                if not user_input:
                    continue
            else:
                # CLI invocation
                user_input = " ".join(sys.argv[1:]).strip()
                cli_input_executed = True
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
                    console.print(prompt_data["scrape"]["error_desc"])
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
                    "-s",
                    "--skip-existing",
                    action="store_true",
                    dest="skip_existing",
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
                # If invoking scrape subreddit with no limit, default to 10
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
                        scrape_entire_thread(
                            post_url=arg,
                            limit=limit,
                            threshold=threshold,
                            overwrite=overwrite,
                        )
                    if exit_after:
                        break
                    else:
                        scrape_entire_thread(
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
                        scrape_submission(
                            post_url=arg,
                            overwrite=overwrite,
                        )
                    if exit_after:
                        break
                    else:
                        scrape_submission(
                            post_id=arg,
                            overwrite=overwrite,
                        )
                    if exit_after:
                        break
                # comment
                elif target in ("comment", "c"):
                    scrape_comment(arg, overwrite=overwrite)
                    if exit_after:
                        break
                # subreddit (collection of submissions)
                elif target in ("subreddit", "r"):
                    # arg should be subreddit name, e.g. 'python' or 'r/python'
                    scrape_subreddit(
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
                subs_del, comm_del = clear_tables(target)
                console.print(
                    f"Deleted: submissions={subs_del}, comments={comm_del}"
                )
            elif user_input.startswith("db "):
                _, sql_str = user_input.split(" ", 1)
                db_execute(sql_str)
            elif user_input in {"exit", "quit"}:
                break
            else:
                print("Unknown command. Try 'scrape', 'db', or 'exit'.")
        except KeyboardInterrupt:
            break
        except EOFError:
            break
