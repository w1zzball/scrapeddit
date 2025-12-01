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
from .state import subreddit_progress
from .db_utils import db_execute, clear_tables
from .console import console
from .prompt_help_text import prompt_data

# pylint: disable=locally-disabled, line-too-long


# TODO add unit tests for prompt loop (mocking input/output)
# TODO add recursive subreddit scraper command
def prompt_loop():
    """Interactive prompt loop for scrapeddit CLI."""
    # Autocompletion for top-level commands and scrape targets.
    completer = NestedCompleter.from_nested_dict(
        {
            "scrape": {
                func
                for func in prompt_data["scrape"].keys()
                if func not in ("error", "base")
            },
            "delete": {
                targets for targets in prompt_data["delete"]["targets"].keys()
            },
            "expand": None,
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

            # TODO change to declarative style with data structure mapping
        if not tokens:
            return HTML(
                "Commands: <b>scrape</b>, <b>db</b>, "
                "<b>delete</b>, <b>exit</b>"
            )

        # TODO refactor to allow delete, db, and other commands
        # TODO ... to be supporte in same loop
        cmd = tokens[0].lower()
        # ---- help for scrape command ----#
        if cmd == "scrape":
            # brief usage when only 'scrape' typed
            if len(tokens) == 1:
                return HTML(prompt_data["scrape"]["base"]["desc"])

            target = tokens[1].lower()
            s = prompt_data["scrape"]["error"]["desc"]
            for scrape_func in prompt_data["scrape"].values():
                if target in scrape_func.get("targets", ()):
                    s = scrape_func["desc"]

            return HTML(s)

        if cmd == "delete":
            # help for delete command
            return HTML(prompt_data["delete"]["desc"])
        # help for db command
        if cmd == "db":
            return HTML(prompt_data["db"]["desc"])
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

            # TODO refactor to accept none scrape commands
            # TODO factor out argparse handling to function returning args
            # Support commands:
            #   scrape thread <id|url>
            #   scrape submission <id|url>
            #   scrape comment <comment_id>
            if user_input.startswith("scrape "):
                # allow flags after the id/url, e.g.:
                #   scrape thread <id|url> --overwrite --limit 0 --threshold 0
                tokens = shlex.split(user_input)
                if len(tokens) < 3:
                    console.print(prompt_data["scrape"]["error"]["desc"])
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
                # TODO: clean up limit handling here and above
                scrape_functions = [
                    command_dict
                    for name, command_dict in prompt_data["scrape"].items()
                    if prompt_data["scrape"].get(name).get("func")
                ]
                for prompt in scrape_functions:
                    if target in prompt["targets"]:
                        func = prompt["func"]
                        func(
                            post_id=arg,
                            subreddit_name=arg,
                            comment_id=arg,
                            user_id=arg,
                            sort=sort,
                            limit=limit,
                            threshold=threshold,
                            overwrite=overwrite,
                            subs_only=subs_only,
                            max_workers=max_workers,
                            skip_existing=skip_existing,
                        )
                    if exit_after:
                        break
            # delete command
            elif user_input.startswith("delete ") or user_input == "delete":
                tokens = shlex.split(user_input)
                if len(tokens) < 2:
                    print("Usage: delete <submissions|comments|all>")
                    continue
                target = tokens[1].lower()
                if target in prompt_data["delete"]["targets"]["submissions"]:
                    target = "submissions"
                elif target in prompt_data["delete"]["targets"]["comments"]:
                    target = "comments"
                elif target == prompt_data["delete"]["targets"]["all"]:
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
                subs_del, comm_del = prompt_data["delete"]["func"](target)
                console.print(
                    f"Deleted: submissions={subs_del}, comments={comm_del}"
                )
            elif user_input.startswith("db "):
                _, sql_str = user_input.split(" ", 1)
                prompt_data["db"]["func"](sql_str)
            elif user_input.startswith("expand "):
                tokens = shlex.split(user_input)
                flags = tokens[1:]
                parser = argparse.ArgumentParser(add_help=False)
                parser.add_argument("--threshold", type=int, required=True)
                parser.add_argument("--limit", type=int, required=False)
                try:
                    ns, unknown = parser.parse_known_args(flags)
                except Exception as e:
                    print("Error parsing flags:", e)
                    continue
                threshold = ns.threshold
                limit = ns.limit
                prompt_data["expand"]["func"](threshold=threshold, limit=limit)
            elif user_input in {"exit", "quit"}:
                break
            else:
                print("Unknown command. Try 'scrape', 'db', or 'exit'.")
        except KeyboardInterrupt:
            break
        except EOFError:
            break
