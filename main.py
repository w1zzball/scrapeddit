from utils.prompt import prompt_loop
from utils.scraping_utils import scrape_subreddit


def main():
    # scrape_subreddit("cavesofqud", sort="new", limit=3, comments_only=False)
    prompt_loop()


if __name__ == "__main__":
    main()
