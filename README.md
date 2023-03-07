# Ethereum Best Bid/Offer (EBBO) Monitoring Tool

This is a tool that monitors all settlements that happen onchain - primarily focusing on EBBO tests. More concretely, we give the promise to our users that they will get a price that is at least as good as what they can find on other DEXs and by parsing publicly available liquidity, we want to test how often solutions with better surplus could have been provided.

## Scripts

The project consists of 3 main components:  

1.  In the first component, for each auction, we look at all solutions that did NOT win and check whether any of them actually provided a better deal to an order that got executed by the winning solution. This currently is best used for analyzing historical data. This script utilizes the callData of all solutions.
The output consists of all orders that could have provided the user a better surplus with corresponding solver and absolute/relative values of the surplus difference. It also provides the error rate of each solver. The competition endpoint is used for this.
*Relevant file for this test:*
	`cowEndpointSurplus.py`

2. The second component is a spin-off from the first that serves as a logging tool on the most recent data available using the competition endpoint. It gathers the most recent settlements available, and analyzes them to see if any of them could have given a better surplus.
*Relevant files for this test. The first file should be executed since it uses functions from the second:*
`main.py` 
`cowEndpointFunctions.py`

4.  The third component will rely on onchain data and the instance.json describing the auction. This component parses all settlements that happened onchain, recovers the surplus that each order got, and then, for each executed order separately, calls Quasimodo and asks for a solution that only executes that order. Then, it checks what surplus Quasimodo gives to that order and compares with what happened onchain.
*Relevant file for this test:*
`OnChainSurplus.py`


## Running Code

To test either of the components, create a `config.py` file and set variables `ETHERSCAN_KEY` and `INFURA_KEY` as string values from [Etherscan API Key](https://etherscan.io/myapikey) in your profile and Infura once you have an account created. 

### Dependencies:
If not already installed, please install the `requests` and `web3.py` libraries.
Using pip/pip3, run the following commands:

    pip install requests

    pip install web3

You should be good to go now!