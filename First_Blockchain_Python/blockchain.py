import hashlib
import json
from time import time

class blockchain(object):
	def __init__(self):
		self.current_transaction = []
		self.chain = []

		self.new_block(previous_hash=1, proof=100)


	def new_block(self, proof, previous_hash=None):
		"""
		proof: int , the proof given by the PoW algorithm
		previous_hash: str , hash of previous block
		return : dict, new block

		"""
		block = {
		'index':len(self.chain)+1,
		'timestamp':time(),
		'transaction': self.current_transaction,
		'proof': proof,
		'previous_hash': previous_hash or self.hash(self.chain[-1]),
		}

		#reset current list of transactions
		self.current_transaction[]
		self.chain.append(block)
		return block


	def new_transaction(self, sender, recipient, amount):
		"""
		sender: str, address of sender
		recipient: str, address of receiver
		amount: int, amount
		return: int , the index of the block that will hold the transaction
		"""

		self.current_transaction.append({

			})
