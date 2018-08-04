//Voting system by solidity 
//The idea is to create one contract per ballot

pragma solidity ^0.4.22;

/// @title Voting with delegation 

contract Ballot {
    // single voter 
    struct Voter {
        uint weight;
        bool voted;
        address delegate; 
        uint vote;              //index of voted proposal
    }
    
    //This is a type for a single proposal 
    
    struct Proposal {
        bytes32 name; 
        uint voteCount; 
    }
    
    address public chairperson;
    mapping (address => uint) public voters;
    
    Proposal[] public proposals;
    
    /// Create a new ballot to choose one of 'proposalNames'
    constructor(bytes32[] proposalNames) public {
        chairperson = msg.sender;
        voters[chairperson].weight = 1;
        
        //For each of provided proposal names, creates a new proposal object and add it to the end of the array
        
        for(uint i=0; i<proposalNames.length;i++){
            proposals.push(Proposal({
                name:proposalNames[i], voteCount:0
            }));
        }
    }
    
    //Give voter the right to vote on this ballot, only be called by 'chairperson'
    
    function giveRighttoVote(address voter) public {
        require(
            msg.sender == chairperson, 'only chariperson can give right to vote');
        require(
            !voters[voter].weight == 0, 'the voter alreay vote');
        
        require(voters[voter].weight ==0);
        voters[voter].weight =1;
    }
    
    
    ///Delegate your vote to the voter 'to'
    
    function delegate(address to) public {
        //assign reference
        Voter storage sender = voters[msg.sender];
        require(!sender.voted, "You already voted.");
        
        //Forward the delegation as long as 'to' also delagated
        
        while(voters[to].delegate !=address(0)){
            to = voters[to].delegate;
            require(to !=msg.sender, "Found loop in delegation");
        }
        
        sender.voted = true;
        sender.delegate = to;
        Voter storage delegate_ = voters[to];
        
        if(delegate_.voted){
            proposals[delegate_.vote].voteCount += sender.weight;
        } else {
            delegate_.weight +=sender.weight;
        }
    }
    
    /// Give your vote including votes delegated to you to proposal proposals[proposal].name
    
    function vote(uint proposal) public {
        Voter storage sender = voters[msg.sender];
        require(!sender.voted, "Already voted.");
        sender.voted = true;
        sender.vote = proposal;
        
        proposals[proposal].voteCount += sender.weight;
    }
    
    ///@dev computes the winning proposal taking all previous votes into account
    function winningProposal() public view returns (uint winnningProposal_){
        uint winningVoteCount = 0;
        for(uint p=0; p<proposals.length; p++){
            if(proposals[p].voteCount > winningVoteCount){
                winningVoteCount = proposals[p].voteCount;
                winnningProposal_ = p;
            }
        }
    }
    function winnerName() public view returns (bytes32 winnerName_){
        winnerName_ = proposals[winningProposal()].name;
    }
    
}
		}
    
    
    
}