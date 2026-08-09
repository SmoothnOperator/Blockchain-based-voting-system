import time
from typing import List, Dict, Optional
from backend.crypto_utils import hash_data, build_merkle_root, sign_data, verify_signature
from backend.pos_consensus import PoSConsensus, Validator
from backend.voting_contract import VotingSmartContract

class Block:
    def __init__(
        self,
        index: int,
        timestamp: float,
        transactions: list,
        previous_hash: str,
        validator_address: str,
        validator_signature: str = "",
        merkle_root: str = "",
        block_hash: str = ""
    ):
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.previous_hash = previous_hash
        self.validator_address = validator_address
        self.merkle_root = merkle_root if merkle_root else build_merkle_root(transactions)
        self.validator_signature = validator_signature
        self.hash = block_hash if block_hash else self.calculate_hash()

    def calculate_hash(self) -> str:
        header = {
            "index": self.index,
            "timestamp": self.timestamp,
            "merkle_root": self.merkle_root,
            "previous_hash": self.previous_hash,
            "validator_address": self.validator_address
        }
        return hash_data(header)

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions_count": len(self.transactions),
            "transactions": self.transactions,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "validator_address": self.validator_address,
            "validator_signature": self.validator_signature,
            "hash": self.hash
        }

class Blockchain:
    """Core Proof-of-Stake Blockchain Engine maintaining Ledger State & Merkle Trees."""

    def __init__(self):
        self.chain: List[Block] = []
        self.mempool: List[dict] = []
        self.pos_engine = PoSConsensus()
        self.voting_contract = VotingSmartContract()
        
        # Build Genesis Block
        self._create_genesis_block()

    def _create_genesis_block(self):
        genesis_tx = [{
            "type": "GENESIS",
            "message": "Genesis Block - Proof-of-Stake Electronic Voting System Initialized",
            "timestamp": time.time()
        }]
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            transactions=genesis_tx,
            previous_hash="0" * 64,
            validator_address="val_node_01_alpha",
            validator_signature="GENESIS_SYSTEM_SIG"
        )
        self.chain.append(genesis_block)

    def get_latest_block(self) -> Block:
        return self.chain[-1]

    def add_transaction(self, tx: dict) -> tuple[bool, str]:
        """Validates and adds a transaction to the mempool."""
        valid, msg = self.voting_contract.verify_vote_transaction(tx)
        if not valid:
            return False, msg

        # Prevent duplicate transactions in mempool
        for pending in self.mempool:
            if pending.get("tx_id") == tx.get("tx_id") or pending.get("voter_nullifier") == tx.get("voter_nullifier"):
                return False, "Duplicate transaction already in mempool."

        self.mempool.append(tx)
        return True, f"Transaction '{tx['tx_id'][:12]}...' added to mempool successfully."

    def forge_block(self, forced_validator_address: str = None) -> tuple[Optional[Block], str]:
        """
        Executes a Proof-of-Stake Block Forging Round:
        1. Selects Slot Leader via PoS lottery (or specified validator).
        2. Pulls transactions from mempool.
        3. Builds Merkle Tree root hash.
        4. Signs and creates Block.
        5. Rewards validator and appends block to blockchain.
        """
        if not self.mempool:
            return None, "Cannot forge block: Mempool is empty (no pending vote transactions)."

        latest = self.get_latest_block()
        
        # Slot Leader Selection via PoS weighted random lottery
        if forced_validator_address and forced_validator_address in self.pos_engine.validators:
            slot_leader = self.pos_engine.validators[forced_validator_address]
        else:
            slot_leader = self.pos_engine.select_slot_leader(latest.hash)

        if not slot_leader or slot_leader.slashed:
            return None, "PoS Error: No eligible non-slashed validator available."

        # Package pending transactions
        txs_to_include = list(self.mempool)
        self.mempool = [] # Clear mempool

        merkle_root = build_merkle_root(txs_to_include)
        timestamp = time.time()
        
        # Block Header Sign
        header_data = f"{latest.index + 1}:{timestamp}:{merkle_root}:{latest.hash}:{slot_leader.address}"
        signature = sign_data(slot_leader.public_key, header_data)

        new_block = Block(
            index=latest.index + 1,
            timestamp=timestamp,
            transactions=txs_to_include,
            previous_hash=latest.hash,
            validator_address=slot_leader.address,
            validator_signature=signature,
            merkle_root=merkle_root
        )

        # Append to Ledger & Reward Validator
        self.chain.append(new_block)
        self.pos_engine.reward_validator(slot_leader.address)

        return new_block, f"Block #{new_block.index} forged successfully by Validator '{slot_leader.name}' ({slot_leader.address})!"

    def is_chain_valid(self) -> tuple[bool, str]:
        """Cryptographically verifies chain integrity, hash links, and Merkle tree roots."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # Check hash link integrity
            if current.previous_hash != previous.hash:
                return False, f"Broken Chain Link at Block #{i}: previous_hash mismatch!"

            # Re-calculate block hash
            if current.hash != current.calculate_hash():
                return False, f"Tampered Block Content at Block #{i}: hash mismatch!"

            # Re-calculate Merkle tree root
            if current.merkle_root != build_merkle_root(current.transactions):
                return False, f"Tampered Transactions at Block #{i}: Merkle root mismatch!"

        return True, "Blockchain ledger is cryptographically 100% valid and verified."

    def get_vote_tally(self) -> dict:
        """Calculates election tally strictly from verified blocks in the immutable blockchain."""
        tally = {c["candidate_id"]: {"candidate": c, "vote_count": 0} for c in self.voting_contract.get_candidates()}
        total_votes = 0

        for block in self.chain:
            for tx in block.transactions:
                if tx.get("type") == "VOTE_CAST":
                    cid = tx.get("candidate_id")
                    if cid in tally:
                        tally[cid]["vote_count"] += 1
                        total_votes += 1

        results = []
        for cid, data in tally.items():
            pct = round((data["vote_count"] / total_votes * 100.0), 2) if total_votes > 0 else 0.0
            results.append({
                "candidate_id": cid,
                "name": data["candidate"]["name"],
                "party": data["candidate"]["party"],
                "symbol": data["candidate"]["symbol"],
                "votes": data["vote_count"],
                "percentage": pct
            })

        return {
            "election_id": self.voting_contract.election_id,
            "title": self.voting_contract.title,
            "total_votes_cast": total_votes,
            "total_blocks": len(self.chain),
            "results": results
        }

    def verify_voter_receipt(self, receipt_hash: str) -> dict:
        """Searches the immutable blockchain for a voter's cryptographic receipt hash."""
        receipt_hash = receipt_hash.strip()
        for block in self.chain:
            for tx in block.transactions:
                if tx.get("voter_receipt") == receipt_hash:
                    return {
                        "verified": True,
                        "status": "CONFIRMED_ON_BLOCKCHAIN",
                        "receipt_hash": receipt_hash,
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "timestamp": tx.get("timestamp"),
                        "validator_address": block.validator_address,
                        "candidate_id": tx.get("candidate_id")
                    }
        return {
            "verified": False,
            "status": "NOT_FOUND",
            "message": "Receipt hash not found on the blockchain ledger."
        }
