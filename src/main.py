"""
Test Deployment File
"""
import logging
import time


def main() -> None:
    """Main Method"""
    logging.basicConfig(format="%(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger.addHandler(logging.StreamHandler())
    logger.setLevel(logging.DEBUG)
    while True:
        logger.warning("CoW Protocol!")
        time.sleep(10)


if __name__ == "__main__":
    main()
