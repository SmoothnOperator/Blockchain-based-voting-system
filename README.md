# DecentriVote: Secure, Transparent, and Decentralized Blockchain Electronic Voting System using Proof-of-Stake (PoS)

A complete, production-ready, working model of a Proof-of-Stake (PoS) Blockchain-Based Electronic Voting System written in Python with an interactive Web Visualizer and REST API.

---

## 🌟 Key Features & Architectural Highlights

- **Proof-of-Stake (PoS) Consensus Engine**: Stake-weighted random leader lottery selection (Ouroboros style), block reward incentives, and validator stake-slashing penalties.
- **Zero-Knowledge Voter Anonymity**: Cryptographic asymmetric keypairs (ECDSA/HMAC SHA-256) and deterministic Voter Nullifiers decouple public voter identity from cast ballot content.
- **Merkle Tree Proofs & Receipt Verification**: Every block computes Merkle Tree root hashes, enabling voters to independently verify their vote inclusion on the immutable blockchain using a unique cryptographic receipt.
- **Smart Contract Anti-Double Voting**: Enforces strict single-vote rules per election instance. Attempts to vote twice with the same voter nullifier are automatically rejected.
- **P2P Node Network Simulator**: Multi-node topology (Election Commission Node, University Auditor Node, Civil Society Watchdog Node) with gossip transaction broadcasting and state synchronization.
- **Interactive Cyber-Security Web Visualizer**: Live Block Explorer, Validator Staking Hub, Voter Booth, Real-time Tally Chart (Chart.js), and Receipt Auditor.

---

## 🏗️ Step-by-Step Architecture Process (6 Phases)

### Phase 1: Cryptographic Identity & Key Management
- **Keypair Generation**: Each voter generates a unique Public/Private Keypair upon registering.
- **Voter Nullifier Hash**: A deterministic zero-knowledge token `SHA256(Voter_ID : Election_ID : Salt)` is derived. This token allows the system to verify that the voter is eligible and hasn't voted yet without storing or revealing the voter's real identity in the ballot.

### Phase 2: Proof-of-Stake (PoS) Consensus Engine
- **Validator Staking Pool**: Nodes deposit token stakes to join the active block proposer set.
- **Slot Leader Lottery**: For each block proposal round, a slot leader validator is chosen randomly weighted by their stake percentage:
  $$\text{Probability}(V_i) = \frac{\text{Stake}(V_i)}{\sum \text{Stake}}$$
- **Block Forging & Slashing Protocol**: The selected validator collects transactions, builds the Merkle tree root, signs the block header, and receives a block reward. Malicious double-signing triggers a 50% stake slashing penalty.

### Phase 3: Smart Contract & Ballot Execution Logic
- **Candidate Registry**: Initializes election candidate profiles.
- **Transaction Packaging**: Ballots are formatted as cryptographic transactions `(tx_id, candidate_id, voter_nullifier, signature, receipt)`.
- **Double-Voting Rejection**: The smart contract checks whether `voter_nullifier` has already been recorded in `cast_nullifiers`. Re-submissions are rejected instantly.

### Phase 4: Decentralized P2P Network Simulation
- **Gossip Transaction Propagation**: Valid vote transactions submitted at any node are broadcast to peer nodes (Node Alpha, Node Beta, Node Gamma) and queued in the global Mempool.
- **Ledger State Synchronization**: Ensures all nodes maintain identical block heights and cryptographic state.

### Phase 5: Transparent Auditability & Real-Time Tally Engine
- **Immutable Block Ledger**: Blocks link sequentially via `previous_hash` chains. Any attempt to modify a past vote breaks the hash link and invalidates the Merkle Tree root.
- **Zero-Leakage Tallying**: The tally engine aggregates votes directly from verified block transactions.
- **Receipt Proof Verifier**: Enables voters to input their `voter_receipt` hash to locate the exact Block Index and Block Hash holding their vote.

### Phase 6: Interactive Web Interface & Visualizer
- **Web App Server**: Lightweight Flask REST API backend (`backend/server.py`).
- **Interactive UI**: Responsive Glassmorphism dark mode interface (`frontend/`) featuring 6 dedicated tabs matching the system lifecycle.

---

## 🚀 How to Run the Working Model

### Prerequisites
- Python 3.8+ (Tested on Python 3.14)
- Flask (`pip install Flask`)

### Quick Start (One-Click Launcher)

1. Open your terminal in the project directory:
   ```bash
   cd "d:/2nd Year/SEM-(3)/OPERATING SYSTEM/working model"
   ```

2. Run the launcher script:
   ```bash
   python run_demo.py
   ```

3. The system will boot the backend server and automatically open the interactive Web Visualizer at **http://127.0.0.1:5000** in your web browser.

---

## 🧪 Running Automated Unit Tests

Run the full 6-Phase test suite to cryptographically verify key generation, PoS selection, anti-double voting, and receipt verification:

```bash
python tests/test_blockchain.py
```

Expected Output:
```text
....
----------------------------------------------------------------------
Ran 4 tests in 0.001s

OK
```

---

## 📁 Codebase Directory Structure

```text
working model/
├── backend/
│   ├── crypto_utils.py       # Phase 1: Cryptographic keypairs, hashing, Merkle trees
│   ├── pos_consensus.py      # Phase 2: PoS Validator Staking, Leader selection, Slashing
│   ├── voting_contract.py    # Phase 3: Candidate registry, Ballot validation, Anti-double-voting
│   ├── blockchain.py         # Phase 2 & 5: Core Block & Blockchain Ledger state
│   ├── p2p_network.py        # Phase 4: Multi-node P2P gossip network simulator
│   └── server.py             # Phase 6: Flask REST API Server
├── frontend/
│   ├── index.html            # 6-Tab Interactive Dashboard UI
│   ├── style.css             # Cyber Security Glassmorphism Dark Theme
│   └── app.js                # Reactive JS API integrations & Chart.js rendering
├── tests/
│   └── test_blockchain.py    # Automated test suite for all 6 phases
├── run_demo.py               # One-click system launcher script
└── README.md                 # Complete Architecture & Step-by-Step Guide
```
