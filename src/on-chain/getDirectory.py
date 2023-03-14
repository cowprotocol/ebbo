import json
import os

gpv2_settlementPath = 'contracts/gpv2_settlement.json'
configPath = 'src/config.py'

# Get the directory path of the current script (src string omitted)
ebboDirPath = os.path.dirname(os.path.abspath(__file__))[:-12]
config = os.path.join(ebboDirPath, configPath)
# Get the directory path of the contract directory relative to the script directory
contractAddressPath = os.path.join(ebboDirPath, gpv2_settlementPath)

#values needed for OnChainSurplus
with open(contractAddressPath, 'r') as f:
    gpv2Abi = json.load(f)

with open(config, 'r') as f:
    fileRead = f.read()
exec(fileRead)
INFURA_KEY = locals()['INFURA_KEY']