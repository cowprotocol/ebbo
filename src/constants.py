"""
All Constants that are used throughout the project
"""

# main loop
SLEEP_TIME_IN_SEC = 10

# surplus tests
SURPLUS_ABSOLUTE_DEVIATION_ETH = 0.005
SURPLUS_REL_DEVIATION = 0.004

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
BUFFERS_VALUE_USD_THRESHOLD = 200000

# threshold parameter to generate an alert when receiving kickbacks
KICKBACKS_ALERT_THRESHOLD = 0.3

# relevant addresses
SETTLEMENT_CONTRACT_ADDRESS = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
MEV_BLOCKER_KICKBACKS_ADDRESS = "0xCe91228789B57DEb45e66Ca10Ff648385fE7093b"

# requests
REQUEST_TIMEOUT = 5
SUCCESS_CODE = 200
FAIL_CODE = 404

header = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}
