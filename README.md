# BlockchainIoT

If you really want to study blockchain and cryptocurrency world, I would like to recommend that you start your journey by reading two very important white papers: 
- Bitcoin: A Peer-to-Peer Electronic Cash System
- Ethereum: A Next-Generation Smart Contract and Decentralized Application Platform


The basic course of Blockchain and Bitcoin on Coursera. 
- Week 1: Introduction to Crypto and Cryptocurrencies 
- Week 2: How Bitcoin Achieves Decentralization 
- Week 3: Mechanis of Bitcoin
- Week 4: Howto Store and Use Bitcoins
- Week 5: Bitcoin Mining 
- Week 6: Bitcoin and Anonymity 
- Week 7: Community, Politics and Regulation 
- Week 8: Alternative Mining Puzzles 
- Week 9: Bitcoin as a Platform
- Week 10: Altcoins and Cryptocurrency Ecosystem
- Week 11: The Future of Bitcoin  ? 

# Basic Knowledge of Blockchain Technology: 
# 1. Principles of Bitcoin and Ethereum 
# 2. Nakamoto Consensus
- It's now clear that anyone that wanted to builded a digital currency at the beginning of this century had to find a way to make it decentralized, hard to attack and with a real, intrinsic value. And in 2008, Satoshi Nakamoto was able to deliver all of this in a peer to peer network, a shared data strucuture blockchain which a set of rules we call Nakamoto Consensus. 
- All of the Bitcoin design is based on the premise that external and internal rational agents have an incentive to destroy or attempt to destroy the network or rob one another to increase their profits or to avoids any losses. On these premises, which are quite realistic, a simple p2 network would have never been useful. 
-  The nakamoto consensus includes a set of rules, most of which regard transaction's validation and transaction's blocks. The latter are transaction groups close in time, cryptographyically concatenated to compose the blockchain. Despite their importantance, there are not the set of rules that gurantee the security and value of the Bitcoin blockchain. Those are mining, deflation trend and block selection rules. 
- Mining is the process through Bitcoins get created. It is a proof-of-work simular to RPOW, and its difficulty increases with the usage of the network. The process is strictly related to the creation of new blocks, and the proceduced bitcoin quantity is recognised only by the approval of the associated block. Nodes that can "mine" bitcoin, earn the mined quantity, but with time this quantity diminishes, up to a point where the netwok will have proceduced 21M bitcoins. Block selection rules deal with choosing which one to add to the blockchain. With Bitcoin, the blocks are selected to obtain the blockchain withn the higher amount of work, meaning the most computing time spent in the mining process. 
- How can these simple rules guarantee the security of the network and the bitcoin value? 
With Bitcoin, anyone can host a node and connect to the network. Nodes are anonnymous to make them harder to target and compromise. In an open an anonymous environment it's not possible to punish single nodes for malicious behavior, so it has to be discouraged. 
The mining process is stochastic, so it’s not possible to accurately know who will find the solution, even if the increasing difficulty of the process makes the amount of nodes able to carry out the calculations smaller. This makes mining like a lottery where participation costs are always increasing. This discourages all agents not willing to invest economic value from participating to the game. While the usage increases, and thus the value, the difficulty increases as well, discouraging anyone who wants to compromise the network. Furthermore, the increasing value forces the “honest” agents to invest more in securing their nodes and, consequently, the network.
The validation rules make sure that no honest agent is going to accept malformed blocks, because this would damage the whole network. Block selection rules make sure that only valid blocks that have enough work invested into (as in computational resources) are accepted. Even if malicious nodes wanted to promote a blockchain that benefits them, this would require an ever increasing need of resources, and consequently economic resources as well. The produced blockchain would then have to compete with blockchains produced in years and with a high amount of other very competitive nodes. This conditions secure the network, which in turn strengthens the value of the currency, given the deflations and the costs of computational resources (CPU, storage, …) and consequently economic resources (users, servers) of the mining process.

What does this have to do with mechanism design?
The mining process of Bitcoin is variant of what we call random serial dictatorship in mechanism design.
One of the most important problems in mechanism design is the resource allocation (houses, contracts, work, etc). In these cases, each agent has informations about its own preferences, which once revealed, could make it easier to execute the mechanism. Sadly, this is often not enough, because actors’ preferences are very similar if not identical between them. In these cases the best strategy is to use a random allocation.
The random serial dictatorship means that for each iteration a “dictator” gets randomly chosen and it decides what to do based on the informations it posses. It’s a random variant of the serial dictatorship. The latter sorts through a list of “dictators” based on an arbitrary (but not random) criteria, creating equity problems and increasing the probability of defection o missing participation from actor that could otherwise have participated. Bitcoin adds to this mechanism a preselection-based costly commitment.

Mining is expensive and its cost will increase as the network acquires a higher economic value. Without a similar mechanism, anyone would have an incentive to propose oneself as “dictator”, even with malicious intent or without having the capacity and requirements to secure the network.
Bitcoin forces agents that want to mine to reveal their willingness to become candidates by spending resources that may not be recovered, since the “dictator” selection mechanism is random.
In turn, deflation reinforces this mechanism, since it ensures that participants that won the lottery in the past used resources that will have a higher value in the future, as long as the network works.
The game theory shows us how it’s not possible to guarantee the resolution of non-cooperative games using just one iteration, but with sequential games (meaning more than one interaction), there are a number of possible strategies to line up incentives. The majority of these strategies is some form of collusion between agents (pacts, corruption, cartels, etc). Bitcoin lines up incentives between agents in the long term simply by using deflation, avoiding the need for expensive transactions and “political” solutions. This guarantees, in the long term, the value of the network since there’s not risk that agents find a consensus.

#3. Simplified Paymen Verification 
It is possible to verify payments without running a full network node. A user only needs to keep a copy of the block headers of the longest proof-of-work chain, which we can get by querying network nodes until we are convinced we have the longest chain, and obtain the Merkle branch linking the transaction to the block it's timestamped in.  