from .console import console
from .reddit_utils import (
    get_submission,
    format_submission,
    get_comment,
    format_comment,
    get_comments_in_thread,
)
from .connection_utils import with_resources
import time
from rich.progress import Progress, BarColumn, TimeRemainingColumn, TextColumn
from concurrent.futures import ThreadPoolExecutor, as_completed
from .state import subreddit_progress


# TODO factor out insertion into separate db_utils.py
@with_resources(use_reddit=False, use_db=True)
def scrape_submission(
    conn,
    post_id: str | None = None,
    post_url: str | None = None,
    overwrite: bool = False,
    index=None,
    total: int | None = None,
):
    """Fetch a submission and insert it into the DB.

    If overwrite is True, existing rows will be updated on conflict.
    """
    submission = get_submission(post_id, post_url)
    submission = format_submission(submission)
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

    with conn.cursor() as cur:
        cur.execute(
            f"""
            INSERT INTO submissions {cols}
            VALUES ({placeholders})
            {conflict_clause}
            """,
            list(submission.values()),
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


@with_resources(use_reddit=False, use_db=True)
def scrape_comment(conn, comment_id: str, overwrite: bool = False):
    """
    Fetch a single comment and insert into DB.

    If overwrite=True update on conflict.
    """
    comment = get_comment(comment_id)  # type: ignore
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


@with_resources(use_reddit=False, use_db=True)
def scrape_comments_in_thread(
    conn,
    post_id=None,
    post_url=None,
    limit: int | None = None,
    threshold=0,
    overwrite: bool = False,
):
    """Scrape all comments in a thread and insert/update into DB.

    If overwrite=True, existing comments will be updated.
    """
    comments = get_comments_in_thread(
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
):
    with console.status("Scraping submission...", spinner="dots"):
        scrape_submission(
            conn,
            post_id=post_id,
            post_url=post_url,
            overwrite=overwrite,
            index=index,
            total=limit,
        )
    with console.status("Scraping comments...", spinner="dots"):
        scrape_comments_in_thread(
            conn,
            post_id=post_id,
            post_url=post_url,
            threshold=threshold,
            overwrite=overwrite,
        )


@with_resources(use_reddit=True, use_db=True)
def scrape_subreddit(
    reddit,
    conn,
    subreddit_name: str,
    sort: str = "new",
    limit: int | None = 10,
    overwrite: bool = False,
    subs_only: bool = False,
    max_workers: int = 5,  # set to respect rate limits
    skip_existing: bool = False,
):
    start_time = time.perf_counter()
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

    # formatted submissions batch
    formatted_rows = [tuple(format_submission(s).values()) for s in submissions]
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

    with conn.cursor() as cur:
        cur.executemany(sql_stmt, formatted_rows)
    conn.commit()

    console.print(f"Inserted {len(submissions)} submissions.")

    # threaded comment scraping
    if not subs_only:
        total_new = 0
        total_updated = 0
        total_skipped = 0
        submissions_scraped = 0
        total_errors = 0
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
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("comments", total=len(submissions))

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(scrape_one, s): s.id for s in submissions}
                for future in as_completed(futures):
                    info, err = future.result()
                    # advance the rich progress bar and our shared state
                    progress.advance(task)
                    subreddit_progress["current"] += 1

                    if err:
                        total_errors += 1
                        console.print(f"[red]Error scraping {info[3]}: {err}[/red]")
                    else:
                        console.print(
                            f"[green]✔ {info[3]} done[/green] "
                            f"{info[0]} new, {info[1]} updated, {info[2]} skipped"
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
