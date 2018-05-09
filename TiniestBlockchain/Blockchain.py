import hashlib as hasher
import datetime as date

class Block:
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
            sha.update(str(self.index) +
                       str(self.timestamp)+
                       str(self.data) +
                       str(self.previous_hash))
            return sha.hexdigest()


# Genesis block
def create_genesis_block():
    return Block(0, date.datetime.now(), "genesis", "0")



