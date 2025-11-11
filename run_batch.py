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
            # read subs from the supplied file
            file_subs = [
                line.strip()
                for line in file_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            # if scraped_subreddits.txt exists, skip any subs already recorded there
            scraped_file = Path("scraped_subreddits.txt")
            if scraped_file.exists():
                already_scraped = {
                    line.strip()
                    for line in scraped_file.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                }
                filtered = [s for s in file_subs if s not in already_scraped]
                skipped = [s for s in file_subs if s in already_scraped]
                if skipped:
                    print(
                        f"Skipping {len(skipped)} already-scraped subreddits from {args.file}: {', '.join(sorted(skipped))}"
                    )
                subreddits.extend(filtered)
            else:
                subreddits.extend(file_subs)
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

        # append to scraped_subreddits.txt
        file_path = Path("scraped_subreddits.txt")
        try:
            existing = set()
            if file_path.exists():
                existing = {
                    line.strip()
                    for line in file_path.read_text(encoding="utf-8").splitlines()
                    if line.strip()
                }
            if sub not in existing:
                with file_path.open("a", encoding="utf-8") as f:
                    f.write(sub + "\n")
        except Exception as e:
            print(f" Error writing scraped subreddit list: {e}")

        sleep(DELAY_BETWEEN)


if __name__ == "__main__":
    main()
