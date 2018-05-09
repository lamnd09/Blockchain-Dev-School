import hashlib as hasher
from datetime import datetime
from flask import Flask
from flask import request


class Blockchain:
    def __init__(self, index, timestamp, data, previous_hash):
        """

        :param index:
        :param timestamp:
        :param data:
        :param previous_hash:
        """

        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.hash = self.hash_block()

    def hash_block(self):
        sha = hasher.sha256()
        sha.update(str(self.index).encode('utf-8') + str(self.timestamp).encode('utf-8') + str(self.data).encode(
            'utf-8') + str(self.previous_hash).encode('utf-8'))

        return sha.hexdigest()


# Genesis block
def create_genesis_block():
    return Blockchain(0, datetime.now(), "genesis", "0")


def next_block(last_block):
    this_index = last_block.index +1
    this_timestamp = datetime.now()
    this_data = "data" + str(this_index)
    this_hash = last_block.hash
    return Blockchain(this_index, this_timestamp, this_data,this_hash)


# Create a blockchain
blockchain = [create_genesis_block()]
previous_block = blockchain[0]

number_of_blocks = 30

for i in range(0, number_of_blocks):
    block_to_add = next_block(previous_block)
    blockchain.append(block_to_add)
    previous_block = block_to_add

    print(" Block #{} has been added".format(block_to_add.index))
    print(" Hash: #{}\n".format(block_to_add.hash))


node = Flask(__name__)
this_node_transactions = []

@node.route('/txtion', methods=['POST'])

def transaction():
    if request.method == 'POST':
        new_txion = request.get_json()
        this_node_transactions.append(new_txion)

        print(" New Transaction")
        print("From : {} ".format(new_txion['from']))

https://medium.com/crypto-currently/lets-make-the-tiniest-blockchain-bigger-ac360a328f4d