#include "Blockchain.h"

Blockchain::Blockchain() {
	_vChain.emplace_back(TBlock(0, "geneis block"));
	_nDifficulty = 5;
}

void Blockchain::AddBlock(TBlock bNew) {
	bNew.sPrevHash = _GetLastBlock().sHash;
	bNew.MineBlock(_nDifficulty);
	_vChain.push_back(bNew);
}

TBlock Blockchain::_GetLastBlock() const {
	return _vChain.back();
}