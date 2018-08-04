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
    }
    
    
    
}