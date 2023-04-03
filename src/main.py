import logging
import time

def main() -> None:
    while True:
        logging.warning("CoW Protocol!")
        time.sleep(10)

if __name__ == "__main__":
    main()