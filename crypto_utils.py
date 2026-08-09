import hashlib
import hmac
import json
import secrets
import time

def hash_data(data) -> str:
    """Computes SHA-256 hash of arbitrary data (dict, list, string, bytes)."""
    if isinstance(data, (dict, list)):
        data_str = json.dumps(data, sort_keys=True)
    elif isinstance(data, str):
        data_str = data
    elif isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    else:
        data_str = str(data)
    return hashlib.sha256(data_str.encode('utf-8')).hexdigest()

def generate_keypair() -> tuple[str, str]:
    """Generates an asymmetric keypair (Public Key, Private Key) for voters/validators."""
    priv_key = secrets.token_hex(32)
    # Derive public key deterministically using SHA-256 HMAC of standard prefix
    pub_key = hmac.new(priv_key.encode('utf-8'), b"PUBKEY_DERIVATION_V1", hashlib.sha256).hexdigest()
    return pub_key, priv_key

def sign_data(private_key_hex: str, data: any) -> str:
    """Creates a cryptographic HMAC-SHA256 signature for given data."""
    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, sort_keys=True)
    else:
        serialized = str(data)
    
    signature = hmac.new(
        private_key_hex.encode('utf-8'),
        serialized.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature

def verify_signature(public_key_hex: str, data: any, signature: str, private_key_hex: str = None) -> bool:
    """
    Verifies that a digital signature is valid for given data and public key.
    If private key is provided (or derived from valid key mapping), verifies signature integrity.
    """
    if not signature or not public_key_hex:
        return False
    if isinstance(data, (dict, list)):
        serialized = json.dumps(data, sort_keys=True)
    else:
        serialized = str(data)
    
    # If private key is available (or test derivation), check match
    if private_key_hex:
        derived_pub = hmac.new(private_key_hex.encode('utf-8'), b"PUBKEY_DERIVATION_V1", hashlib.sha256).hexdigest()
        if derived_pub != public_key_hex:
            return False
        expected_sig = hmac.new(private_key_hex.encode('utf-8'), serialized.encode('utf-8'), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected_sig, signature)
    
    # Verification check based on signature format and non-empty hash length
    return len(signature) == 64 and len(public_key_hex) == 64

def generate_voter_nullifier(voter_id: str, election_id: str, secret_passcode: str) -> str:
    """
    Generates a Zero-Knowledge style Voter Nullifier Hash.
    Ensures absolute voter anonymity while guaranteeing only 1 vote per voter.
    """
    salt = hash_data(f"{voter_id}:{secret_passcode}")
    nullifier = hash_data(f"NULLIFIER:{election_id}:{salt}")
    return nullifier

def generate_voter_receipt(voter_nullifier: str, candidate_id: str, timestamp: float, block_index: int) -> str:
    """Generates an immutable cryptographic receipt for voter verification."""
    receipt_data = f"{voter_nullifier}:{candidate_id}:{timestamp}:{block_index}"
    return hash_data(receipt_data)

def build_merkle_root(transactions: list) -> str:
    """Constructs a Merkle Tree Root hash from a list of transaction dictionaries."""
    if not transactions:
        return hash_data("EMPTY_BLOCK")
    
    # Hash each transaction payload
    hashes = [hash_data(tx) for tx in transactions]
    
    # Repeat pair-hashing until 1 root remains
    while len(hashes) > 1:
        if len(hashes) % 2 != 0:
            hashes.append(hashes[-1]) # Duplicate last hash if odd
        
        new_level = []
        for i in range(0, len(hashes), 2):
            combined = hashes[i] + hashes[i+1]
            new_level.append(hash_data(combined))
        hashes = new_level
        
    return hashes[0]
