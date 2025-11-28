import logging
from utils.prompt import prompt_loop
import sys


# TODO consider adding -nodb flag to skip database storage
# TODO consider adding -vis flag to visualize data after scraping
# TODO add debug flag for more verbose logging
def main():
    logging.basicConfig(
        filename="logs/logs.txt",
        level=logging.INFO,
        encoding="utf-8",
        format=(
            "%(name)s - %(funcName)s - %(asctime)s - "
            "%(levelname)s - %(message)s"
        ),
    )
    logger = logging.getLogger(__name__)
    logger.info("started with args: %s", sys.argv[1:])
    prompt_loop()


if __name__ == "__main__":
    main()
