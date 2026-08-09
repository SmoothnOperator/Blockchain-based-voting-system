import os
import sys
import time
import webbrowser
from backend.server import app

def main():
    print("=" * 80)
    print("  DecentriVote: PoS Blockchain Electronic Voting System Running ")
    print("=" * 80)
    print(" Phase 1: Cryptographic Identity & Key Management initialized.")
    print(" Phase 2: Proof-of-Stake Consensus Engine initialized.")
    print(" Phase 3: Smart Contract & Ballot Rules active.")
    print(" Phase 4: P2P Multi-Node Network active.")
    print(" Phase 5: Merkle Tree & Immutable Receipt Tally ready.")
    print(" Phase 6: Web Visualizer UI running at http://127.0.0.1:5000")
    print("=" * 80)

    # Open browser automatically after 1.2 seconds
    webbrowser.open("http://127.0.0.1:5000")
    
    # Start Flask Web App
    app.run(host="127.0.0.1", port=5000, debug=False)

if __name__ == "__main__":
    main()
