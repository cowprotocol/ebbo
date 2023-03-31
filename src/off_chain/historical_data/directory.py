import os

configPath = "src/config.py"

# Get the directory path of the current script (src string omitted)
# Manually adjusted letter-wise
ebboDirPath = os.path.dirname(os.path.abspath(__file__))[:-29]
config = os.path.join(ebboDirPath, configPath)

with open(config, "r") as f:
    fileRead = f.read()
exec(fileRead)
ETHERSCAN_KEY = locals()["ETHERSCAN_KEY"]
INFURA_KEY = locals()["INFURA_KEY"]