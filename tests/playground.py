# scrapeddit/tests/playground.py
import os
import sys

# Add the parent directory of 'scrapeddit' to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from scrapeddit.utils.scraping_utils import get_submission


def main():
    submission = get_submission("3g1jfi")
    print(submission.title)


if __name__ == "__main__":
    main()
