"""
Test Deployment File
"""
import logging
import time

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)


def get_logger() -> logging.Logger:
    """
    get_logger() returns a logger object.
    """
    logging.basicConfig(format="%(levelname)s - %(message)s")
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    return logger


def main() -> None:
    """Main Method"""
    logger = get_logger()
    while True:
        logger.warning("CoW Protocol!")
        time.sleep(10)


if __name__ == "__main__":
    main()
