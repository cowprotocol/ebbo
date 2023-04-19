"""
Test Deployment file
"""
import logging
import time

logging.basicConfig(level=logging.DEBUG)


def main() -> None:
    """Main Method"""
    while True:
        logging.error("EBBO running...")
        time.sleep(10)


if __name__ == "__main__":
    main()
