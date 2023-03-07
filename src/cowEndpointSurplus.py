import json
import requests
from fractions import Fraction
from config import ETHERSCAN_KEY

totalOrders = 0
higherSurplusOrders = 0
totalSurplusETH = 0
fileName = str
# first value in key-value pair is no. of times the solution won
# second value in key-value pair is no. of times it's been beat
solverDict = {
    "1Inch": [0,0],
    "Raven": [0,0],
    "0x": [0,0],
    "PLM": [0,0],
    "Quasilabs": [0,0],
    "Otex": [0,0],
    "SeaSolver": [0,0],
    "Laertes": [0,0],
    "ParaSwap": [0,0],
    "BalancerSOR": [0,0],
    "BaselineSolver": [0,0],
    "Legacy": [0,0],
    "NaiveSolver": [0,0],
    "DMA": [0,0],
    "CowDexAg": [0,0],
    "Barter": [0,0]
}

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

        with open(f"{fileName}", mode="a") as file:
            file.write(f"Total Orders = {str(totalOrders)} over {str(int(endBlock)-int(startBlock))} blocks from {str(startBlock)} to {str(endBlock)}\n")
            file.write("No. of better surplus orders: " + str(higherSurplusOrders) + "\n")
            file.write("Percent of potentially better offers: " + str(((higherSurplusOrders*100)/totalOrders)) + "%\n")
            file.write(f"Total missed surplus: {totalSurplusETH} ETH\n")
            file.write("\n")

            for i in range(len(solverDict)):
                key = list(solverDict.keys())[i]
                if solverDict[key][0] == 0:
                    errorPercent = 0
                else:
                    errorPercent = ((solverDict[key][1])*100)/(solverDict[key][0])
                file.write(f"Solver: {key} errored: {errorPercent}%\n")
            file.close()
            
def calculations(settlementHash):   
    # Once we have settlement transaction hashes, call competition endpoint to get solver data
    endpointUrl = f"https://api.cow.fi/mainnet/api/v1/solver_competition/by_tx_hash/{settlementHash}"
    jsonCompetitionData = requests.get(endpointUrl)

    if jsonCompetitionData.status_code == 200:
        pyCompetitionData = json.loads(jsonCompetitionData.text)
        winningSolution = pyCompetitionData["solutions"][-1]
        winningSolver = winningSolution["solver"]
        winningOrders = winningSolution["orders"]

        for orderCounter in range(len(winningOrders)):
            global solverDict
            solverDict[winningSolver][0] +=1
            global totalOrders
            totalOrders = totalOrders+1
            individualOrderID = winningSolution["orders"][orderCounter]["id"]
            orderDataUrl = f"https://api.cow.fi/mainnet/api/v1/orders/{individualOrderID}"
            jsonIndividualOrder = requests.get(orderDataUrl)
            if jsonIndividualOrder.status_code == 200:
                pyIndividualOrder = json.loads(jsonIndividualOrder.text)
                if pyIndividualOrder["isLiquidityOrder"] == False:
                    print(settlementHash)
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
        global higherSurplusOrders
        higherSurplusOrders = higherSurplusOrders + 1
        solver = pyCompetitionData["solutions"][-1]["solver"]
        global solverDict
        solverDict[solver][1] += 1
        global totalSurplusETH
        totalSurplusETH += sortedValues[0][0]
        with open(f"{fileName}", mode="a") as file:
            file.write("Settlement Hash: " + settlementHash + "\n")
            file.write("For order: " + individualOrderID + "\n")
            file.write("More surplus Corresponding Solver: " + pyCompetitionData["solutions"][firstKey]["solver"] + "     Deviation: " + str(format(sortedValues[0][1], '.5f')) + "%" + "   absolute difference: " + str(format(sortedValues[0][0], '.5f')) + " ETH\n")
            file.write("\n")
            file.close()

# ---------------------------- TESTING --------------------------------

optionInput = input("b for block input, h for hash input: ")

match optionInput:
    case "b":
        startBlock = input("Start Block: ")
        endBlock = input("End Block: ")
        fileName = str(startBlock) + "_surplusTo__" + str(endBlock) + ".txt"
        # serves to clear the previous file if checking same block range
        with open(f"{fileName}", mode="w") as file: 
            file.write("\n")
        print()
        surplusCalculation(startBlock, endBlock, None)
    case "h":
        settlementHash = input("Settlement Hash: ")
        fileName = settlementHash + "_surplus.txt"
        with open(f"{fileName}", mode="w") as file:
            file.write("\n")
        print()
        surplusCalculation(None, None, settlementHash)


