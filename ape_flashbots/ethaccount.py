from decouple import config
from eth_account.account import Account
from flashbots import flashbot
from web3 import HTTPProvider, Web3
from web3.middleware import construct_sign_and_send_raw_middleware, geth_poa_middleware
from web3.types import TxParams, Wei

"""
In this example we setup a transaction for 0.1 eth with a gasprice of 1
From here we will use Flashbots to pass a bundle with the needed content
"""

from typing import TYPE_CHECKING

from eth_account import Account, messages

if TYPE_CHECKING:
    from eth_account.signers.local import LocalAccount
    from flashbots.types import SignTx


class EthAccount:
    def __init__(self):
        self.eth_account_signature = Account.from_key(config("ETH_SIGNATURE_KEY"))
        self.eth_account_from: LocalAccount = Account.from_key(config("ETH_PRIVATE_FROM"))
        self.eth_account_to: LocalAccount = Account.from_key(config("ETH_PRIVATE_TO"))
        self.body = '{"id": 1234, "method", "eth_sendBundle", "params": [["0x123..."], "0xB84969"]}'
        self.message = messages.encode_defunct(text=Web3.keccak(text=self.body).hex())
        self.signed_message = Account.sign_message(
            self.message, private_key=self.eth_account_signature.key
        )
        self.w3 = Web3(HTTPProvider("https://relay-goerli.flashbots.net"))
        self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
        self.bribe = self.w3.toWei("0.0001", "ether")
        self.connect_to_rpc()

    def connect_to_rpc(self):
        self.w3.middleware_onion.add(construct_sign_and_send_raw_middleware(self.eth_account_from))
        flashbot(self.w3, self.eth_account_signature)

    def send_request(self):
        params: TxParams = {
            "from": self.eth_account_from.address,
            "to": self.eth_account_to.address,
            "value": self.w3.toWei("90.0", "gwei"),
            "gasPrice": self.w3.toWei("90.0", "gwei"),
            "nonce": self.w3.eth.get_transaction_count(self.eth_account_from.address),
        }
        try:
            self.w3.eth.send_transaction(
                params,
            )
        except ValueError as e:
            # Skipping if TX already is added and pending
            if "replacement transaction underpriced" in e.args[0]["message"]:
                pass
            else:
                raise

    def flashbot_request(self) -> [list]:
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
        result = self.w3.flashbots.send_bundle(
            bundle, target_block_number=self.w3.eth.blockNumber + 3
        )
        result.wait()
        receipts = result.receipts()
        block_number = receipts[0].blockNumber

        # the miner has received the amount expected
        bal_before = self.w3.eth.get_balance(self.eth_account_from.address, block_number - 1)
        bal_after = self.w3.eth.get_balance(self.eth_account_from.address, block_number)
        profit = bal_after - bal_before - self.w3.toWei("2", "ether")  # sub block reward
        assert profit == self.bribe

        # the tx is successful


if __name__ == "__main__":
    eth_acc = EthAccount()
    eth_acc.complete_transaction()
