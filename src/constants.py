"""
All Constants that are used throughout the project
"""

# main loop
SLEEP_TIME_IN_SEC = 10

# surplus tests
SURPLUS_ABSOLUTE_DEVIATION_ETH = 0.005
SURPLUS_REL_DEVIATION = 0.004

# combinatorial auctions
COMBINATORIAL_AUCTION_ABSOLUTE_DEVIATION_ETH = 0.005

# cost coverage test
COST_COVERAGE_ABSOLUTE_DEVIATION_ETH = 0.01
COST_COVERAGE_RELATIVE_DEVIATION = 0.50

# reference solver test
SOLVER_TIME_LIMIT = 20

# how many blocks are contained in a single day
DAY_BLOCK_INTERVAL = 7200

# cap parameter, per CIP-20, measured in ETH
CAP_PARAMETER = 0.01

# number of tx hashes before a new buffers check is ran
BUFFER_INTERVAL = 150

# threshold of value of buffers above which an alert is generated
BUFFERS_VALUE_USD_THRESHOLD = 400000

# threshold parameter to generate an alert when receiving kickbacks
KICKBACKS_ALERT_THRESHOLD = 0.5

# threshold to generate an alert for violating UDP
UDP_SENSITIVITY_THRESHOLD = 0.005

# relevant addresses
SETTLEMENT_CONTRACT_ADDRESS = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
MEV_BLOCKER_KICKBACKS_ADDRESSES = [
    "0xCe91228789B57DEb45e66Ca10Ff648385fE7093b",  # CoW DAO
    "0x008300082C3000009e63680088f8c7f4D3ff2E87",  # Copium Capital
    "0xbAda55BaBEE5D2B7F3B551f9da846838760E068C",  # Project Blanc
]

# requests
REQUEST_TIMEOUT = 5
SUCCESS_CODE = 200
FAIL_CODE = 404

header = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}
