from utils.prompt import prompt_loop
from utils.scraping_utils import scrape_subreddit


# TODO consider adding -nodb flag to skip database storage
# TODO consider adding -vis flag to visualize data after scraping
def main():
    # scrape_subreddit("cavesofqud", sort="new", limit=3, comments_only=False)
    prompt_loop()


if __name__ == "__main__":
    main()
