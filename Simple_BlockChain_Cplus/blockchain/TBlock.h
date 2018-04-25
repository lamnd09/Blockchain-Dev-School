#include <cstdint>
#include <iostream>
#include <sstream>

using namespace std;

class TBlock {
public: 
	string sHash;
	string sPrevHash;

	TBlock(uint32_t nIndexIn, const string &sDataIn);
	void MineBlock(uint32_t nDifficulty);
	
private: 
	uint32_t _nIndex;
	uint32_t _nNonce;
	string _sData;
	time_t _tTime;
	string _CalculateHash() const;
};