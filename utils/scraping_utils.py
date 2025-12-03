import logging
from .console import console
from .reddit_utils import (
    get_submission,
    format_submission,
    get_comment,
    format_comment,
    get_comments_in_thread,
    get_redditors_comments,
    get_redditors_from_subreddit,
)
from .connection_utils import with_resources
from .db_utils import insert_submission
import time
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
from concurrent.futures import ThreadPoolExecutor, as_completed
from .state import subreddit_progress

logger = logging.getLogger(__name__)


"""Utils for scraping Reddit and inserting into DB."""


# TODO factor out insertion into separate db_utils.py
# @with_resources(use_reddit=False, use_db=True)
def scrape_submission(
    # conn,
    post_id: str | None = None,
    post_url: str | None = None,
    overwrite: bool = False,
    index=None,
    total: int | None = None,
    **kwargs,
):
    """Fetch a submission and insert it into the DB.

    If overwrite is True, existing rows will be updated on conflict.
    """
    logger.info(
        f"Scraping submission {post_id} / {post_url} | overwrite={overwrite}"
    )
    logger.info("extracting submission data...")
    submission = get_submission(post_id, post_url)
    logger.info("transforming submission data...")
    submission = format_submission(submission)
    res = insert_submission(submission)
    if res:
        prefix = ""
        if index is not None and total is not None:
            prefix = f"[{index}/{total}] "
        elif index is not None:
            prefix = f"[{index}] "
        console.print(f"{prefix}Inserted/updated submission {res[0]}")
    else:
        console.print("No change to submission (conflict and skipped)")


@with_resources(use_reddit=False, use_db=True)
def scrape_comment(conn, comment_id: str, overwrite: bool = False, **kwargs):
    """
    Fetch a single comment and insert into DB.

    If overwrite=True update on conflict.
    """
    logger.info(f"Scraping comment {comment_id} | overwrite={overwrite}")
    logger.info("extracting comment data...")
    comment = get_comment(comment_id)  # type: ignore
    logger.info("transforming comment data...")
    formatted_comment = format_comment(comment)
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

    logger.info("loading comment data into DB...")
    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO comments {cols}
            VALUES ({placeholders})
            {conflict_clause}
            """,
            formatted_comment,
        )
        res = cur.fetchone()
    if res:
        console.print(f"Inserted/updated comment {res[0]}")
    else:
        console.print("No change to comment (conflict and skipped)")


# TODO add more progress info
@with_resources(use_reddit=False, use_db=True)
def scrape_comments_in_thread(
    conn,
    post_id=None,
    post_url=None,
    limit: int | None = None,
    threshold=0,
    overwrite: bool = False,
    **kwargs,
):
    """Scrape all comments in a thread and insert/update into DB.

    If overwrite=True, existing comments will be updated.
    """
    logger.info(
        f"Scraping comments in thread {post_id} / {post_url} "
        f"| overwrite={overwrite}"
    )
    logger.info("extracting comments data...")
    comments = get_comments_in_thread(
        post_id=post_id,
        post_url=post_url,
        limit=limit,
        threshold=threshold,
    )
    total = len(comments)
    logger.info(f"transforming {total} comments data...")
    cols = (
        "(name, author, body, created_utc, edited, ups, "
        "parent_id, submission_id, subreddit)"
    )
    placeholders = "%s,%s,%s,%s,%s,%s,%s,%s,%s"

    logger.info("loading comments data into DB...")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT name, COALESCE(edited, FALSE), COALESCE(ups, 0)
            FROM comments
            WHERE submission_id = %s;
            """,
            ("t3_" + str(post_id),),
        )
        existing = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

        formatted_comments = list(map(format_comment, comments))

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
    if not conn.autocommit:
        conn.commit()
    return (
        len(new_rows),
        len(changed_rows),
        total - len(changed_rows) - len(new_rows),
    )


@with_resources(use_reddit=False, use_db=True)
def scrape_entire_thread(
    conn,
    post_id=None,
    post_url=None,
    limit: int | None = None,
    threshold=0,
    overwrite: bool = False,
    index: int | None = None,
    **kwargs,
):
    logger.info(
        f"Scraping entire thread {post_id} / {post_url} | "
        f"overwrite={overwrite}"
    )
    with console.status("Scraping submission...", spinner="dots"):
        scrape_submission(
            post_id=post_id,
            post_url=post_url,
            overwrite=overwrite,
            index=index,
            total=limit,
        )
    with console.status("Scraping comments...", spinner="dots"):
        scrape_comments_in_thread(
            post_id=post_id,
            post_url=post_url,
            threshold=threshold,
            overwrite=overwrite,
        )


# TODO update count logic to reflect skipped submissions
@with_resources(use_reddit=True, use_db=True)
def scrape_subreddit(
    reddit,
    conn,
    subreddit_name: str,
    sort: str = "new",
    limit: int | None = 10,
    overwrite: bool = False,
    subs_only: bool = False,
    comments_only: bool = False,
    max_workers: int = 5,  # set to respect rate limits
    skip_existing: bool = False,
    **kwargs,
):
    """Scrape submissions and comments from a subreddit."""
    logger.info(
        f"Scraping subreddit {subreddit_name} | sort={sort} | limit={limit} "
        f"| overwrite={overwrite} | subs_only={subs_only} | "
        f"comments_only={comments_only} | max_workers={max_workers}"
        f" | skip_existing={skip_existing}"
    )
    start_time = time.perf_counter()
    logger.info(f"extracting submissions from r/{subreddit_name}...")
    sub = reddit.subreddit(subreddit_name)
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
        with conn.cursor() as cur:
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

    # insert formatted submissions batch
    if not comments_only:
        logger.info("transforming submissions data...")
        formatted_rows = [
            tuple(format_submission(s).values()) for s in submissions
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

        if not overwrite:
            conflict_clause = "ON CONFLICT (name) DO NOTHING"
        else:
            conflict_clause = (
                "ON CONFLICT (name) DO UPDATE SET "
                "author=EXCLUDED.author, title=EXCLUDED.title"
            )

        # build SQL statement in smaller parts to avoid long lines
        columns_str = ", ".join(cols)
        sql_stmt = (
            "INSERT INTO submissions (" + columns_str + ")\n"
            "VALUES (" + placeholders + ")\n" + conflict_clause
        )
        logger.info("loading submissions data into DB...")
        with conn.cursor() as cur:
            cur.executemany(sql_stmt, formatted_rows)
        conn.commit()

        console.print(f"Inserted {len(submissions)} submissions.")

    else:
        console.print("Skipping submission insertion as (comments only mode).")

    # threaded comment scraping
    total_new = 0
    total_updated = 0
    total_skipped = 0
    submissions_scraped = 0
    total_errors = 0

    if not subs_only:
        console.print(
            "Fetching comments for "
            f"{len(submissions)} threads (max {max_workers} workers)..."
        )

        def scrape_one(submission):
            """Worker: scrape and insert all comments for one submission.

            Always return a tuple (info_tuple, err) where info_tuple is
            (new, updated, skipped, submission_id).
            """
            try:
                new, updated, skipped = scrape_comments_in_thread(
                    submission.id, overwrite=overwrite
                )
                return (new, updated, skipped, submission.id), None
            except Exception as e:
                logger.error(
                    f"Error scraping comments for submission "
                    f"{submission.id}: {e}"
                )
                return (0, 0, 0, submission.id), str(e)

        # progress state for toolbar
        subreddit_progress.update(
            {
                "enabled": True,
                "current": 0,
                "total": len(submissions),
            }
        )

        # rich progress bar for main scraping loop
        with Progress(
            "Scraping threads...",
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeRemainingColumn(elapsed_when_finished=True),
            console=console,
        ) as progress:
            task = progress.add_task("comments", total=len(submissions))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(scrape_one, s): s.id for s in submissions
                }
                for future in as_completed(futures):
                    info, err = future.result()
                    # advance the rich progress bar and shared state
                    progress.advance(task)
                    subreddit_progress["current"] += 1

                    if err:
                        total_errors += 1
                        console.print(
                            f"[red]Error scraping {info[3]}: {err}[/red]"
                        )
                    else:
                        console.print(
                            f"[green]✔ {info[3]} done[/green] "
                            f"{info[0]} new, {info[1]} updated, "
                            f"{info[2]} skipped"
                        )
                        total_new += info[0]
                        total_updated += info[1]
                        total_skipped += info[2]
                        submissions_scraped += 1

        # disable the toolbar progress after scraping finishes
        subreddit_progress["enabled"] = False

    elapsed = time.perf_counter() - start_time
    total_ms = int(elapsed * 1000)
    hh = total_ms // 3600000
    rem = total_ms % 3600000
    mm = rem // 60000
    rem = rem % 60000
    ss = rem // 1000
    ms = rem % 1000
    elapsed_str = f"[green]{hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}[/green]"

    comment_summary = (
        " \nComments: "
        f"[green]{total_new} new[/green], "
        f"[yellow]{total_updated} updated[/yellow], "
        f"[red]{total_skipped} skipped[/red]"
    )

    if total_errors > 0:
        error_summary = f"[red]{total_errors} errors[/red]"
    else:
        error_summary = f"[white]{total_errors} errors[/white]"

    # print final summary in smaller concatenated pieces
    console.print(
        "\nDone in "
        + elapsed_str
        + ". with "
        + error_summary
        + "\nSubmissions: "
        + f"[green]{submissions_scraped} scraped[/green], "
        + f"[red]{skipped_count} skipped[/red]."
        + (comment_summary if submissions_scraped > 0 else ""),
        markup=True,
    )


# TODO stop duplicate redditor scraping
@with_resources(use_reddit=False, use_db=True)
def scrape_redditor(
    conn,
    user_id,
    limit: int = 100,
    overwrite: bool = False,
    sort: str = "new",
    **kwargs,
):
    """
    Given a redditor, scrape the last n (default: 100) comments they made
    """
    logger.info(
        f"Scraping comments for u/{user_id} | limit={limit} "
        f"| overwrite={overwrite} | sort={sort}"
    )
    print(f"Scraping comments for u/{user_id}...")
    try:
        comments = get_redditors_comments(user_id, limit, sort=sort)
    except Exception as e:
        logger.error(f"Error scraping u/{user_id}: {e}")
        console.print(f"[red]Error scraping u/{user_id}: {e}[/red]")
        return
    formatted_rows = [format_comment(c) for c in comments]
    # TODO factor out common insertion code as it is used multiple times
    logger.info(
        f"Inserting {len(formatted_rows)} comments for "
        f"u/{user_id} into the database."
    )
    with conn.cursor() as cur:
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
                "subreddit=EXCLUDED.subreddit"
            )
        else:
            conflict_clause = "ON CONFLICT (name) DO NOTHING"

        sql_stmt = (
            "INSERT INTO comments " + cols + "\n"
            "VALUES (" + placeholders + ")\n" + conflict_clause
        )
        cur.executemany(sql_stmt, formatted_rows)
    console.print(f"Inserted {len(formatted_rows)} comments for u/{user_id}.")


# TODO add multithreading option


def scrape_redditors(
    redditors, limit: int = 100, overwrite: bool = False, sort: str = "new"
):
    """
    Given a list of redditors, scrape the last n comments they made
    """
    logger.info(
        f"Scraping comments for {len(redditors)} redditors | limit={limit} "
        f"| overwrite={overwrite} | sort={sort}"
    )
    for redditor in redditors:
        try:
            console.print(f"Scraping redditor: u/{redditor}")
            scrape_redditor(
                redditor, limit=limit, overwrite=overwrite, sort=sort
            )
        except Exception as e:
            console.print(f"[red]Error scraping u/{redditor}: {e}[/red]")


# TODO add multithreading option


@with_resources(use_reddit=False, use_db=True)
def expand_redditors_comments(conn, threshold, limit, max_workers=5, **kwargs):
    """get more comments from redditors in the
    database with less than threshold comments"""
    logger.info(f"Expanding redditors with less than {threshold} comments ")
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT author, COUNT(*)
            FROM comments
            GROUP BY author
            HAVING COUNT(*) < %s;
            """,
            (threshold,),
        )
        redditors = [row[0] for row in cur.fetchall()]

    console.print(
        f"Found {len(redditors)} redditors with less than "
        f"{threshold} comments. Expanding..."
    )

    # rich progress bar for main scraping loop
    with Progress(
        "expanding redditors...",
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TimeRemainingColumn(elapsed_when_finished=True),
        console=console,
    ) as progress:
        task = progress.add_task("redditors", total=len(redditors))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(scrape_redditor, redditor): redditor
                for redditor in redditors
            }
            for future in as_completed(futures):
                redditor = futures[future]
                try:
                    future.result()
                    console.print(f"[green]✔ u/{redditor} done[/green]")
                except Exception as e:
                    console.print(
                        f"[red]Error expanding u/{redditor}: {e}[/red]"
                    )
                progress.advance(task)


@with_resources(use_reddit=False, use_db=True)
def recursively_scrape_redditors_for_subreddit(
    conn,
    subreddit,
    comment_limit: int = 100,
    redditor_limit: int = 100,
    overwrite: bool = False,
    sort: str = "top",
    depth: int = 2,
    scraped_redditors: list[str] = [],
    scraped_subreddits: list[str] = [],
):
    """
    Given a subreddit, fetch all redditors with comments on that
    subreddit from database, then scrape their comments, and for each
    subreddit found in those comments, repeat
    """

    logger.info(
        f"Recursively scraping redditors for subreddit r/{subreddit} "
        f"| comment_limit={comment_limit} | redditor_limit={redditor_limit} "
        f"| overwrite={overwrite} | sort={sort} | depth={depth}"
    )
    redditors = get_redditors_from_subreddit(subreddit, limit=redditor_limit)
    scraped_subreddits.append(subreddit)
    redditors = [r for r in redditors if r not in scraped_redditors]
    print("got redittors")
    console.print(f"Found {len(redditors)} redditors in r/{subreddit}.")
    scrape_redditors(
        redditors, limit=comment_limit, overwrite=overwrite, sort=sort
    )
    scraped_redditors.extend(redditors)
    if depth == 0:
        return
    # look up redditors comments and get subreddits
    with conn.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT subreddit FROM comments WHERE author = ANY(%s)",
            (list(redditors),),
        )
        subreddits = [
            row[0].replace("r/", "")
            for row in cur.fetchall()
            if row[0] is not None and row[0] not in scraped_subreddits
        ]
    console.print(
        f"Found {len(subreddits)} subreddits from redditors' comments."
    )
    for sub in subreddits:
        console.print(f"Recursing into subreddit: r/{sub} (depth {depth-1})")

        recursively_scrape_redditors_for_subreddit(
            subreddit=sub,
            comment_limit=comment_limit,
            redditor_limit=redditor_limit,
            overwrite=overwrite,
            sort=sort,
            depth=depth - 1,
            scraped_redditors=scraped_redditors,
            scraped_subreddits=scraped_subreddits,
        )
