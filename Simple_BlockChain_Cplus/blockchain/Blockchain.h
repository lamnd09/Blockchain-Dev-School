#include <cstdint>
#include <vector>
#include "TBlock.h"

using namespace std;

class Blockchain {
public: 
	Blockchain();
	void AddBlock(TBlock bNew);

private: 
	uint32_t _nDifficulty;
	vector<TBlock> _vChain;

	TBlock _GetLastBlock() const;
};
