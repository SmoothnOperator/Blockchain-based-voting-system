// DecentriVote - Frontend Application Logic

let currentVoterState = {
    voter_id: "",
    secret_passcode: "",
    public_key: "",
    private_key: "",
    voter_nullifier: "",
    selected_candidate: null
};

let tallyChartInstance = null;

// --- INITIALIZATION ---
document.addEventListener("DOMContentLoaded", () => {
    initNavigationTabs();
    loadCandidates();
    loadStatus();
    loadValidators();
    loadBlockchain();
    loadP2PNodes();
    loadTally();

    // Setup Form Listeners
    document.getElementById("voter-reg-form").addEventListener("submit", handleVoterRegistration);
    document.getElementById("staking-form").addEventListener("submit", handleStakingSubmit);

    // Auto-refresh stats every 8 seconds
    setInterval(loadStatus, 8000);
});

// --- NAVIGATION TABS ---
function initNavigationTabs() {
    const tabBtns = document.querySelectorAll(".tab-btn");
    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetId = btn.getAttribute("data-tab");
            switchTab(targetId);
        });
    });
}

function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));

    const activeBtn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    const activeTab = document.getElementById(tabId);
    
    if (activeBtn) activeBtn.classList.add("active");
    if (activeTab) activeTab.classList.add("active");

    // Refresh specific tab data on activation
    if (tabId === "tab-explorer") loadBlockchain();
    if (tabId === "tab-staking") loadValidators();
    if (tabId === "tab-p2p") loadP2PNodes();
    if (tabId === "tab-tally") loadTally();
}

// --- NOTIFICATION BANNER ---
function showToast(message, type = "info") {
    const banner = document.getElementById("toast-banner");
    banner.innerText = message;
    banner.className = `toast ${type}`;
    banner.classList.remove("hidden");
    setTimeout(() => {
        banner.classList.add("hidden");
    }, 4000);
}

// --- API CALL: SYSTEM STATUS ---
async function loadStatus() {
    try {
        const res = await fetch("/api/status");
        const data = await res.json();
        
        document.getElementById("nav-block-height").innerText = `#${data.chain_length - 1}`;
        document.getElementById("nav-total-stake").innerText = `${data.total_stake} 🪙`;
        document.getElementById("nav-mempool").innerText = `${data.mempool_count} Tx`;

        const statusText = document.getElementById("chain-status-text");
        const statusPill = document.getElementById("chain-status-pill");
        if (data.is_chain_valid) {
            statusText.innerText = "Ledger Verified 100%";
            statusPill.className = "stat-pill status-ok";
        } else {
            statusText.innerText = "CHAIN TAMPERED!";
            statusPill.className = "stat-pill status-danger";
        }
    } catch (e) {
        console.error("Status fetch error:", e);
    }
}

// --- PHASE 1: VOTER REGISTRATION ---
async function handleVoterRegistration(e) {
    e.preventDefault();
    const voterId = document.getElementById("voter-id-input").value.trim();
    const passcode = document.getElementById("voter-passcode-input").value.trim();

    try {
        const res = await fetch("/api/register_voter", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ voter_id: voterId, secret_passcode: passcode })
        });
        const data = await res.json();

        if (data.success) {
            currentVoterState.voter_id = voterId;
            currentVoterState.secret_passcode = passcode;
            currentVoterState.public_key = data.public_key;
            currentVoterState.private_key = data.private_key;
            currentVoterState.voter_nullifier = data.voter_nullifier;

            document.getElementById("display-pubkey").innerText = data.public_key;
            document.getElementById("display-privkey").innerText = `${data.private_key.substring(0, 16)}... [PROTECTED]`;
            document.getElementById("display-nullifier").innerText = data.voter_nullifier;
            document.getElementById("voter-credentials-box").classList.remove("hidden");

            if (data.already_voted) {
                showToast("Notice: This voter nullifier has ALREADY cast a vote!", "warning");
                document.getElementById("btn-submit-vote").disabled = true;
            } else {
                showToast("Cryptographic keys & Anonymous Nullifier Token generated!");
                checkVoteButtonState();
            }
        } else {
            showToast(`Registration failed: ${data.error}`, "danger");
        }
    } catch (e) {
        showToast("Error generating voter keys.", "danger");
    }
}

// --- PHASE 3: CANDIDATE LOADING & SELECTION ---
async function loadCandidates() {
    try {
        const res = await fetch("/api/candidates");
        const data = await res.json();
        
        const grid = document.getElementById("candidate-list-grid");
        grid.innerHTML = "";

        data.candidates.forEach(c => {
            const card = document.createElement("div");
            card.className = "candidate-card";
            card.setAttribute("data-id", c.candidate_id);
            card.innerHTML = `
                <div class="candidate-symbol">${c.symbol}</div>
                <div class="candidate-info">
                    <h4>${c.name}</h4>
                    <p>${c.party}</p>
                </div>
            `;
            card.addEventListener("click", () => selectCandidate(c.candidate_id, card));
            grid.appendChild(card);
        });
    } catch (e) {
        console.error("Candidates fetch error:", e);
    }
}

function selectCandidate(candidateId, cardElem) {
    document.querySelectorAll(".candidate-card").forEach(c => c.classList.remove("selected"));
    cardElem.classList.add("selected");
    currentVoterState.selected_candidate = candidateId;
    checkVoteButtonState();
}

function checkVoteButtonState() {
    const btn = document.getElementById("btn-submit-vote");
    if (currentVoterState.public_key && currentVoterState.selected_candidate) {
        btn.disabled = false;
    } else {
        btn.disabled = true;
    }
}

// --- PHASE 3: CAST BALLOT ---
async function submitVote() {
    if (!currentVoterState.public_key || !currentVoterState.selected_candidate) {
        showToast("Please register credentials and select a candidate first.", "warning");
        return;
    }

    try {
        const payload = {
            voter_id: currentVoterState.voter_id,
            secret_passcode: currentVoterState.secret_passcode,
            voter_pubkey: currentVoterState.public_key,
            voter_privkey: currentVoterState.private_key,
            candidate_id: currentVoterState.selected_candidate
        };

        const res = await fetch("/api/cast_vote", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        const data = await res.json();

        if (data.success) {
            showToast("🎉 Vote cast and broadcast to P2P network mempool!");
            document.getElementById("receipt-hash-display").innerText = data.receipt;
            document.getElementById("vote-receipt-box").classList.remove("hidden");
            document.getElementById("verify-receipt-input").value = data.receipt;
            document.getElementById("btn-submit-vote").disabled = true;
            loadStatus();
        } else {
            showToast(`Vote Rejected: ${data.error}`, "danger");
        }
    } catch (e) {
        showToast("Server error casting vote.", "danger");
    }
}

// --- PHASE 2: POS VALIDATORS & STAKING ---
async function loadValidators() {
    try {
        const res = await fetch("/api/validators");
        const data = await res.json();

        const list = document.getElementById("validators-list");
        const slashSelect = document.getElementById("slash-validator-select");
        list.innerHTML = "";
        slashSelect.innerHTML = "";

        data.validators.forEach(v => {
            const card = document.createElement("div");
            card.className = `validator-card ${v.slashed ? "slashed" : ""}`;
            card.innerHTML = `
                <div class="validator-info">
                    <h4>${v.name} ${v.slashed ? "<span class='badge danger'>SLASHED</span>" : ""}</h4>
                    <p>Address: <code>${v.address}</code></p>
                    <p>Blocks Forged: <strong>${v.blocks_forged}</strong> | Reputation: <strong>${v.reputation}</strong></p>
                </div>
                <div class="validator-stake">
                    <span class="stat-value">${v.stake} 🪙</span>
                    <span class="sub-text">${v.stake_percentage}% Lottery Prob</span>
                </div>
            `;
            list.appendChild(card);

            if (!v.slashed) {
                const opt = document.createElement("option");
                opt.value = v.address;
                opt.innerText = `${v.name} (${v.stake} tokens)`;
                slashSelect.appendChild(opt);
            }
        });
    } catch (e) {
        console.error("Validators error:", e);
    }
}

async function handleStakingSubmit(e) {
    e.preventDefault();
    const name = document.getElementById("stake-node-name").value;
    const address = document.getElementById("stake-address").value;
    const stake = document.getElementById("stake-amount").value;

    try {
        const res = await fetch("/api/stake", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name, address, stake: parseFloat(stake) })
        });
        const data = await res.json();

        if (data.success) {
            showToast(data.message);
            loadValidators();
            loadStatus();
        } else {
            showToast(`Staking failed: ${data.error}`, "danger");
        }
    } catch (e) {
        showToast("Error depositing stake.", "danger");
    }
}

// --- PHASE 2: FORGE BLOCK ---
async function triggerBlockForging() {
    try {
        const res = await fetch("/api/forge_block", { method: "POST", headers: { "Content-Type": "application/json" } });
        const data = await res.json();

        if (data.success) {
            showToast(`⚡ ${data.message}`);
            loadStatus();
            loadBlockchain();
            loadValidators();
            loadTally();
        } else {
            showToast(`Block Forging Error: ${data.error}`, "warning");
        }
    } catch (e) {
        showToast("Error triggering block forging.", "danger");
    }
}

async function slashSelectedValidator() {
    const address = document.getElementById("slash-validator-select").value;
    if (!address) return;

    try {
        const res = await fetch("/api/slash_validator", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ address, reason: "Security violation: Invalid block proposal" })
        });
        const data = await res.json();

        if (data.success) {
            showToast(`⚠️ Slashed 50% stake from validator '${address}'!`, "warning");
            loadValidators();
            loadStatus();
        }
    } catch (e) {
        showToast("Slashing failed.", "danger");
    }
}

// --- PHASE 2 & 5: BLOCKCHAIN EXPLORER ---
async function loadBlockchain() {
    try {
        const res = await fetch("/api/blocks");
        const data = await res.json();

        const container = document.getElementById("blocks-container");
        container.innerHTML = "";

        data.blocks.reverse().forEach(b => {
            const card = document.createElement("div");
            card.className = "block-card";
            
            let txHtml = "";
            b.transactions.forEach(tx => {
                if (tx.type === "GENESIS") {
                    txHtml += `<div class="tx-item"><span>🚀 GENESIS BLOCK INITIALIZED</span></div>`;
                } else {
                    txHtml += `
                        <div class="tx-item">
                            <span>🗳️ Vote Tx: <code>${tx.tx_id.substring(0, 14)}...</code></span>
                            <span>Candidate: <strong>${tx.candidate_id}</strong></span>
                            <span>Receipt: <code>${tx.voter_receipt.substring(0, 12)}...</code></span>
                        </div>
                    `;
                }
            });

            card.innerHTML = `
                <div class="block-header">
                    <div class="block-title">
                        <h4>Block #${b.index}</h4>
                        <span class="badge pos-badge">Forged by: ${b.validator_address}</span>
                    </div>
                    <span class="sub-text">${new Date(b.timestamp * 1000).toLocaleTimeString()}</span>
                </div>
                <div class="code-field">
                    <span class="code-label">Block Hash:</span>
                    <code>${b.hash}</code>
                </div>
                <div class="code-field">
                    <span class="code-label">Previous Hash:</span>
                    <code>${b.previous_hash}</code>
                </div>
                <div class="code-field">
                    <span class="code-label">Merkle Tree Root Hash:</span>
                    <code class="highlight-code">${b.merkle_root}</code>
                </div>
                <div class="tx-list">
                    <span class="code-label">Included Transactions (${b.transactions_count}):</span>
                    ${txHtml}
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Blockchain fetch error:", e);
    }
}

// --- PHASE 4: P2P NODES ---
async function loadP2PNodes() {
    try {
        const res = await fetch("/api/nodes");
        const data = await res.json();

        const grid = document.getElementById("p2p-nodes-grid");
        grid.innerHTML = "";

        data.topology.nodes.forEach(n => {
            const card = document.createElement("div");
            card.className = "node-card";
            card.innerHTML = `
                <div class="node-info">
                    <h4>${n.name} <span class="status-ok" style="padding: 2px 8px; font-size: 10px;">${n.status}</span></h4>
                    <p>Role: ${n.role} | Connected Peers: ${n.peers.join(", ")}</p>
                </div>
                <div class="node-stats">
                    <span class="stat-value">${data.topology.total_blocks} Blocks</span>
                </div>
            `;
            grid.appendChild(card);
        });

        // Load Mempool entries
        const mempoolRes = await fetch("/api/mempool");
        const mempoolData = await mempoolRes.json();
        const mempoolList = document.getElementById("mempool-list");
        mempoolList.innerHTML = "";

        if (mempoolData.transactions.length === 0) {
            mempoolList.innerHTML = `<p class="sub-text">No pending transactions in Mempool.</p>`;
        } else {
            mempoolData.transactions.forEach(tx => {
                const item = document.createElement("div");
                item.className = "tx-item";
                item.innerHTML = `
                    <span>🗳️ Pending Tx: <code>${tx.tx_id.substring(0, 16)}...</code></span>
                    <span>Nullifier: <code>${tx.voter_nullifier.substring(0, 12)}...</code></span>
                `;
                mempoolList.appendChild(item);
            });
        }
    } catch (e) {
        console.error("P2P error:", e);
    }
}

// --- PHASE 5: ELECTION TALLY & CHART ---
async function loadTally() {
    try {
        const res = await fetch("/api/tally");
        const data = await res.json();

        renderTallyChart(data.results);
        renderTallyTable(data);
    } catch (e) {
        console.error("Tally error:", e);
    }
}

function renderTallyChart(results) {
    const ctx = document.getElementById("tally-chart").getContext("2d");
    const labels = results.map(r => `${r.symbol} ${r.name}`);
    const votes = results.map(r => r.votes);

    if (tallyChartInstance) {
        tallyChartInstance.destroy();
    }

    tallyChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Votes Cast',
                data: votes,
                backgroundColor: [
                    'rgba(56, 189, 248, 0.7)',
                    'rgba(16, 185, 129, 0.7)',
                    'rgba(139, 92, 246, 0.7)',
                    'rgba(245, 158, 11, 0.7)'
                ],
                borderColor: [
                    '#38bdf8',
                    '#10b981',
                    '#8b5cf6',
                    '#f59e0b'
                ],
                borderWidth: 1.5,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: { precision: 0, color: '#94a3b8' },
                    grid: { color: 'rgba(56, 189, 248, 0.1)' }
                },
                x: {
                    ticks: { color: '#f8fafc' },
                    grid: { display: false }
                }
            }
        }
    });
}

function renderTallyTable(data) {
    const container = document.getElementById("tally-table-container");
    let rowsHtml = "";
    data.results.forEach(r => {
        rowsHtml += `
            <tr>
                <td><strong>${r.symbol} ${r.name}</strong></td>
                <td>${r.party}</td>
                <td><strong>${r.votes}</strong></td>
                <td><span class="badge pos-badge">${r.percentage}%</span></td>
            </tr>
        `;
    });

    container.innerHTML = `
        <table>
            <thead>
                <tr>
                    <th>Candidate</th>
                    <th>Party / Affiliation</th>
                    <th>Immutable Votes</th>
                    <th>Share</th>
                </tr>
            </thead>
            <tbody>
                ${rowsHtml}
            </tbody>
        </table>
    `;
}

// --- PHASE 5: RECEIPT VERIFIER ---
async function verifyReceipt() {
    const hash = document.getElementById("verify-receipt-input").value.trim();
    if (!hash) {
        showToast("Please enter a receipt hash.", "warning");
        return;
    }

    try {
        const res = await fetch("/api/verify_receipt", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ receipt_hash: hash })
        });
        const data = await res.json();

        const box = document.getElementById("verify-result-box");
        box.classList.remove("hidden");

        if (data.verified) {
            box.innerHTML = `
                <div class="status-ok">
                    <span>✔ VALIDATED ON BLOCKCHAIN</span>
                </div>
                <div class="code-field">
                    <span class="code-label">Confirmed Block Index:</span>
                    <code>Block #${data.block_index}</code>
                </div>
                <div class="code-field">
                    <span class="code-label">Block Hash:</span>
                    <code>${data.block_hash}</code>
                </div>
                <div class="code-field">
                    <span class="code-label">Forged By Validator:</span>
                    <code>${data.validator_address}</code>
                </div>
                <p class="sub-text">ℹ️ Your vote receipt is cryptographically locked inside Block #${data.block_index} and verified by Merkle Tree proof.</p>
            `;
        } else {
            box.innerHTML = `
                <div class="status-ok" style="background: rgba(244, 63, 94, 0.1); color: #f43f5e; border-color: rgba(244, 63, 94, 0.3);">
                    <span>✖ RECEIPT NOT FOUND</span>
                </div>
                <p class="sub-text">Receipt hash not found in any forged block yet. If you recently voted, forge the pending block first!</p>
            `;
        }
    } catch (e) {
        showToast("Error verifying receipt.", "danger");
    }
}
