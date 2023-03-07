import json
import requests
from fractions import Fraction
from config import ETHERSCAN_KEY


def surplusCalculation(startBlock = None, endBlock = None, settlementHash = None):
    if settlementHash is not None:
        calculations(settlementHash)

    elif startBlock is not None and endBlock is not None:
        #Etherscan endpoint call for settlements between start and end block
        etherscanUrl = f"https://api.etherscan.io/api?module=account&action=txlist&address=0x9008D19f58AAbD9eD0D60971565AA8510560ab41&startblock={startBlock}&endblock={endBlock}&sort=desc&apikey={ETHERSCAN_KEY}"
        jsonRecentSettlements = requests.get(etherscanUrl)
        pyRecentSettlements = json.loads(jsonRecentSettlements.text)
        #all "result" go into results (based on API return value names from docs)
        results = pyRecentSettlements["result"]

        for counterResults in range(len(results)):
            settlementHash = results[counterResults]["hash"]
            calculations(settlementHash)

def fetchCompetitionData(settlementHash):
    endpointUrl = f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlementHash}"
    jsonCompetitionData = requests.get(endpointUrl)
    return jsonCompetitionData

            
def calculations(settlementHash):   
    # Once we have settlement transaction hashes, call competition endpoint to get solver data
    # endpointUrl = f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlementHash}"
    # jsonCompetitionData = requests.get(endpointUrl)
    jsonCompetitionData = fetchCompetitionData(settlementHash)

    if jsonCompetitionData.status_code == 200:
        pyCompetitionData = json.loads(jsonCompetitionData.text)
        winningSolution = pyCompetitionData["solutions"][-1]
        winningOrders = winningSolution["orders"]

        for orderCounter in range(len(winningOrders)):
            individualOrderID = winningSolution["orders"][orderCounter]["id"]
            orderDataUrl = f"https://api.cow.fi/mainnet/api/v1/orders/{individualOrderID}"
            jsonIndividualOrder = requests.get(orderDataUrl)
            if jsonIndividualOrder.status_code == 200:
                pyIndividualOrder = json.loads(jsonIndividualOrder.text)
                if pyIndividualOrder["isLiquidityOrder"] == False:
                    # print(settlementHash)
                #These two values are fixed for each order ID
                    buyAmountFromID = int(pyIndividualOrder["buyAmount"])
                    sellAmountFromID = int(pyIndividualOrder["sellAmount"])
                    sellToken = pyIndividualOrder["sellToken"]
                    buyToken = pyIndividualOrder["buyToken"]
                    kind = pyIndividualOrder["kind"]
                
                    surplusDeviationDict = {}
                    solnCount = 0
                    for soln in pyCompetitionData["solutions"]:
                        for OrdersCounter in range(len(soln["orders"])):
                            if individualOrderID == soln["orders"][OrdersCounter]["id"]:
                                if kind == "sell":
                                    winSurplus = int(pyIndividualOrder["executedBuyAmount"]) - buyAmountFromID
                                    if pyIndividualOrder["class"]=="limit":                      
                                        execAmt = ((int(Fraction(soln["orders"][OrdersCounter]["executedAmount"])) - int(pyIndividualOrder["executedSurplusFee"])) * Fraction(soln["clearingPrices"][sellToken]) // Fraction(soln["clearingPrices"][buyToken]))
                                        surplus = execAmt - buyAmountFromID
                                    else:
                                        execAmt = int(Fraction(soln["orders"][OrdersCounter]["executedAmount"]) * Fraction(soln["clearingPrices"][sellToken]) // Fraction(soln["clearingPrices"][buyToken]))
                                        surplus = execAmt - buyAmountFromID
                                    index = 0    
                                    surplusToken = pyIndividualOrder["buyToken"]

                                elif kind == "buy":
                                    winSurplus = sellAmountFromID - int(pyIndividualOrder["executedSellAmountBeforeFees"])
                                    if pyIndividualOrder["class"] == "limit":
                                        execAmt = ((int(Fraction(soln["orders"][OrdersCounter]["executedAmount"])) ) * Fraction(soln["clearingPrices"][buyToken]) // Fraction(soln["clearingPrices"][sellToken]))
                                        surplus = sellAmountFromID - int(pyIndividualOrder["executedSurplusFee"]) - execAmt 
                                    else:
                                        execAmt = int(Fraction(soln["orders"][OrdersCounter]["executedAmount"]) * Fraction(soln["clearingPrices"][buyToken]) // Fraction(soln["clearingPrices"][sellToken]))
                                        surplus = sellAmountFromID - execAmt
                                    index = 1    
                                    surplusToken = pyIndividualOrder["sellToken"]
                                
                                diffSurplus = winSurplus - surplus
                                if index == 0:
                                    percentDeviation = (diffSurplus*100)/buyAmountFromID
                                else:
                                    percentDeviation = (diffSurplus*100)/sellAmountFromID
                                surplusETH = (int(pyCompetitionData["auction"]["prices"][surplusToken])/(pow(10,18))) * (diffSurplus / pow(10,18))
                                surplusDeviationDict[solnCount] = surplusETH, percentDeviation
                        solnCount+=1
                    printFunction(surplusDeviationDict, settlementHash, individualOrderID, pyCompetitionData)
                        

def printFunction(surplusDeviationDict, settlementHash, individualOrderID, pyCompetitionData):
    sortedDict = dict(sorted(surplusDeviationDict.items(), key=lambda x: x[1][0]))
    sortedValues = sorted(sortedDict.values(), key=lambda x: x[0])
    if sortedValues[0][0] < -0.001 and sortedValues[0][1]< -1:
        for key, value in sortedDict.items():
            if value == sortedValues[0]:
                firstKey = key
                break
        print("Settlement Hash: " + settlementHash)
        print("For order: " + individualOrderID)
        print("More surplus Corresponding Solver: " + pyCompetitionData["solutions"][firstKey]["solver"] + "     Deviation: " + str(format(sortedValues[0][1], '.5f')) + "%" + "   absolute difference: " + str(format(sortedValues[0][0], '.5f')) + " ETH\n")
