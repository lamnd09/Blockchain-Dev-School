import hashlib
import json
from time import time
from textwrap import dedent

from uuid import uuid4
from flask import Flask
from flask import jsonify, request
from urllib.parse import urlparse

class Blockchain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        # create the genesis block
        self.new_block(previous_hash = 1, proof=100)


    def new_transaction(self,sender, receiver, amount):
        """

        :param sender: <str> address of sender
        :param receiver: <str> address of reciver
        :param amount: int Amount
        :return: int The index of the block that will hold this transaction
        """

        self.current_transactions.append({
            'sender': sender,
            'receiver': receiver,
            'amount': amount,
        })

        return self.last_block['index']+1

    def new_block(self, proof, previous_hash=None):
        """
        Create a new block in the blockchain

        :param proof: Int - The proof given by the PoW algorithm
        :param previous_hash: std - Hash of previous block
        :return: dict - new block
        """
        block = {
            'index': len(self.chain)+1,
            'timestamp': time(),
            'transaction': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1]),
        }

        # reset the current list of transactions
        self.current_transactions = []
        self.chain.append(block)

        return block


    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        """
        creates a SHA-256 hash of a block

        :param block: dict - block
        :return: str
        """
        block_string = json.dump(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()


    def proof_of_work(self, last_proof):
        """
        simple proof of work algorithm
        - Find a number p' such that hash(pp') contains leadding 4 zeros, where p is the previous
        - p is the previous proof, and p' is the new proof

        :param last_proof: int
        :return: int
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof = proof + 1

        return proof

    def register_node(self, address):
        """
        Add a new node to the list of nopde
        :param address: Address of node
        :return:
        """
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')


    def valid_chain(self, chain):
        """
        Consider whether a given chain  is valid
        :param chain: a blockcgain
        :return: True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]

            print(f'{last_block}')
            print(f'{block}')
            print("\n ")

            # Check that the hash of the block is correct
            last_block_hash = self.hash(last_block)
            if block['previous_hash'] !=last_block_hash:
                    return False

            #check that the Proof_of_Work is correct
            if not self.valid_proof(last_block['proof'], block['proof'], last_block_hash):
                return False

            last_block=block
            current_index = current_index +1

        return True


    def resolve_conflicts(self):
        """
        Consensus algorithm, it resolves conflicts by replacing our chain with the longest one in the network.
        :return: True if our chain was relaced, false if not
        """

        neighbors = self.nodes
        new_chain = None

        # looking for the chains longer
        max_length = len(self.chain)

        #grab and verify the chains from all the nodes in our network
        for node in neighbors:
            response = request.get(f'htt[://{node}/chain')
            if response.status_code ==200:
                length = response.json()['length']
                chain = response.json()['chain']

                #Check if the length is longer and the chain is valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if we discover a new, valid chain longer than ours
        if new_chain:
            self.chain = new_chain
            return True

        return False





    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validate the Proof: Does hash(last_proof, proof) contain 4 leading zeros
        :param last_proof:  previous proof
        :param proof:  current proof
        :return:  true if correct, false if not
        """

        guess = f'{last_proof}{proof}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] =="0000"



# Instantiate the node
app = Flask(__name__)

#Genrate a gloobal unique address for the node
node_identifier = str(uuid4()).replace('-','')

# Instantiate the blockchain

blockchain = Blockchain()

@app.route('/mine', methods = ['GET'])

# The mining endpoint has to do three things:
#1  Calculate the PoW
#2 Reward the miner by adding a transaction granting 1 coin
#3 Forge the new block by adding to chain


def mine():
    # Run the PoW to get the next Proof
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)

    #we must receive a reward for fiding the proof
    #the sender is '0' to signify that this node has mined a new coin
    blockchain.new_transaction(
        sender = "0",
        receiver= node_identifier,
        amount=1,
    )


    # Forge the new block by adding to the chain
    previous_hash = blockchain.blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "new Block forged",
        'index': block['index'],
        'transactions': block['transaction'],
        'proof':block['proof'],
        'previous_hash':block['previous_hash'],
    }

    return jsonify(response),200

@app.route('/transactions/new', methods = ['POST'])
def new_transaction():
    values = request.get_json()

    #Check that the required fields are in the Post data
    required = ['sender', 'receiver', 'amount' ]
    if not all(k in values for k in required):
        return 'Missing values',400

    # Create a new transaction
    index = blockchain.new_transaction(values['sender'], values['receiver'], values['amount'])

    response = {'message': f'Transaction will be added to Block {index}'}
    return jsonify(response),201


@app.route('/chain', methods= ['GET'])
def full_chain():
    respone = {
        'chain': blockchain.chain,
        'length':len(blockchain.chain)
    }
    return jsonify(respone),200

@app.route('/nodes/register', methods = ['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')

    if nodes is None:
        return "Error: Please supply a valid list of nodes",400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'new nodes have been added',
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response),201

@app.route('/nodes/resolve', methods = ['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'blockchain was replaced',
            'chain': blockchain.chain
        }
    else:
        response = {
            'message': 'chain is authoritative',
            'chain': blockchain.chain
        }

    return jsonify(response),200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default = 6000, type=int, help='port listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='127.0.0.1', port=port)






