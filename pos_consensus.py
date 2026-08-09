import random
import time
from typing import List, Dict, Optional
from backend.crypto_utils import hash_data, sign_data, verify_signature

class Validator:
    def __init__(self, address: str, public_key: str, stake: float = 100.0, name: str = "Validator"):
        self.address = address
        self.public_key = public_key
        self.stake = float(stake)
        self.name = name
        self.blocks_forged = 0
        self.slashed = False
        self.reputation = 100.0
        self.created_at = time.time()

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "public_key": self.public_key,
            "stake": round(self.stake, 2),
            "name": self.name,
            "blocks_forged": self.blocks_forged,
            "slashed": self.slashed,
            "reputation": round(self.reputation, 1)
        }

class PoSConsensus:
    """Proof-of-Stake Consensus Engine with Weighted Leader Selection & Slashing Protocol."""
    
    def __init__(self, minimum_stake: float = 10.0):
        self.validators: Dict[str, Validator] = {}
        self.minimum_stake = minimum_stake
        self.block_reward = 5.0 # Stake reward for forging valid block
        self.slashing_penalty = 50.0 # Percentage stake loss on malicious block creation

        # Register default Genesis / System Boot Validators
        self.register_validator(
            address="val_node_01_alpha",
            public_key="0000000000000000000000000000000000000000000000000000000000000001",
            stake=500.0,
            name="Primary Node Alpha (Election Commission)"
        )
        self.register_validator(
            address="val_node_02_beta",
            public_key="0000000000000000000000000000000000000000000000000000000000000002",
            stake=300.0,
            name="Auditor Node Beta (University Node)"
        )
        self.register_validator(
            address="val_node_03_gamma",
            public_key="0000000000000000000000000000000000000000000000000000000000000003",
            stake=200.0,
            name="Independent Watchdog Node Gamma"
        )

    def register_validator(self, address: str, public_key: str, stake: float, name: str = "Validator Node") -> Validator:
        """Registers a new validator node or updates stake."""
        if stake < self.minimum_stake:
            raise ValueError(f"Minimum stake required is {self.minimum_stake} tokens.")
        
        if address in self.validators:
            self.validators[address].stake += stake
        else:
            self.validators[address] = Validator(address, public_key, stake, name)
        
        return self.validators[address]

    def get_total_stake(self) -> float:
        """Returns the sum of all active non-slashed validator stakes."""
        return sum(v.stake for v in self.validators.values() if not v.slashed and v.stake > 0)

    def select_slot_leader(self, prev_block_hash: str) -> Optional[Validator]:
        """
        Stake-weighted deterministic random slot leader selection algorithm.
        Probability of selection is directly proportional to (Validator Stake / Total Stake).
        Uses previous block hash as seed for cryptographic pseudo-random selection.
        """
        active_validators = [v for v in self.validators.values() if not v.slashed and v.stake >= self.minimum_stake]
        if not active_validators:
            return None
        
        total_stake = sum(v.stake for v in active_validators)
        if total_stake == 0:
            return None

        # Derive seed integer from previous block hash
        seed_int = int(hash_data(prev_block_hash), 16)
        rng = random.Random(seed_int)
        
        # Weighted selection logic
        pick = rng.uniform(0, total_stake)
        current = 0.0
        for validator in active_validators:
            current += validator.stake
            if current >= pick:
                return validator
                
        return active_validators[-1]

    def reward_validator(self, validator_address: str):
        """Grants block reward for successful block forging."""
        if validator_address in self.validators:
            v = self.validators[validator_address]
            v.stake += self.block_reward
            v.blocks_forged += 1
            v.reputation = min(100.0, v.reputation + 0.5)

    def slash_validator(self, validator_address: str, reason: str) -> dict:
        """Slashes malicious validator's stake if double-signing or proposing invalid transactions."""
        if validator_address in self.validators:
            v = self.validators[validator_address]
            slashed_amount = v.stake * (self.slashing_penalty / 100.0)
            v.stake -= slashed_amount
            v.reputation = max(0.0, v.reputation - 50.0)
            if v.stake < self.minimum_stake:
                v.slashed = True
            return {
                "validator": validator_address,
                "slashed_amount": slashed_amount,
                "remaining_stake": v.stake,
                "reason": reason
            }
        return {"error": "Validator not found"}

    def get_validators_info(self) -> List[dict]:
        total_stake = self.get_total_stake()
        info = []
        for v in self.validators.values():
            d = v.to_dict()
            d["stake_percentage"] = round((v.stake / total_stake * 100.0) if total_stake > 0 else 0, 2)
            info.append(d)
        return info
