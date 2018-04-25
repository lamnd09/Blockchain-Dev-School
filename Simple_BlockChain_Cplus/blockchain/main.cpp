#include "Blockchain.h"
int main() {
	Blockchain TbChain = Blockchain();

	cout << "Node are mining block 1 ... " << endl;
	TbChain.AddBlock(TBlock(1, "Block 1"));

	cout << "Node are mining block 2 ... " << endl;
	TbChain.AddBlock(TbChain(2, "Block 2"));

	return 0;
}