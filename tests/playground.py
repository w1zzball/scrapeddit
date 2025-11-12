import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from scrapeddit.utils.prompt import prompt_loop
from scrapeddit.utils.reddit_utils import (
    get_submission,
    format_submission,
    get_comment,
    format_comment,
    get_redditors_comments,
    get_redditors_from_subreddit,
)
from scrapeddit.utils.db_utils import (
    db_get_redditors_from_subreddit,
)
from scrapeddit.utils.scraping_utils import (
    scrape_redditor,
    recursively_scrape_redditors_for_subreddit,
)


def main():
    # prompt_loop()
    # comments = get_redditors_comments("bubblebotz", 5)
    # for comment in comments:
    #     formatted = format_comment(comment)
    #     print(formatted)
    # redditors = db_get_redditors_from_subreddit("cats", 100)
    # print(redditors)
    # scrape_redditor("bubblebotz", sort="top", limit=10)
    recursively_scrape_redditors_for_subreddit(
        "gaming", redditor_limit=100, comment_limit=100, depth=5
    )
    # redditors = get_redditors_from_subreddit("cats")
    # print(redditors)


if __name__ == "__main__":
    main()
