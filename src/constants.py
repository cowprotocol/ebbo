"""
All Constants that are used throughout the project
"""

# main loop
SLEEP_TIME_IN_SEC = 10

# surplus tests
SURPLUS_ABSOLUTE_DEVIATION_ETH = 0.002
SURPLUS_REL_DEVIATION = 0.001

# cost coverage test
COST_COVERAGE_ABSOLUTE_DEVIATION_ETH = 0.005
COST_COVERAGE_RELATIVE_DEVIATION = 0.50

# fee quote test
FEE_RELATIVE_DEVIATION_FLAG = 0.50

# requests
SETTLEMENT_CONTRACT_ADDRESS = "0x9008D19f58AAbD9eD0D60971565AA8510560ab41"
REQUEST_TIMEOUT = 5
SUCCESS_CODE = 200
FAIL_CODE = 404

header = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"
}
