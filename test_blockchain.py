import os
import sys
import unittest

# Ensure working directory is added to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.crypto_utils import (
    generate_keypair,
    hash_data,
    sign_data,
    verify_signature,
    generate_voter_nullifier,
    build_merkle_root
)
from backend.pos_consensus import PoSConsensus
from backend.voting_contract import VotingSmartContract
from backend.blockchain import Blockchain
from backend.p2p_network import P2PNetworkSimulator

class TestPoSBlockchainVotingSystem(unittest.TestCase):

    def test_phase1_cryptography(self):
        """Test Phase 1: Cryptographic keypairs, hashing, nullifiers, and Merkle tree root."""
        pub_key, priv_key = generate_keypair()
        self.assertEqual(len(pub_key), 64)
        self.assertEqual(len(priv_key), 64)

        payload = {"vote": "CAN-01", "election": "ELEC-2026"}
        sig = sign_data(priv_key, payload)
        self.assertTrue(verify_signature(pub_key, payload, sig, priv_key))

        # Test voter nullifier uniqueness & consistency
        null1 = generate_voter_nullifier("VOTER-100", "ELEC-2026", "secret123")
        null2 = generate_voter_nullifier("VOTER-100", "ELEC-2026", "secret123")
        null3 = generate_voter_nullifier("VOTER-101", "ELEC-2026", "secret123")
        self.assertEqual(null1, null2)
        self.assertNotEqual(null1, null3)

        # Test Merkle Tree computation
        txs = [{"id": 1}, {"id": 2}, {"id": 3}]
        merkle_root = build_merkle_root(txs)
        self.assertEqual(len(merkle_root), 64)

    def test_phase2_pos_consensus(self):
        """Test Phase 2: PoS Validator Staking, Weighted Leader Selection, Slashing."""
        pos = PoSConsensus(minimum_stake=10.0)
        initial_stake = pos.get_total_stake()
        self.assertGreater(initial_stake, 0)

        # Register new validator
        v = pos.register_validator("val_test_node", "pub_key_test", stake=100.0, name="Test Node")
        self.assertEqual(v.stake, 100.0)

        # Select leader
        leader = pos.select_slot_leader("prev_hash_123456789")
        self.assertIsNotNone(leader)
        self.assertIn(leader.address, pos.validators)

        # Slash validator
        report = pos.slash_validator("val_test_node", "Double signing block")
        self.assertEqual(report["validator"], "val_test_node")
        self.assertEqual(report["remaining_stake"], 50.0)

    def test_phase3_smart_contract_and_anti_double_voting(self):
        """Test Phase 3: Smart contract rules, vote packaging, and double-voting prevention."""
        contract = VotingSmartContract()
        candidates = contract.get_candidates()
        self.assertGreater(len(candidates), 0)

        pub_key, priv_key = generate_keypair()
        
        # Cast 1st Vote (Valid)
        tx1 = contract.create_vote_transaction("VOTER-001", "pass123", pub_key, priv_key, "CAN-01")
        self.assertEqual(tx1["candidate_id"], "CAN-01")

        # Attempt to cast 2nd Vote with SAME voter credentials (Should fail)
        with self.assertRaises(ValueError) as ctx:
            contract.create_vote_transaction("VOTER-001", "pass123", pub_key, priv_key, "CAN-02")
        self.assertIn("ALREADY voted", str(ctx.exception))

    def test_phase4_5_blockchain_p2p_and_tally(self):
        """Test Phase 4 & 5: Blockchain block forging, ledger validation, P2P sync, receipt auditing."""
        chain = Blockchain()
        p2p = P2PNetworkSimulator(chain)

        pub_key, priv_key = generate_keypair()
        tx = chain.voting_contract.create_vote_transaction("VOTER-TEST", "pass456", pub_key, priv_key, "CAN-01")
        
        # Add to mempool
        success, msg = chain.add_transaction(tx)
        self.assertTrue(success)
        self.assertEqual(len(chain.mempool), 1)

        # Broadcast via P2P
        b_info = p2p.broadcast_transaction(tx)
        self.assertEqual(b_info["status"], "GOSSIP_BROADCAST_COMPLETE")

        # Forge block
        block, msg = chain.forge_block()
        self.assertIsNotNone(block)
        self.assertEqual(block.index, 1)
        self.assertEqual(len(chain.mempool), 0)

        # Verify Blockchain Integrity
        valid, msg = chain.is_chain_valid()
        self.assertTrue(valid)

        # Verify Immutable Tally
        tally = chain.get_vote_tally()
        self.assertEqual(tally["total_votes_cast"], 1)

        # Verify Receipt
        receipt_hash = tx["voter_receipt"]
        verification = chain.verify_voter_receipt(receipt_hash)
        self.assertTrue(verification["verified"])
        self.assertEqual(verification["block_index"], 1)

if __name__ == "__main__":
    unittest.main()
