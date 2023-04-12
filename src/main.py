"""
Test Deployment file
"""
import logging
import time


def main() -> None:
    """Main Method"""
    while True:
        logging.info("Ebbo running...")
        time.sleep(10)


if __name__ == "__main__":
    main()
