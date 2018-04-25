#include "TBlock.h"
#include "sha256.h"

TBlock::TBlock(uint32_t nIndexIn, const string &sDataIn) : _nIndex(nIndexIn), _sData(sDataIn) {
	_nNonce = 0;
	_tTime = time(nullptr);
	sHash = _CalculateHash();
}

void TBlock::MineBlock(uint32_t nDifficulty) {
	char cstr[nDifficulty + 1];
	for (uint32_t i = 0; i < nDifficulty; i++) {
		cstr[i] = '0';
	}
	cstr[nDifficulty] = '\0';

	string str(cstr);

	while (sHash.substr(0, nDifficulty) != str) {
		_nNonce++;
		sHash = _CalculateHash();
	}

	cout << "Block mined: " << sHash << endl;
}

inline string TBlock::_CalculateHash() const {
	stringstream ss;
	ss << _nIndex << _tTime << _sData << _nNonce << sPrevHash;
	return sha256(ss.str());
}
