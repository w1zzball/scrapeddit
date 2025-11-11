import os
import sys

# from scrapeddit.utils.scraping_utils import get_submission

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# Add the parent directory of 'scrapeddit' to sys.path

from scrapeddit.utils.scraping_utils import (
    get_submission,
    scrape_submission,
    get_comment,
    format_comment,
    scrape_comment,
    scrape_comments_in_thread,
    scrape_subreddit,
)


def main():
    # scrape_submission("1ok8gp0")
    # comment = get_comment("nm8tzft")
    # scrape_comment("nm8tzft", overwrite=True)
    # scrape_comments_in_thread(
    #     post_id="1ok8gp0",
    # )
    # print(format_comment(comment))
    # submission = get_submission("3g1jfi")
    # print(submission.title)
    scrape_subreddit("learnpython")


if __name__ == "__main__":
    main()
