cowamm_constantproduct = [
    {
        "inputs": [
            {"internalType": "address", "name": "_solutionSettler", "type": "address"}
        ],
        "stateMutability": "nonpayable",
        "type": "constructor",
    },
    {"inputs": [], "name": "CommitOutsideOfSettlement", "type": "error"},
    {"inputs": [], "name": "OrderDoesNotMatchCommitmentHash", "type": "error"},
    {"inputs": [], "name": "OrderDoesNotMatchDefaultTradeableOrder", "type": "error"},
    {
        "inputs": [{"internalType": "string", "name": "", "type": "string"}],
        "name": "OrderNotValid",
        "type": "error",
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "blockNumber", "type": "uint256"},
            {"internalType": "string", "name": "message", "type": "string"},
        ],
        "name": "PollTryAtBlock",
        "type": "error",
    },
    {
        "anonymous": False,
        "inputs": [
            {
                "indexed": True,
                "internalType": "address",
                "name": "owner",
                "type": "address",
            },
            {
                "components": [
                    {
                        "internalType": "contract IConditionalOrder",
                        "name": "handler",
                        "type": "address",
                    },
                    {"internalType": "bytes32", "name": "salt", "type": "bytes32"},
                    {"internalType": "bytes", "name": "staticInput", "type": "bytes"},
                ],
                "indexed": False,
                "internalType": "struct IConditionalOrder.ConditionalOrderParams",
                "name": "params",
                "type": "tuple",
            },
        ],
        "name": "ConditionalOrderCreated",
        "type": "event",
    },
    {
        "inputs": [],
        "name": "EMPTY_COMMITMENT",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "MAX_ORDER_DURATION",
        "outputs": [{"internalType": "uint32", "name": "", "type": "uint32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "bytes32", "name": "orderHash", "type": "bytes32"},
        ],
        "name": "commit",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "commitment",
        "outputs": [{"internalType": "bytes32", "name": "", "type": "bytes32"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "", "type": "address"},
            {"internalType": "bytes32", "name": "", "type": "bytes32"},
            {"internalType": "bytes", "name": "staticInput", "type": "bytes"},
            {"internalType": "bytes", "name": "", "type": "bytes"},
        ],
        "name": "getTradeableOrder",
        "outputs": [
            {
                "components": [
                    {
                        "internalType": "contract IERC20",
                        "name": "sellToken",
                        "type": "address",
                    },
                    {
                        "internalType": "contract IERC20",
                        "name": "buyToken",
                        "type": "address",
                    },
                    {"internalType": "address", "name": "receiver", "type": "address"},
                    {
                        "internalType": "uint256",
                        "name": "sellAmount",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "buyAmount", "type": "uint256"},
                    {"internalType": "uint32", "name": "validTo", "type": "uint32"},
                    {"internalType": "bytes32", "name": "appData", "type": "bytes32"},
                    {"internalType": "uint256", "name": "feeAmount", "type": "uint256"},
                    {"internalType": "bytes32", "name": "kind", "type": "bytes32"},
                    {
                        "internalType": "bool",
                        "name": "partiallyFillable",
                        "type": "bool",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "sellTokenBalance",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "buyTokenBalance",
                        "type": "bytes32",
                    },
                ],
                "internalType": "struct GPv2Order.Data",
                "name": "",
                "type": "tuple",
            }
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "solutionSettler",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "bytes4", "name": "interfaceId", "type": "bytes4"}],
        "name": "supportsInterface",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "owner", "type": "address"},
            {"internalType": "address", "name": "", "type": "address"},
            {"internalType": "bytes32", "name": "orderHash", "type": "bytes32"},
            {"internalType": "bytes32", "name": "", "type": "bytes32"},
            {"internalType": "bytes32", "name": "", "type": "bytes32"},
            {"internalType": "bytes", "name": "staticInput", "type": "bytes"},
            {"internalType": "bytes", "name": "", "type": "bytes"},
            {
                "components": [
                    {
                        "internalType": "contract IERC20",
                        "name": "sellToken",
                        "type": "address",
                    },
                    {
                        "internalType": "contract IERC20",
                        "name": "buyToken",
                        "type": "address",
                    },
                    {"internalType": "address", "name": "receiver", "type": "address"},
                    {
                        "internalType": "uint256",
                        "name": "sellAmount",
                        "type": "uint256",
                    },
                    {"internalType": "uint256", "name": "buyAmount", "type": "uint256"},
                    {"internalType": "uint32", "name": "validTo", "type": "uint32"},
                    {"internalType": "bytes32", "name": "appData", "type": "bytes32"},
                    {"internalType": "uint256", "name": "feeAmount", "type": "uint256"},
                    {"internalType": "bytes32", "name": "kind", "type": "bytes32"},
                    {
                        "internalType": "bool",
                        "name": "partiallyFillable",
                        "type": "bool",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "sellTokenBalance",
                        "type": "bytes32",
                    },
                    {
                        "internalType": "bytes32",
                        "name": "buyTokenBalance",
                        "type": "bytes32",
                    },
                ],
                "internalType": "struct GPv2Order.Data",
                "name": "order",
                "type": "tuple",
            },
        ],
        "name": "verify",
        "outputs": [],
        "stateMutability": "view",
        "type": "function",
    },
]
