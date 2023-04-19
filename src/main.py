"""
Test Deployment file
"""
import logging
import time

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)
# logging.basicConfig(level=logging.DEBUG)


def main() -> None:
    """Main Method"""
    while True:
        logging.info("EBBO running...")
        time.sleep(10)


if __name__ == "__main__":
    main()
