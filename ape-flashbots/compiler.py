from eth_account.signers.local import LocalAccount
from web3.middleware import construct_sign_and_send_raw_middleware

from flashbots import flashbot
from flashbots.types import SignTx
from eth_account.account import Account
from web3 import Web3, HTTPProvider
from web3.types import TxParams, Wei

import os
"""
In this example we setup a transaction for 0.1 eth with a gasprice of 1
From here we will use Flashbots to pass a bundle with the needed content
"""
# "http://localhost:8545"

class EthAccount:

    def __init__(self):
        self.eth_account_signature = Account.from_key(os.environ.get("ETH_SIGNATURE_KEY"))
        self.eth_account_from: LocalAccount = Account.from_key(os.environ.get("ETH_PRIVATE_FROM"))
        self.eth_account_to: LocalAccount = Account.from_key(os.environ.get("ETH_PRIVATE_TO"))
        self.w3 = Web3(HTTPProvider("https://kovan.infura.io/v3/019bb498bd924e2a915f0db51c9c50d1"))
        self.bribe = self.w3.toWei("0.01", "ether")
        self.connect_to_rpc()

    def connect_to_rpc(self):
        print("Connecting to RPC")
        self.w3.middleware_onion.add(construct_sign_and_send_raw_middleware(self.eth_account_from))
        flashbot(self.w3, self.eth_account_signature)
        print(
            f"From account {self.eth_account_from.address}: {self.w3.eth.get_balance(self.eth_account_from.address)}"
        )
        print(
            f"To account {self.eth_account_to.address}: {self.w3.eth.get_balance(self.eth_account_to.address)}"
        )

    def send_request(self):
        print("Sending request")
        params: TxParams = {
            "from": self.eth_account_from.address,
            "to": self.eth_account_to.address,
            "value": self.w3.toWei("1.0", "gwei"),
            "gasPrice": self.w3.toWei("1.0", "gwei"),
            "nonce": self.w3.eth.get_transaction_count(self.eth_account_from.address),
        }
        try:
            tx = self.w3.eth.send_transaction(params,)
            print("Request sent! Waiting for receipt")
        except ValueError as e:
            # Skipping if TX already is added and pending
            if "replacement transaction underpriced" in e.args[0]["message"]:
                print("Have TX in pool we can use for the example")
            else:
                raise

    def flashbot_request(self) -> [list]:
        print("Setting up flashbots request")
        nonce = self.w3.eth.get_transaction_count(self.eth_account_from.address)
        signed_tx: SignTx = {
            "to": self.eth_account_to.address,
            "value": self.bribe,
            "nonce": nonce + 1,
            "gasPrice": 0,
            "gas": 25000,
        }
        signed_transaction = self.eth_account_to.sign_transaction(signed_tx)
        return [
            #  some transaction
            {
                "signer": self.eth_account_from,
                "transaction": {
                    "to": self.eth_account_to.address,
                    "value": Wei(123),
                    "nonce": nonce,
                    "gasPrice": 0,
                },
            },
            # the bribe
            {
                "signed_transaction": signed_transaction.rawTransaction,
            },
        ]

    def complete_transaction(self):
        self.send_request()
        bundle = self.flashbot_request()
        block = self.w3.eth.block_number
        result = self.w3.flashbot.send_bundle(bundle, target_block_number=self.w3.eth.blockNumber + 3)
        result.wait()
        receipts = result.receipts()
        block_number = receipts[0].blockNumber

        # the miner has received the amount expected
        bal_before = self.w3.eth.get_balance(self.eth_account_from.address, block_number - 1)
        bal_after = self.w3.eth.get_balance(self.eth_account_from.address, block_number)
        profit = bal_after - bal_before - self.w3.toWei("2", "ether")  # sub block reward
        print("Balance before", bal_before)
        print("Balance after", bal_after)
        assert profit == self.bribe

        # the tx is successful
        print(self.w3.eth.get_balance(self.eth_account_to.address))


if __name__ == "__main__":
    eth_acc = EthAccount()
    eth_acc.complete_transaction()