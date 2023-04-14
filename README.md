
# Ethereum Best Bid/Offer (EBBO) Monitoring Tool

  

This is a tool that monitors all settlements that happen onchain - primarily focusing on EBBO tests. More concretely, we give the promise to our users that they will get a price that is at least as good as what they can find on other DEXs and by parsing publicly available liquidity, we want to test how often solutions with better surplus could have been provided.

  

## Scripts

  

The project consists of 3 main components:

  
1. In the first component, for each auction, we look at all solutions that did NOT win and check whether any of them actually provided a better deal to an order that got executed by the winning solution. This currently is best used for analyzing historical data. This script utilizes the callData of all solutions.

The output consists of all orders that could have provided the user a better surplus with corresponding solver and absolute/relative values of the surplus difference. It also provides the error rate of each solver. The competition endpoint is used for this. To run this, set start_block, end_block or tx_hash in `test.py`.


*After dependencies have been installed, run the following from the ebbo directory:* <br>

       python3 -m tests.unit.test
<br>
2. The second component is a spin-off from the first that serves as a logging tool on the most recent data available using the competition endpoint. It gathers the most recent settlements available, and analyses them to see if any of them could have given a better surplus. 

*To start the daemon, run the following from the ebbo directory:* <br>

    python3 -m src.daemon

  
3. The third component will rely on onchain data and the instance.json describing the auction. This component parses all settlements that happened onchain, recovers the surplus that each order got, and then, for each executed order separately, calls Quasimodo and asks for a solution that only executes that order. Then, it checks what surplus Quasimodo gives to that order and compares with what happened onchain.

*Relevant file for this test:*

`on_chain_surplus.py`

  
  

## Running Code

  

To test either of the components, create a `config.py` file in the root directory (ebbo) and set variables `ETHERSCAN_KEY` and `INFURA_KEY` as string values from [Etherscan API Key](https://etherscan.io/myapikey) in your profile and Infura once you have an account created one. You will also need a `DUNE_KEY` for running the historical data test.

  

### Dependencies:

Version python 3.10 is used. <br>
Please install the following libraries as dependencies using pip/pip3. <br>

    pip install requests
    pip install web3
    pip install dune-client

  

You should be good to go now!


