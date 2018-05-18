"""This module defines the logic of the piChain algorithm.
It implements the Node class which represents a node and specifies how it should behave.
"""

import random
import logging
import time
import json

from twisted.internet.task import deferLater

from piChain.PaxosNetwork import ConnectionManager
from piChain.blocktree import Blocktree
from piChain.messages import PaxosMessage, Block, RequestBlockMessage, RespondBlockMessage, Transaction, \
    AckCommitMessage
from piChain.config import ACCUMULATION_TIME, MAX_COMMIT_TIME, MAX_TXN_COUNT, TESTING, RECOVERY_BLOCKS_COUNT


# variables representing the state of a node
QUICK = 0
MEDIUM = 1
SLOW = 2

EPSILON = 0.001

# genesis block
GENESIS = Block(-1, None, [], 0)
GENESIS.depth = 0


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
if not TESTING:
    logging.disable(logging.DEBUG)


class Node(ConnectionManager):
    """This class represents a piChain node. It is a subclass of the ConnectionManager class defined in the networking
    module. This allows to directly call functions like broadcast and respond from the networking module and to override
    the receive-methods which are called in the networking module based on the type of the message.

    Args:
        node_index (int): the index of this node into the peers dictionary. The entry defines its ip address and port.
        peers_dict (dict): a dict containing the (ip, port) pairs for all nodes (see examples folder for its structure).

    Attributes:
        state (int): 0,1 or 2 corresponds to QUICK, MEDIUM or SLOW.
        blocktree (Blocktree): The blocktree which this node owns.
        known_txs (set): all txs seen so far. Set of txn ids.
        new_txs (list): txs not yet in a block, behaving like a queue.
        oldest_txn (Transaction): txn which started a timeout.
        s_max_block_depth (int):  depth of deepest block seen in round 1 (like T_max).
        s_prop_block (Block): stored block from a valid propose message.
        s_supp_block (Block): block supporting proposed block (like T_store).
        c_new_block (Block): block which client (a quick node) wants to commit next.
        c_com_block (Block): temporary compromise block.
        c_request_seq (int): voting round number.
        c_votes (int): used to check if majority is already reached.
        c_prop_block (Block): propose block with deepest support block the client has seen in round 2.
        c_supp_block (Block): support block supporting c_prop_block.
        c_quick_proposing (bool): a node may skip round 1 if his ticket is still valid.
        c_commit_running (bool): True if a commit currently running.
        c_current_committable_block (Block): block to still be committed
        tx_committed (Callable): method given by app service that is called once a transaction has been committed.
        rtts (dict): Mapping from peer_node_id to RTT. Used to estimate expected round trip time.
        expected_rtt (float): based on this rtt the timeouts are computed.
        slow_timeout_backoff (float): fix additional timeout backoff of a slow node (u.a.r only set once).
        n (int): total numberof nodes.
        retry_commit_timeout_queued (bool): is there a timeout in queue that will retry to commit.
    """
    def __init__(self, node_index, peers_dict):

        super().__init__(node_index, peers_dict)

        self.state = SLOW

        # ensure that exactly one node will be QUICK in beginning
        if self.id == 0:
            self.state = QUICK

        self.blocktree = Blocktree(node_index)

        # Transaction variables
        self.known_txs = set()
        self.new_txs = []
        self.oldest_txn = None

        # node acting as server
        self.s_max_block_depth = 0
        self.s_prop_block = None
        self.s_supp_block = None

        # node acting as client
        self.c_new_block = None
        self.c_com_block = None
        self.c_request_seq = 0
        self.c_votes = 0
        self.c_prop_block = None
        self.c_supp_block = None
        self.c_quick_proposing = False
        self.c_commit_running = False
        self.c_current_committable_block = None

        self.tx_committed = None

        # timeout/timing variables
        self.rtts = {}
        self.expected_rtt = 1
        self.slow_timeout_backoff = None
        self.retry_commit_timeout_queued = False

        self.n = len(self.peers)

        # load server variables (after crash)
        for key, value in self.blocktree.db:
            if key == b's_max_block_depth':
                self.s_max_block_depth = int(value.decode())
            elif key == b's_prop_block':
                block = self.blocktree.nodes.get(int(value.decode()))
                self.s_prop_block = block
            elif key == b's_supp_block':
                block = self.blocktree.nodes.get(int(value.decode()))
                self.s_supp_block = block

    def receive_paxos_message(self, message, sender):
        """React on a received paxos `message`. This method implements the main functionality of the paxos algorithm.

        Args:
            message (PaxosMessage): Message received.
            sender (Connection): Connection instance of the sender (None if sender is this Node).
        """
        logger.debug('receive message type = %s', message.msg_type)
        if message.msg_type == 'TRY':
            # make sure last commited block of sender is also committed by this node
            if message.last_committed_block not in self.blocktree.committed_blocks:
                last_committed_block = self.get_block(message.last_committed_block)
                if last_committed_block is None:
                    return
                self.commit(last_committed_block)

            # make sure that message.new_block is descendant of last committed block
            new_block = self.get_block(message.new_block)
            if new_block is None:
                return
            if not self.reach_genesis_block(new_block):
                # first need to request some missing blocks to be able to decide
                return

            if not self.blocktree.ancestor(self.blocktree.committed_block, new_block):
                # new_block is not a descendent of last committed block thus we reject it
                return

            if self.s_max_block_depth < new_block.depth:
                self.s_max_block_depth = new_block.depth

                # write changes to disk (add s_max_block_depth)
                self.blocktree.db.put(b's_max_block_depth', str(self.s_max_block_depth).encode())

                # create a TRY_OK message
                try_ok = PaxosMessage('TRY_OK', message.request_seq)
                if self.s_prop_block is not None:
                    try_ok.prop_block = self.s_prop_block.block_id
                if self.s_supp_block is not None:
                    try_ok.supp_block = self.s_supp_block.block_id
                if sender is not None:
                    self.respond(try_ok, sender)
                else:
                    self.receive_paxos_message(try_ok, None)

        elif message.msg_type == 'TRY_OK':
            # check if message is not outdated
            if message.request_seq != self.c_request_seq:
                # outdated message
                logger.debug('TRY_OK outdated')
                return

            # if TRY_OK message contains a propose block, we will support it if it is the first received
            # or if its support block is deeper than the one already stored.
            supp_block = self.get_block(message.supp_block)
            prop_block = self.get_block(message.prop_block)

            if supp_block and self.c_supp_block is None:
                self.c_supp_block = supp_block
                self.c_prop_block = prop_block
            elif supp_block and self.c_supp_block and self.c_supp_block < supp_block:
                self.c_supp_block = supp_block
                self.c_prop_block = prop_block

            self.c_votes += 1
            if self.c_votes > self.n / 2:

                # start new round
                self.c_votes = 0
                self.c_request_seq += 1

                # the compromise block will be the block we are going to propose in the end
                self.c_com_block = self.c_new_block

                # check if we need to support another block instead of the new block
                if self.c_prop_block:
                    self.c_com_block = self.c_prop_block

                # create PROPOSE message
                propose = PaxosMessage('PROPOSE', self.c_request_seq)
                propose.com_block = self.c_com_block.block_id
                propose.new_block = self.c_new_block.block_id

                self.broadcast(propose, 'PROPOSE')
                self.receive_paxos_message(propose, None)

        elif message.msg_type == 'PROPOSE':
            # if did not receive a try message with a deeper new block in mean time can store proposed block on server
            new_block = self.get_block(message.new_block)
            if new_block is None:
                return
            com_block = self.get_block(message.com_block)
            if com_block is None:
                return
            if new_block.depth == self.s_max_block_depth:
                self.s_prop_block = com_block
                self.s_supp_block = new_block

                # write changes to disk (add s_prop_block and s_supp_block)
                if self.s_prop_block is not None:
                    block_id_bytes = str(self.s_prop_block.block_id).encode()
                    self.blocktree.db.put(b's_prop_block', block_id_bytes)

                if self.s_supp_block is not None:
                    block_id_bytes = str(self.s_supp_block.block_id).encode()
                    self.blocktree.db.put(b's_supp_block', block_id_bytes)

                # create a PROPOSE_ACK message
                propose_ack = PaxosMessage('PROPOSE_ACK', message.request_seq)
                propose_ack.com_block = message.com_block

                if sender is not None:
                    self.respond(propose_ack, sender)
                else:
                    self.receive_paxos_message(propose_ack, None)

        elif message.msg_type == 'PROPOSE_ACK':
            # check if message is not outdated
            if message.request_seq != self.c_request_seq:
                # outdated message
                return

            self.c_votes += 1
            if self.c_votes > self.n / 2:
                # ignore further answers
                self.c_request_seq += 1

                # create commit message
                com_block = self.get_block(message.com_block)
                if com_block is None:
                    return
                commit = PaxosMessage('COMMIT', self.c_request_seq)
                commit.com_block = message.com_block
                self.broadcast(commit, 'COMMIT')
                self.commit(com_block)

                # allow new paxos instance
                self.c_commit_running = False
                self.c_quick_proposing = True

        elif message.msg_type == 'COMMIT':
            com_block = self.get_block(message.com_block)
            if com_block is None:
                return
            self.commit(com_block)

    def receive_transaction(self, txn):
        """React on a received `txn` depending on state.

        Args:
            txn (Transaction): Transaction received.
        """
        # check if txn has already been seen
        if txn.txn_id not in self.known_txs:
            logger.debug('txn has not yet been seen')
            # add txn to set of seen txs
            self.known_txs.add(txn.txn_id)

            # timeout handling
            self.new_txs.append(txn)
            if len(self.new_txs) == 1:
                self.oldest_txn = txn
                # start a timeout
                logger.debug('start timeout')
                deferLater(self.reactor, self.get_patience(), self.timeout_over, txn)
        else:
            logger.debug('txn has already been seen')

    def receive_block(self, block):
        """React on a received `block`.

        Args:
            block (Block): Received block.
        """
        # make sure block is reachable
        if not self.reach_genesis_block(block):
            logger.debug('block not reachable')
            return

        # demote node if necessary
        if self.blocktree.head_block < block or block.creator_state == QUICK:
            if self.state != SLOW:
                logger.debug('Demoted to slow. Previous State = %s', str(self.state))
            self.state = SLOW
            self.c_quick_proposing = False

        if not self.blocktree.valid_block(block):
            logger.debug('block invalid')
            return

        self.move_to_block(block)

        # timeout readjustment
        self.readjust_timeout()

    def receive_request_blocks_message(self, req, sender):
        """A node is missing a block. Send him the missing block if we have it. Also send him a predefined number
        (=RECOVERY_BLOCKS_COUNT given in config.py) of ancestors of the missing block s.t he can recover faster in case
        he is missing more blocks.

        Args:
            req (RequestBlockMessage): Message that requests a missing block.
            sender (Connection): Connection instance form the sender.
        """
        if self.blocktree.nodes.get(req.block_id) is not None:
            blocks = [self.blocktree.nodes.get(req.block_id)]

            # add five ancestors to blocks
            b = self.blocktree.nodes.get(req.block_id)
            i = 0
            while i < RECOVERY_BLOCKS_COUNT and b is not None and b != self.blocktree.genesis:
                i = i + 1
                b = self.blocktree.nodes.get(b.parent_block_id)
                if b is not None and b != self.blocktree.genesis:
                    blocks.append(b)

            # send blocks back
            respond = RespondBlockMessage(blocks)
            self.respond(respond, sender)

    def receive_respond_blocks_message(self, resp):
        """Receive the blocks that are missing from a peer. Can directly be added to `self.nodes`.

        Args:
            resp (RespondBlockMessage): may contain the missing blocks s.t the node can recover.
        """
        blocks = resp.blocks
        for b in blocks:
            self.blocktree.add_block(b)

    def receive_pong_message(self, message, peer_node_id):
        """Receive PongMessage and update RRT's accordingly.

        Args:
            message (PongMessage): Received PongMessage
            peer_node_id (str): uuid of peer who send the pong message

        """
        rtt = round(time.time() - message.time, 3)  # in seconds
        logger.debug('PongMessage received, rtt = %s', str(rtt))

        # update RTT's
        self.rtts.update({peer_node_id: rtt})
        self.expected_rtt = max(self.rtts.values()) + 0.1

    def receive_ack_commit_message(self, message):
        """Check if all nodes acknowledged this block, if true make it the new genesis block and delete the blocks
        below the new genesis block from db and blocktree.

        Note: A node may miss acks because he is down and then once online again, if he commits the missed blocks, the
        other nodes will perform a genesis block change while he doesn't. No problem since a temporary inconsistency
        between genesis blocks does not matter.

        Args:
            message (AckCommitMessage): Received AckCommitMessage.
        """
        # update the count how many times the block has been committed
        block_id = message.block_id
        old_count = self.blocktree.ack_commits.get(block_id)
        if old_count is None:
            self.blocktree.ack_commits.update({block_id: 1})
        else:
            new_count = old_count + 1
            self.blocktree.ack_commits.update({block_id: new_count})

        # check if all nodes have committed this block
        if self.blocktree.ack_commits.get(block_id) == self.n:
            logger.debug('perform genesis block change')

            # this block will be the new genesis block
            self.blocktree.genesis = self.blocktree.nodes.get(block_id)
            logger.debug('new genesis block id = %s', str(self.blocktree.genesis.block_id))

            # write it to db
            block_id_bytes = str(self.blocktree.genesis.block_id).encode()
            self.blocktree.db.put(b'genesis', block_id_bytes)

            # delete inside blocktree.nodes dict and on disk
            parent = self.blocktree.genesis
            while parent is not None and parent.parent_block_id is not None:
                parent_block_id = parent.parent_block_id
                self.blocktree.db.delete(str(parent_block_id).encode())
                parent = self.blocktree.nodes.pop(parent_block_id, None)
                # also delete txns
                if parent is not None:
                    for txn in parent.txs:
                        self.known_txs.discard(txn.txn_id)

            self.blocktree.nodes.update({GENESIS.block_id: GENESIS})

            # force deletion in leveldb
            self.blocktree.db.compact_range()

    def move_to_block(self, target):
        """Change to `target` block as new `head_block`. If `target` is found on a forked path, have to broadcast txs
         that wont be on the path from `GENESIS` to new `head_block` anymore.

        Args:
            target (Block): will be the new `head_block`.
        """
        # make sure target is reachable
        if not self.reach_genesis_block(target):
            return

        if (not self.blocktree.ancestor(target, self.blocktree.head_block)) and target != self.blocktree.head_block:
            common_ancestor = self.blocktree.common_ancestor(self.blocktree.head_block, target)
            to_broadcast = set()
            # go from head_block to common ancestor: add txs to to_broadcast
            b = self.blocktree.head_block
            while b != common_ancestor:
                to_broadcast |= set(b.txs)
                b = self.blocktree.nodes.get(b.parent_block_id)
            # go from target to common ancestor: remove txs from to_broadcast and new_txs, add to known_txs
            b = target
            while b != common_ancestor:
                for tx in b.txs:
                    self.known_txs.add(tx.txn_id)
                for tx in b.txs:
                    if tx in self.new_txs:
                        self.new_txs.remove(tx)
                to_broadcast -= set(b.txs)
                b = self.blocktree.nodes.get(b.parent_block_id)

            # target is now the new head_block
            self.blocktree.head_block = target

            # write changes to disk (add headblock)
            block_id_bytes = str(target.block_id).encode()
            self.blocktree.db.put(b'head_block', block_id_bytes)

            # broadcast txs in to_broadcast
            for tx in to_broadcast:
                self.broadcast(tx, 'TXN')
            self.readjust_timeout()

    def commit(self, block):
        """Commit `block`.

        Args:
            block (Block): Block to be committed.

        """
        if block.block_id in self.blocktree.committed_blocks:
            return

        # make sure block is reachable
        if not self.reach_genesis_block(block):
            return

        if not self.blocktree.ancestor(block, self.blocktree.committed_block) and \
           block != self.blocktree.committed_block:
            if block.creator_id != self.id:
                self.c_quick_proposing = False

            last_committed_block = self.blocktree.committed_block
            self.blocktree.committed_block = block
            self.move_to_block(block)

            # write changes to disk (add committed block)
            block_id_bytes = str(block.block_id).encode()
            self.blocktree.db.put(b'committed_block', block_id_bytes)

            # broadcast confirmation of committing this block
            acm = AckCommitMessage(block.block_id)
            self.broadcast(acm, 'ACM')
            self.receive_ack_commit_message(acm)

            # iterate over blocks from currently committed block to last committed block
            # need to commit all those blocks (not just currently committed block)
            block_list = []
            b = self.blocktree.committed_block
            while b != last_committed_block:
                block_list.append(b)
                b = self.blocktree.nodes.get(b.parent_block_id)
                if b is None:
                    logger.debug('block to be committed is not descendent of last committed block -> error')
                    return

            block_list.reverse()

            for b in block_list:
                # write committed block to stdout (-> testing purpose)
                print('block = %s:', str(b.block_id))

                self.blocktree.committed_blocks.append(b.block_id)
                # write changes to disk
                block_ids_str = json.dumps(self.blocktree.committed_blocks)
                block_ids_bytes = block_ids_str.encode()
                self.blocktree.db.put(b'committed_blocks', block_ids_bytes)

                logger.debug('committing a block: with block id = %s', str(b.block_id))
                logger.debug('committed blocks so far: %s', str(self.blocktree.committed_blocks))

                # call callable of app service
                commands = []
                for txn in b.txs:
                    commands.append(txn.content)
                if self.tx_committed is not None:
                    self.tx_committed(commands)

            # reinitialize server variables
            self.s_supp_block = None
            self.s_prop_block = None
            self.s_max_block_depth = 0
            self.c_commit_running = False

            # write changes to disk (delete s_max_block, s_prop_block and s_supp_block)
            self.blocktree.db.delete(b's_max_block_depth')
            self.blocktree.db.delete(b's_prop_block')
            self.blocktree.db.delete(b's_supp_block')

    def reach_genesis_block(self, block):
        """Check if there is a path from `block` to `GENESIS` block. If a block on the path is not contained in
        `self.nodes`, we need to request it from other peers.
        This may happen because of a network partition or if a node is down for a period of time.

        Args:
            block (Block): From this block we want to find a path to GENESIS block.

        Returns:
            bool: True if `GENESIS` block was reached.
        """
        self.blocktree.add_block(block)
        b = block
        while b != self.blocktree.genesis:
            if self.blocktree.nodes.get(b.parent_block_id) is not None:
                b = self.blocktree.nodes.get(b.parent_block_id)
            else:
                req = RequestBlockMessage(b.parent_block_id)
                self.broadcast(req, 'RQB')
                return False
        return True

    def create_block(self):
        """Create a block containing `new_txs` and return it.

        Returns:
            Block: The block that was created.

        """
        logger.debug('create a block')
        # store depth of current head_block (will be parent of new block)
        d = self.blocktree.head_block.depth

        # create block
        self.blocktree.counter += 1
        if len(self.new_txs) < MAX_TXN_COUNT:
            b = Block(self.id, self.blocktree.head_block.block_id, self.new_txs, self.blocktree.counter)
            # create a new, empty list (do not use clear!)
            self.new_txs = []
        else:
            logger.debug('Cannot fit all transactions in the block that is beeing created. Remaining transactions '
                         'will be included in the next block.')
            txns_include = self.new_txs[:MAX_TXN_COUNT]
            b = Block(self.id, self.blocktree.head_block.block_id, txns_include, self.blocktree.counter)
            self.new_txs = self.new_txs[MAX_TXN_COUNT:]
            self.readjust_timeout()

        # compute its depth (will be fixed -> depth field is only set once)
        b.depth = d + len(b.txs)

        self.blocktree.db.put(b'counter', str(self.blocktree.counter).encode())

        # add block to blocktree
        self.blocktree.add_block(b)

        # promote node
        if self.state != QUICK:
            self.state = max(QUICK, self.state - 1)
            logger.debug('Got promoted. State = %s', str(self.state))

        # add state of creator node to block
        b.creator_state = self.state

        logger.debug('created block with block id = %s', str(b.block_id))

        return b

    def get_patience(self):
        """Returns the time a node has to wait before creating a new block.
        Corresponds to the nodes eagerness to create a new block.

        Returns:
            int: time node has to wait.

        """
        if self.state == QUICK:
            patience = 0

        elif self.state == MEDIUM:
            patience = (1 + EPSILON) * self.expected_rtt

        else:
            # compute a random backoff time for each slow node and fix it. This ensures that only one slow node will
            # create a block in expectation
            if self.slow_timeout_backoff is None:
                self.slow_timeout_backoff = random.uniform(0, self.n) * 0.5

            patience = (2. + EPSILON) * self.expected_rtt + self.slow_timeout_backoff * self.expected_rtt

        return patience + ACCUMULATION_TIME

    def timeout_over(self, txn):
        """This function is called once a timeout is over. Will check if in the meantime the node received
        the `txn`. If not it is allowed to ceate a new block and broadcast it.

        Args:
            txn (Transaction): This transaction triggered the timeout.

        """
        logger.debug('timeout_over called')
        if txn in self.new_txs:
            # create a new block
            b = self.create_block()
            self.move_to_block(b)
            self.broadcast(b, 'BLK')
            self.c_current_committable_block = b
            self.start_commit_process()

    def start_commit_process(self):
        """Commit `self.current_committable_block`."""
        self.retry_commit_timeout_queued = False

        if self.c_current_committable_block.block_id in self.blocktree.committed_blocks:
            # this block has already been committed
            return

        #  if quick node then start a new instance of paxos
        if self.state == QUICK and not self.c_commit_running:
            logger.debug('start an new instance of paxos')
            self.c_commit_running = True
            self.c_votes = 0
            self.c_request_seq += 1
            self.c_supp_block = None
            self.c_prop_block = None

            # set commit_running to False if after expected time needed for commit process still equals True
            deferLater(self.reactor, 2 * self.expected_rtt + MAX_COMMIT_TIME, self.commit_timeout, self.c_request_seq)

            if not self.c_quick_proposing:
                self.c_new_block = self.c_current_committable_block

                # create try message
                try_msg = PaxosMessage('TRY', self.c_request_seq)
                try_msg.last_committed_block = self.blocktree.committed_block.block_id
                try_msg.new_block = self.c_new_block.block_id
                self.broadcast(try_msg, 'TRY')
                self.receive_paxos_message(try_msg, None)
            else:
                logger.debug('quick proposing')
                # create propose message directly
                propose = PaxosMessage('PROPOSE', self.c_request_seq)
                propose.com_block = self.c_current_committable_block.block_id
                propose.new_block = GENESIS.block_id
                self.broadcast(propose, 'PROPOSE')
                self.receive_paxos_message(propose, None)

        elif self.state == QUICK and self.c_commit_running:
            # try to commit block later
            logger.debug('commit is already running, try to commit later')
            if not self.retry_commit_timeout_queued:
                self.retry_commit_timeout_queued = True
                deferLater(self.reactor, 2 * self.expected_rtt + MAX_COMMIT_TIME, self.start_commit_process)

    def readjust_timeout(self):
        """Is called if `new_txs` changed and thus the `oldest_txn` may be removed."""
        if len(self.new_txs) != 0 and self.new_txs[0] != self.oldest_txn:
                self.oldest_txn = self.new_txs[0]
                # start a new timeout
                deferLater(self.reactor, self.get_patience(), self.timeout_over, self.new_txs[0])

    def commit_timeout(self, commit_counter):
        """Is called once a commit should have been finished. If it is still running, it will be 'terminated'. """
        if self.c_commit_running and self.c_request_seq == commit_counter:
            self.c_commit_running = False
            self.c_quick_proposing = False
            logger.debug('current commit terminated because did not receive enough acknowlegements')
            logger.debug('try to commit again')
            self.start_commit_process()

    def get_block(self, block_id):
        """Get block based on block_id.

        Args:
            block_id (int): block id of the requested block.

        Returns (Block): requested block. If not stored locally return None.

        """
        if block_id is None:
            return None
        b = self.blocktree.nodes.get(block_id)
        if b is None:
            req = RequestBlockMessage(block_id)
            self.broadcast(req, 'RQB')
        return b

    # methods used by the app (part of external interface)

    def make_txn(self, command):
        """This method is called by the app with the command to be committed.

        Args:
            command (str): command to be commited
        """
        self.blocktree.counter += 1
        txn = Transaction(self.id, command, self.blocktree.counter)
        self.blocktree.db.put(b'counter', str(self.blocktree.counter).encode())
        self.broadcast(txn, 'TXN')
