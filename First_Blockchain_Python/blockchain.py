import hashlib
import json
from time import time 

class blockchain(object):
	def __init__(self):
		self.current_transaction = []
		self.chain = []

		self.new_block(previous_hash=1, proof=100)

	