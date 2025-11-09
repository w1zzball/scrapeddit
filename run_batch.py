import subprocess
import sys
from time import sleep
from pathlib import Path
import argparse


def main(*args, **kwargs):
    DELAY_BETWEEN = 5  # delay between requests in seconds
    parse = argparse.ArgumentParser()
    parse.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip submissions that have already been scraped.",
    )
    parse.add_argument(
        "--sorts",
        type=str,
        help="Comma-separated list of sorts to loop through.",
    )
    parse.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Number of posts to scrape per subreddit per sort.",
    )
    parse.add_argument(
        "--delay",
        type=int,
        default=DELAY_BETWEEN,
        help="Delay between requests in seconds.",
    )
    parse.add_argument(
        "--subreddits",
        type=str,
        default=None,
        help="Comma-separated list of subreddits to scrape.",
    )
    parse.add_argument(
        "--file",
        type=str,
        help="Path to a file containing a list of subreddits to scrape.",
    )
    args = parse.parse_args()
    print(args)
    subreddits = []

    # use provided delay if any
    if args.delay:
        DELAY_BETWEEN = args.delay

    # collect subreddits from file if provided
    if args.file:
        file_path = Path(args.file)
        if file_path.exists():
            with file_path.open() as f:
                subreddits.extend([line.strip() for line in f if line.strip()])
        else:
            print(f"File {args.file} does not exist.")

    # collect subreddits from --subreddits if provided
    if args.subreddits:
        subreddits.extend(
            [sub.strip() for sub in args.subreddits.split(",") if sub.strip()]
        )

    # dedupe while preserving order
    seen = set()
    subreddits = [s for s in subreddits if not (s in seen or seen.add(s))]

    if not subreddits:
        print("No subreddits provided via --file or --subreddits. Exiting.")
        return

    # build sorts list preserving order and filtering to allowed sorts
    allowed = ["new", "hot", "top", "relevance", "comments"]
    if args.sorts:
        sorts = [sort.strip() for sort in args.sorts.split(",") if sort.strip()]
        sorts = [s for s in sorts if s in allowed]
        if not sorts:
            sorts = ["new", "hot", "top"]
    else:
        sorts = ["new", "hot", "top"]

    for sub in subreddits:
        for sort in sorts:
            print(
                f"\n Scraping subreddit: {sub} | sort: {sort} | limit: {args.limit}\n{'-' * 40}"
            )
            cmd = [
                sys.executable,
                "main.py",
                "scrape",
                "subreddit",
                sub,
                "--limit",
                str(args.limit),
                "--sort",
                sort,
                "--exit-after",
            ]

            # pass skip-existing flag through to main.py if requested
            if args.skip_existing:
                cmd.append("--skip-existing")

            try:
                subprocess.run(cmd, check=True)
            except subprocess.CalledProcessError as e:
                print(f" Error scraping {sub}: {e}")

        sleep(DELAY_BETWEEN)


if __name__ == "__main__":
    main()
