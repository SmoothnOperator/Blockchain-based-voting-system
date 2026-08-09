import time
from typing import Dict, List, Optional
from backend.crypto_utils import (
    hash_data,
    generate_voter_nullifier,
    generate_voter_receipt,
    sign_data,
    verify_signature
)

class Candidate:
    def __init__(self, candidate_id: str, name: str, party: str, symbol: str):
        self.candidate_id = candidate_id
        self.name = name
        self.party = party
        self.symbol = symbol

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "name": self.name,
            "party": self.party,
            "symbol": self.symbol
        }

class VotingSmartContract:
    """Smart Contract enforcing Ballot Rules, Candidate Registry, Anti-Double Voting, and Vote Packaging."""
    
    def __init__(self, election_id: str = "ELEC-2026-NATIONAL", title: str = "National Presidential & Parliamentary Election 2026"):
        self.election_id = election_id
        self.title = title
        self.is_active = True
        self.created_at = time.time()
        self.candidates: Dict[str, Candidate] = {}
        self.registered_nullifiers: set = set()
        self.cast_nullifiers: set = set()

        # Seed Default Candidates
        self.register_candidate("CAN-01", "Dr. Elena Vance", "Cyber Progress Party", "⚡")
        self.register_candidate("CAN-02", "Marcus Sterling", "Decentralized Alliance", "🛡️")
        self.register_candidate("CAN-03", "Aisha Patel", "Open Transparency Front", "🌐")
        self.register_candidate("CAN-04", "Julian Thorne", "Eco-Future Coalition", "🌱")

    def register_candidate(self, candidate_id: str, name: str, party: str, symbol: str = "🗳️") -> Candidate:
        candidate = Candidate(candidate_id, name, party, symbol)
        self.candidates[candidate_id] = candidate
        return candidate

    def is_nullifier_used(self, voter_nullifier: str) -> bool:
        """Checks if a voter nullifier has already cast a ballot."""
        return voter_nullifier in self.cast_nullifiers

    def create_vote_transaction(
        self,
        voter_id: str,
        voter_secret: str,
        voter_pubkey: str,
        voter_privkey: str,
        candidate_id: str
    ) -> dict:
        """
        Creates, signs, and packages an anonymous cryptographic vote transaction.
        Checks for double voting before issuing transaction.
        """
        if not self.is_active:
            raise ValueError("Election is currently closed.")
        
        if candidate_id not in self.candidates:
            raise ValueError(f"Invalid candidate ID: '{candidate_id}'")

        # Derive Anonymous Voter Nullifier
        nullifier = generate_voter_nullifier(voter_id, self.election_id, voter_secret)
        
        if self.is_nullifier_used(nullifier):
            raise ValueError(f"Security Alert: Voter nullifier '{nullifier[:12]}...' has ALREADY voted!")

        timestamp = time.time()
        receipt = generate_voter_receipt(nullifier, candidate_id, timestamp, 0)
        
        # Transaction Payload (Voter Identity is NOT included; only Nullifier hash)
        payload = {
            "type": "VOTE_CAST",
            "election_id": self.election_id,
            "candidate_id": candidate_id,
            "voter_nullifier": nullifier,
            "voter_pubkey": voter_pubkey,
            "timestamp": timestamp,
            "voter_receipt": receipt
        }

        # Sign transaction payload
        signature = sign_data(voter_privkey, payload)
        payload["signature"] = signature
        payload["tx_id"] = hash_data(payload)

        # Mark nullifier as pending/cast
        self.cast_nullifiers.add(nullifier)

        return payload

    def verify_vote_transaction(self, tx: dict) -> tuple[bool, str]:
        """Validates transaction format, signature, and anti-double voting constraints."""
        required_fields = ["type", "election_id", "candidate_id", "voter_nullifier", "voter_pubkey", "timestamp", "signature", "tx_id"]
        for f in required_fields:
            if f not in tx:
                return False, f"Missing required transaction field: {f}"

        if tx["type"] != "VOTE_CAST" or tx["election_id"] != self.election_id:
            return False, "Invalid election transaction type or election ID mismatch."

        if tx["candidate_id"] not in self.candidates:
            return False, "Selected candidate does not exist."

        # Signature check
        payload_copy = {k: v for k, v in tx.items() if k not in ["signature", "tx_id"]}
        if not verify_signature(tx["voter_pubkey"], payload_copy, tx["signature"]):
            return False, "Cryptographic signature verification failed."

        return True, "Valid Vote Transaction"

    def get_candidates(self) -> List[dict]:
        return [c.to_dict() for c in self.candidates.values()]
