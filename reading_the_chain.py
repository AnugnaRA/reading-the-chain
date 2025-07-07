import random
import json
from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware
from web3.providers.rpc import HTTPProvider


# If you use one of the suggested infrastructure providers, the url will be of the form
# now_url  = f"https://eth.nownodes.io/{now_token}"
# alchemy_url = f"https://eth-mainnet.alchemyapi.io/v2/{alchemy_token}"
# infura_url = f"https://mainnet.infura.io/v3/{infura_token}"

def connect_to_eth():
    alchemy_url = "https://eth-mainnet.g.alchemy.com/v2/QgeJ73SopS_ON9aJ1P8EXHMXMxuUBJji"
    w3 = Web3(HTTPProvider(alchemy_url))
    return w3


def connect_with_middleware(contract_json):
    with open(contract_json, 'r') as f:
        contract_data = json.load(f)

    # Automatically detect whether it's a raw ABI array or wrapped in "abi"
    if isinstance(contract_data, list):
        abi = contract_data
    elif isinstance(contract_data, dict) and "abi" in contract_data:
        abi = contract_data["abi"]
    else:
        raise ValueError("ABI not found or improperly formatted")

    # Connect to BNB testnet
    bnb_url = "https://data-seed-prebsc-1-s1.binance.org:8545/"
    w3 = Web3(HTTPProvider(bnb_url))
    w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)

    contract_address = Web3.to_checksum_address("0xaA7CAaDA823300D18D3c43f65569a47e78220073")
    contract = w3.eth.contract(address=contract_address, abi=abi)

    return w3, contract

def is_ordered_block(w3, block_num):
    """
    Takes a block number
    Returns a boolean that tells whether all the transactions in the block are ordered by priority fee

    Before EIP-1559, a block is ordered if and only if all transactions are sorted in decreasing order of the gasPrice field

    After EIP-1559, there are two types of transactions
            *Type 0* The priority fee is tx.gasPrice - block.baseFeePerGas
            *Type 2* The priority fee is min( tx.maxPriorityFeePerGas, tx.maxFeePerGas - block.baseFeePerGas )

    Conveniently, most type 2 transactions set the gasPrice field to be min( tx.maxPriorityFeePerGas + block.baseFeePerGas, tx.maxFeePerGas )
    """
    block = w3.eth.get_block(block_num, full_transactions=True)
    base_fee = block.get("baseFeePerGas", 0)

    def get_priority_fee(tx):
        if "maxPriorityFeePerGas" in tx and "maxFeePerGas" in tx:
            return min(tx["maxPriorityFeePerGas"], tx["maxFeePerGas"] - base_fee)
        elif "gasPrice" in tx:
            return tx["gasPrice"] - base_fee
        else:
            return 0

    fees = [get_priority_fee(tx) for tx in block.transactions]
    ordered = fees == sorted(fees, reverse=True)
    return ordered


def get_contract_values(contract, admin_address, owner_address):
    """
    Takes a contract object, and two addresses (as strings) to be used for calling
    the contract to check current on chain values.

    The provided "default_admin_role" is the correctly formatted solidity default
    admin value to use when checking with the contract.
    """
    default_admin_role = contract.functions.DEFAULT_ADMIN_ROLE().call()

    # Fallbacks in case other functions don't exist in ABI
    try:
        has_role = contract.functions.hasRole(default_admin_role, admin_address).call()
    except:
        has_role = False

    try:
        prime = contract.functions.getPrimeByOwner(owner_address).call()
    except:
        prime = 0

    try:
        onchain_root = contract.functions.merkleRoot().call()
    except:
        onchain_root = None

    return onchain_root, has_role, prime


"""
	This might be useful for testing (main is not run by the grader feel free to change 
	this code anyway that is helpful)
"""
if __name__ == "__main__":
    # These are addresses associated with the Merkle contract (check on contract
    # functions and transactions on the block explorer at
    # https://testnet.bscscan.com/address/0xaA7CAaDA823300D18D3c43f65569a47e78220073
    admin_address = "0xAC55e7d73A792fE1A9e051BDF4A010c33962809A"
    owner_address = "0x793A37a85964D96ACD6368777c7C7050F05b11dE"
    contract_file = "contract_info.json"

    eth_w3 = connect_to_eth()
    cont_w3, contract = connect_with_middleware(contract_file)

    latest_block = eth_w3.eth.get_block_number()
    london_hard_fork_block_num = 12965000
    assert latest_block > london_hard_fork_block_num, f"Error: the chain never got past the London Hard Fork"

    n = 5
    for _ in range(n):
        block_num = random.randint(1, latest_block)
        ordered = is_ordered_block(block_num)
        if ordered:
            print(f"Block {block_num} is ordered")
        else:
            print(f"Block {block_num} is not ordered")
