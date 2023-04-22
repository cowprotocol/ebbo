
# Ethereum Best Bid/Offer (EBBO) Monitoring Tool

  

This tool monitors all settlements that happen on-chain, focusing on EBBO testing. More concretely, we promise our users that they will get a price that is at least as good as what they can find on other DEXs. By parsing publicly available liquidity, we can monitor how often solver solutions with better surplus could have been provided.

  
## Scripts

The project consists of 3 main components: <br>

  
1. In the first component, for each auction, we look at all solutions that did NOT win and check whether any of them actually provided a better deal to an order that got executed by the winning solution. This currently is best used for analyzing historical data. This script utilizes the callData of all solutions.
The output consists of all orders that could have provided the user a better surplus with corresponding solver and absolute/relative values of the surplus difference. It also provides the error rate of each solver. The competition endpoint is used for this. To run this, set start_block, end_block or tx_hash in `test.py`.

<br>

2. The second component is a spin-off from the first that serves as a live logging tool which gathers the most recent settlements on CowSwap available, and checks them for EBBO.
<br>
<br>
3. The third component relies on onchain data and the instance.json describing the auction. This component parses all settlements that happened on-chain, recovers the surplus that each order got, and for each executed order, calls Quasimodo and asks for a solution that only executes that order. Then, it checks what surplus Quasimodo gives to that order and compares with what happened on-chain.

  

## Setup Project

Clone Repository: <br>
  

    git clone https://github.com/cowprotocol/ebbo.git


Version python 3.10 is used. <br>

### Dependencies:


Install the following libraries as dependencies. <br>

    pip install requests
    
    pip install web3
    
    pip install dune-client
    
    pip  install  python-dotenv
  

To test either of the components, create a `.env` file in the root directory (ebbo) and set variables `ETHERSCAN_KEY` and `INFURA_KEY` as string values from [Etherscan API Key](https://etherscan.io/myapikey) in your profile and Infura once you have an account created one. You will also need a `DUNE_KEY` for running the historical data test. <br>
Sample `.env` structure:

    INFURA_KEY = 'string key here'
    ETHERSCAN_KEY = 'string key here'
    DUNE_KEY = 'string key here'


*To start the EBBO daemon, run the following from the ebbo directory:* <br>

    python3 -m src.daemon

*If you wish to run the EBBO tool over historical data, set the (start_block, end_block) or tx_hash in `test.py` and run the following from the ebbo directory:* <br>

       python3 -m tests.unit.test

You should be good to go now!


