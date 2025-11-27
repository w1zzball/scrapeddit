import logging
from utils.prompt import prompt_loop


# TODO consider adding -nodb flag to skip database storage
# TODO consider adding -vis flag to visualize data after scraping
def main():
    logging.basicConfig(
        filename="logs/logs.txt", level=logging.INFO, encoding="utf-8"
    )
    prompt_loop()


if __name__ == "__main__":
    main()
