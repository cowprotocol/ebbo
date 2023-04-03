"""
Test Deployment file
"""
import logging
import time

def main() -> None:
    """ Main Method"""
    while True:
        logging.warning("CoW Protocol!")
        time.sleep(10)

if __name__ == "__main__":
    main()
