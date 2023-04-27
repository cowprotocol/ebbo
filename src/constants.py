"""
Fetch env loaded secret keys, and other constants from here
"""
import os
from dotenv import load_dotenv

load_dotenv()
DUNE_KEY = os.getenv("DUNE_KEY")
INFURA_KEY = os.getenv("INFURA_KEY")
ETHERSCAN_KEY = os.getenv("INFURA_KEY")

ADDRESS = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"

ABSOLUTE_ETH_FLAG_AMOUNT = 0.002
REL_DEVIATION_FLAG_PERCENT = 0.1

header = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}
