"""an example paradigmatic ETL pipeline using the utils, this pipeline
scrapes a redditors comment
"""

from pathlib import Path
import sys
import logging

# resolves importation path issues
sys.path.append(str(Path(__file__).resolve().parents[1]))

from utils.reddit_utils import (
    get_redditors_comments,
    format_comment,
)
from utils.db_utils import batch_insert_comments


def main():
    # establish logger
    logging.basicConfig(
        filename="logs/logs.txt",
        level=logging.INFO,
        encoding="utf-8",
        format=(
            "%(name)s - %(funcName)s - %(asctime)s - "
            "%(levelname)s - %(message)s"
        ),
    )
    user_id = sys.argv[1]
    print(f"Starting ETL for user: {user_id}")
    logger = logging.getLogger(__name__)
    logger.info("started with args: %s", sys.argv[1:])
    # extract
    print("Extracting comments...")
    logger.info("started extraction")
    comments = get_redditors_comments(user_id)
    # transform
    print("Transforming comments...")
    logger.info("started transformation")
    formatted_comments = [format_comment(c) for c in comments]
    # load
    print("Loading comments...")
    logger.info("started loading")
    batch_insert_comments(comments=formatted_comments)
    logger.info("ETL finished")


if __name__ == "__main__":
    main()
