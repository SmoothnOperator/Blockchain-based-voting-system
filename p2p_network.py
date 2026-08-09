import copy
import time
from typing import Dict, List
from backend.blockchain import Blockchain

class P2PNode:
    def __init__(self, node_id: str, name: str, role: str):
        self.node_id = node_id
        self.name = name
        self.role = role
        self.status = "ONLINE"
        self.peers: List[str] = []
        self.mempool_sync_count = 0
        self.last_sync_time = time.time()

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "peers": self.peers,
            "mempool_sync_count": self.mempool_sync_count,
            "last_sync_time": self.last_sync_time
        }

class P2PNetworkSimulator:
    """Simulates a decentralized Peer-to-Peer Multi-Node Blockchain Network."""

    def __init__(self, main_blockchain: Blockchain):
        self.main_blockchain = main_blockchain
        self.nodes: Dict[str, P2PNode] = {
            "node_01": P2PNode("node_01", "Node Alpha - Election Authority", "Validator & Aggregator"),
            "node_02": P2PNode("node_02", "Node Beta - National University", "Validator & Auditor"),
            "node_03": P2PNode("node_03", "Node Gamma - Civil Society Watchdog", "Public Auditor")
        }

        # Interconnect peer nodes (Full mesh topology)
        self.nodes["node_01"].peers = ["node_02", "node_03"]
        self.nodes["node_02"].peers = ["node_01", "node_03"]
        self.nodes["node_03"].peers = ["node_01", "node_02"]

    def broadcast_transaction(self, tx: dict) -> dict:
        """Simulates broadcasting a vote transaction across all connected P2P nodes."""
        propagated_nodes = []
        for nid, node in self.nodes.items():
            if node.status == "ONLINE":
                node.mempool_sync_count += 1
                node.last_sync_time = time.time()
                propagated_nodes.append(node.name)
        
        return {
            "tx_id": tx.get("tx_id"),
            "propagated_nodes_count": len(propagated_nodes),
            "nodes": propagated_nodes,
            "status": "GOSSIP_BROADCAST_COMPLETE"
        }

    def sync_nodes_ledger(self) -> dict:
        """Simulates cross-node ledger validation and height synchronization."""
        block_height = len(self.main_blockchain.chain)
        valid, msg = self.main_blockchain.is_chain_valid()
        
        sync_report = []
        for nid, node in self.nodes.items():
            sync_report.append({
                "node_id": node.node_id,
                "name": node.name,
                "height": block_height,
                "in_sync": valid,
                "status": "SYNCHRONIZED" if valid else "DESYNC_DETECTED"
            })

        return {
            "global_height": block_height,
            "consensus_reached": valid,
            "consensus_message": msg,
            "nodes_state": sync_report
        }

    def get_network_topology(self) -> dict:
        return {
            "active_nodes": len(self.nodes),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "mempool_size": len(self.main_blockchain.mempool),
            "total_blocks": len(self.main_blockchain.chain)
        }
