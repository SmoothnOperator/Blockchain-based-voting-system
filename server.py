import os
from flask import Flask, jsonify, request, send_from_directory
from backend.blockchain import Blockchain
from backend.crypto_utils import generate_keypair, generate_voter_nullifier
from backend.p2p_network import P2PNetworkSimulator

# Initialize Flask app
app = Flask(__name__, static_folder="../frontend", static_url_path="")

# Initialize Core Blockchain & P2P Engine
blockchain = Blockchain()
p2p_network = P2PNetworkSimulator(blockchain)

# --- STATIC FILE ROUTES ---
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def serve_static(path):
    return send_from_directory(app.static_folder, path)

# --- API ENDPOINTS ---

@app.route("/api/status", methods=["GET"])
def get_status():
    valid, msg = blockchain.is_chain_valid()
    return jsonify({
        "chain_length": len(blockchain.chain),
        "latest_block_hash": blockchain.get_latest_block().hash,
        "mempool_count": len(blockchain.mempool),
        "total_stake": blockchain.pos_engine.get_total_stake(),
        "active_validators": len([v for v in blockchain.pos_engine.validators.values() if not v.slashed]),
        "is_chain_valid": valid,
        "chain_validation_message": msg
    })

@app.route("/api/register_voter", methods=["POST"])
def register_voter():
    data = request.json or {}
    voter_id = data.get("voter_id", "").strip()
    secret_passcode = data.get("secret_passcode", "").strip()

    if not voter_id or not secret_passcode:
        return jsonify({"success": False, "error": "Voter ID and Secret Passcode are required."}), 400

    pub_key, priv_key = generate_keypair()
    nullifier = generate_voter_nullifier(voter_id, blockchain.voting_contract.election_id, secret_passcode)
    already_voted = blockchain.voting_contract.is_nullifier_used(nullifier)

    return jsonify({
        "success": True,
        "voter_id": voter_id,
        "public_key": pub_key,
        "private_key": priv_key,
        "voter_nullifier": nullifier,
        "already_voted": already_voted
    })

@app.route("/api/candidates", methods=["GET"])
def get_candidates():
    return jsonify({
        "election_id": blockchain.voting_contract.election_id,
        "title": blockchain.voting_contract.title,
        "candidates": blockchain.voting_contract.get_candidates()
    })

@app.route("/api/cast_vote", methods=["POST"])
def cast_vote():
    data = request.json or {}
    voter_id = data.get("voter_id", "").strip()
    secret_passcode = data.get("secret_passcode", "").strip()
    voter_pubkey = data.get("voter_pubkey", "").strip()
    voter_privkey = data.get("voter_privkey", "").strip()
    candidate_id = data.get("candidate_id", "").strip()

    if not all([voter_id, secret_passcode, voter_pubkey, voter_privkey, candidate_id]):
        return jsonify({"success": False, "error": "Missing required voting credentials or candidate selection."}), 400

    try:
        # Create vote transaction via smart contract
        tx = blockchain.voting_contract.create_vote_transaction(
            voter_id=voter_id,
            voter_secret=secret_passcode,
            voter_pubkey=voter_pubkey,
            voter_privkey=voter_privkey,
            candidate_id=candidate_id
        )

        # Add to mempool
        success, msg = blockchain.add_transaction(tx)
        if not success:
            return jsonify({"success": False, "error": msg}), 400

        # Broadcast via P2P Gossip network
        broadcast_info = p2p_network.broadcast_transaction(tx)

        return jsonify({
            "success": True,
            "message": "Vote successfully cast and broadcast to P2P network mempool!",
            "transaction": tx,
            "receipt": tx.get("voter_receipt"),
            "broadcast": broadcast_info
        })

    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Voting system error: {str(e)}"}), 500

@app.route("/api/mempool", methods=["GET"])
def get_mempool():
    return jsonify({
        "mempool_count": len(blockchain.mempool),
        "transactions": blockchain.mempool
    })

@app.route("/api/forge_block", methods=["POST"])
def forge_block():
    data = request.json or {}
    forced_validator = data.get("validator_address", None)
    
    block, msg = blockchain.forge_block(forced_validator)
    if not block:
        return jsonify({"success": False, "error": msg}), 400

    return jsonify({
        "success": True,
        "message": msg,
        "block": block.to_dict()
    })

@app.route("/api/blocks", methods=["GET"])
def get_blocks():
    return jsonify({
        "total_blocks": len(blockchain.chain),
        "blocks": [b.to_dict() for b in blockchain.chain]
    })

@app.route("/api/stake", methods=["POST"])
def stake_tokens():
    data = request.json or {}
    address = data.get("address", "").strip()
    name = data.get("name", "Validator Node").strip()
    stake = float(data.get("stake", 50.0))
    pubkey = data.get("public_key", generate_keypair()[0])

    if not address or stake <= 0:
        return jsonify({"success": False, "error": "Invalid address or stake amount."}), 400

    try:
        val = blockchain.pos_engine.register_validator(address, pubkey, stake, name)
        return jsonify({
            "success": True,
            "message": f"Successfully staked {stake} tokens for '{name}'.",
            "validator": val.to_dict()
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route("/api/validators", methods=["GET"])
def get_validators():
    return jsonify({
        "minimum_stake": blockchain.pos_engine.minimum_stake,
        "total_stake": blockchain.pos_engine.get_total_stake(),
        "validators": blockchain.pos_engine.get_validators_info()
    })

@app.route("/api/tally", methods=["GET"])
def get_tally():
    return jsonify(blockchain.get_vote_tally())

@app.route("/api/verify_receipt", methods=["POST"])
def verify_receipt():
    data = request.json or {}
    receipt_hash = data.get("receipt_hash", "").strip()
    if not receipt_hash:
        return jsonify({"verified": False, "error": "Please provide a valid voter receipt hash."}), 400
    
    res = blockchain.verify_voter_receipt(receipt_hash)
    return jsonify(res)

@app.route("/api/nodes", methods=["GET"])
def get_nodes():
    sync_report = p2p_network.sync_nodes_ledger()
    topology = p2p_network.get_network_topology()
    return jsonify({
        "topology": topology,
        "sync_report": sync_report
    })

@app.route("/api/slash_validator", methods=["POST"])
def slash_validator():
    data = request.json or {}
    address = data.get("address", "").strip()
    reason = data.get("reason", "Malicious activity or invalid block signature.").strip()
    
    if not address:
        return jsonify({"success": False, "error": "Validator address required."}), 400

    res = blockchain.pos_engine.slash_validator(address, reason)
    return jsonify({"success": True, "slashing_report": res})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
