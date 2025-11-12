import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from scrapeddit.utils.io_utils import prompt_loop


def main():
    prompt_loop()


if __name__ == "__main__":
    main()
