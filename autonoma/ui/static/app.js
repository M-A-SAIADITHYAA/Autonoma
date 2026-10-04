document.addEventListener("DOMContentLoaded", () => {
    const scenarioPills = document.getElementById("scenarioPills");
    const taskInput = document.getElementById("taskInput");
    const scenarioBadge = document.getElementById("scenarioBadge");
    const btnRun = document.getElementById("btnRun");
    const btnReset = document.getElementById("btnReset");
    const btnRefreshErp = document.getElementById("btnRefreshErp");
    const chaosToggle = document.getElementById("chaosToggle");
    const traceContainer = document.getElementById("traceContainer");
    const planContainer = document.getElementById("planContainer");
    const milestonesList = document.getElementById("milestonesList");
    const planStats = document.getElementById("planStats");
    const certificateCard = document.getElementById("certificateCard");
    const emptyState = document.getElementById("emptyState");
    const invoicesTableBody = document.getElementById("invoicesTableBody");
    const invoiceCount = document.getElementById("invoiceCount");
    const auditList = document.getElementById("auditList");
    const supportTicketsList = document.getElementById("supportTicketsList");
    const supportLedgerList = document.getElementById("supportLedgerList");

    let currentScenarioId = "scenario_invoice_happy";
    let isExecuting = false;

    // Load Scenarios
    async function loadScenarios() {
        try {
            const res = await fetch("/api/scenarios");
            const data = await res.json();
            scenarioPills.innerHTML = "";
            data.scenarios.forEach((sc, idx) => {
                const btn = document.createElement("button");
                btn.className = `px-3 py-1.5 rounded-lg text-xs font-medium border transition text-left flex items-center space-x-1.5 ${
                    sc.id === currentScenarioId 
                        ? "bg-cyan-500/10 border-cyan-500/50 text-cyan-300 shadow-sm" 
                        : "bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
                }`;
                btn.innerHTML = `<span class="font-mono text-[10px] text-cyan-400">#${idx + 1}</span> <span>${sc.title.split(":")[0]}</span>`;
                btn.title = sc.description;
                btn.onclick = () => selectScenario(sc);
                scenarioPills.appendChild(btn);
            });
            selectScenario(data.scenarios[0]);
        } catch (e) {
            console.error("Failed to load scenarios", e);
        }
    }

    function selectScenario(sc) {
        currentScenarioId = sc.id;
        taskInput.value = sc.prompt;
        scenarioBadge.textContent = sc.title;
        chaosToggle.checked = !!sc.chaos;
        document.querySelectorAll("#scenarioPills button").forEach((b, i) => {
            const isMatch = b.innerHTML.includes(`#${i + 1}`);
            b.className = `px-3 py-1.5 rounded-lg text-xs font-medium border transition text-left flex items-center space-x-1.5 ${
                b.textContent.includes(sc.title.split(":")[0])
                    ? "bg-cyan-500/10 border-cyan-500/50 text-cyan-300 shadow-sm ring-1 ring-cyan-500/30"
                    : "bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200 hover:bg-slate-800"
            }`;
        });
    }

    // Refresh ERP state
    async function refreshErpState() {
        try {
            const res = await fetch("/api/erp/state");
            const data = await res.json();
            
            // Invoices
            invoiceCount.textContent = data.invoices.length;
            if (data.invoices.length === 0) {
                invoicesTableBody.innerHTML = `<tr><td colspan="6" class="p-4 text-center text-slate-500 italic">No invoices in ledger yet.</td></tr>`;
            } else {
                invoicesTableBody.innerHTML = data.invoices.map(inv => `
                    <tr class="border-b border-slate-800/60 hover:bg-slate-800/30">
                        <td class="p-2.5 font-mono text-slate-500">#${inv.id}</td>
                        <td class="p-2.5 font-semibold text-slate-200">${inv.invoice_number}</td>
                        <td class="p-2.5 text-slate-300">${inv.vendor}</td>
                        <td class="p-2.5 font-mono font-bold text-emerald-400">$${Number(inv.amount).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                        <td class="p-2.5 text-slate-400">${inv.due_date}</td>
                        <td class="p-2.5"><span class="px-2 py-0.5 rounded text-[10px] font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">${inv.status}</span></td>
                    </tr>
                `).join("");
            }

            // Audit Logs
            if (data.audit_logs.length === 0) {
                auditList.innerHTML = `<div class="text-slate-500 text-xs italic">No activity recorded.</div>`;
            } else {
                auditList.innerHTML = data.audit_logs.map(log => `
                    <div class="p-2 rounded bg-slate-900 border border-slate-800/80 flex justify-between items-start">
                        <div>
                            <span class="text-indigo-400 font-semibold">[${log.action}]</span>
                            <span class="text-slate-300">${log.details}</span>
                        </div>
                        <span class="text-[10px] text-slate-500 whitespace-nowrap ml-2">${log.timestamp}</span>
                    </div>
                `).join("");
            }

            // Support Desk
            if (data.tickets) {
                supportTicketsList.innerHTML = data.tickets.map(t => `
                    <div class="p-2.5 rounded bg-slate-900 border border-slate-800 text-xs">
                        <div class="flex justify-between font-semibold">
                            <span class="text-indigo-400">${t.ticket_id} - ${t.customer_name}</span>
                            <span class="px-1.5 py-0.5 rounded text-[10px] ${t.status === 'resolved' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-blue-500/20 text-blue-300'}">${t.status}</span>
                        </div>
                        <p class="text-slate-400 mt-1">${t.description}</p>
                        <div class="text-[11px] font-mono text-red-400 mt-1">Dispute Amount: $${t.disputed_amount.toFixed(2)}</div>
                    </div>
                `).join("");
            }

            if (data.ledger) {
                supportLedgerList.innerHTML = data.ledger.map(l => `
                    <div class="p-2 rounded bg-slate-900 border border-slate-800 text-xs flex justify-between items-center font-mono">
                        <span class="text-slate-200">${l.customer_name}</span>
                        <span class="text-emerald-400 font-bold">$${Number(l.balance).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                `).join("");
            }

        } catch (e) {
            console.error("ERP refresh error", e);
        }
    }

    // Run Task
    btnRun.onclick = async () => {
        if (isExecuting) return;
        const goal = taskInput.value.trim();
        if (!goal) return;

        isExecuting = true;
        btnRun.disabled = true;
        btnRun.innerHTML = `<i class="fa-solid fa-spinner fa-spin mr-2"></i> Reasoning & Executing...`;
        
        // Reset view
        if (emptyState) emptyState.remove();
        traceContainer.innerHTML = "";
        certificateCard.classList.add("hidden");
        planContainer.classList.remove("hidden");

        try {
            const res = await fetch("/api/run", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({
                    goal: goal,
                    scenario_id: currentScenarioId,
                    chaos_mode: chaosToggle.checked,
                    interactive: false,
                    auto_approve: true
                })
            });

            const data = await res.json();
            renderExecutionTrace(data.steps, data.bundle);
            await refreshErpState();
        } catch (e) {
            console.error("Execution failed", e);
            traceContainer.innerHTML += `<div class="p-4 rounded-xl bg-red-950/50 border border-red-800 text-red-200 text-xs">Execution Error: ${e.message}</div>`;
        } finally {
            isExecuting = false;
            btnRun.disabled = false;
            btnRun.innerHTML = `<i class="fa-solid fa-play text-xs mr-2"></i> Execute Task Autonomously`;
        }
    };

    function renderExecutionTrace(steps, bundle) {
        // Render Milestones
        if (bundle.extracted_entities) {
            const milestones = [
                "Locate Invoice", "Extract Data", "Safety / HITL", "ERP Entry", "Self-Verification"
            ];
            milestonesList.innerHTML = milestones.map((m, idx) => `
                <div class="px-2.5 py-1 rounded-md text-[11px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 whitespace-nowrap flex items-center space-x-1.5">
                    <i class="fa-solid fa-check text-[9px]"></i>
                    <span>${m}</span>
                </div>
            `).join("");
            planStats.textContent = "5 / 5 Complete";
        }

        // Render Step Cards
        traceContainer.innerHTML = steps.map(step => {
            const obs = step.observation;
            const isSuccess = obs && obs.status === "success";
            const obsBadge = isSuccess 
                ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">SUCCESS</span>`
                : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30">ERROR</span>`;

            return `
                <div class="step-card bg-slate-900/90 border border-slate-800 rounded-xl p-4 space-y-3 shadow-md">
                    <div class="flex items-center justify-between border-b border-slate-800/80 pb-2">
                        <div class="flex items-center space-x-2">
                            <span class="w-6 h-6 rounded-md bg-indigo-600/30 border border-indigo-500/40 text-indigo-300 font-mono text-xs flex items-center justify-center font-bold">${step.step_number}</span>
                            <span class="text-xs font-semibold text-slate-300">${step.milestone || "Execution"}</span>
                        </div>
                        <span class="text-[10px] text-slate-500 font-mono">${obs ? obs.elapsed_ms.toFixed(1) + "ms" : ""}</span>
                    </div>

                    <!-- Thought -->
                    <div class="text-xs text-slate-300 space-y-1 bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60">
                        <div class="text-[10px] font-bold uppercase tracking-wider text-amber-400 flex items-center">
                            <i class="fa-solid fa-brain mr-1.5"></i> Agent Reasoning
                        </div>
                        <p class="leading-relaxed">${step.thought}</p>
                    </div>

                    <!-- Action & Params -->
                    <div class="flex items-start justify-between bg-slate-950/80 p-2.5 rounded-lg border border-slate-800/80 font-mono text-xs">
                        <div class="space-y-1 w-full">
                            <div class="text-[10px] font-bold uppercase tracking-wider text-cyan-400 flex items-center">
                                <i class="fa-solid fa-bolt mr-1.5"></i> Tool: ${step.action.tool_name}
                            </div>
                            <pre class="text-[11px] text-slate-400 overflow-x-auto">${JSON.stringify(step.action.parameters, null, 2)}</pre>
                        </div>
                    </div>

                    <!-- Observation -->
                    ${obs ? `
                        <div class="text-xs bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60 space-y-1">
                            <div class="flex items-center justify-between">
                                <span class="text-[10px] font-bold uppercase tracking-wider text-purple-400 flex items-center">
                                    <i class="fa-solid fa-eye mr-1.5"></i> Observation
                                </span>
                                ${obsBadge}
                            </div>
                            <div class="text-slate-300 text-[11px]">
                                ${obs.error_message ? `<span class="text-red-400 font-medium">${obs.error_message}</span>` : `<pre class="text-[11px] text-slate-400 overflow-x-auto">${JSON.stringify(obs.data, null, 2)}</pre>`}
                            </div>
                        </div>
                    ` : ""}

                    ${step.reflection ? `
                        <div class="text-[11px] text-emerald-300/90 italic bg-emerald-950/20 border border-emerald-800/30 p-2 rounded-lg">
                            <i class="fa-solid fa-sparkles mr-1 text-emerald-400"></i> ${step.reflection}
                        </div>
                    ` : ""}
                </div>
            `;
        }).join("");

        // Render Completion Card & Verification Checks
        certificateCard.classList.remove("hidden");
        const inv = bundle.extracted_entities.extracted_invoice || {};
        const checksHtml = (bundle.verifications || []).map(chk => `
            <tr class="border-b border-slate-800/60">
                <td class="p-2 font-medium text-slate-200">${chk.description}</td>
                <td class="p-2 text-slate-400 font-mono">${chk.expected_outcome}</td>
                <td class="p-2 text-slate-300 font-mono">${chk.actual_outcome}</td>
                <td class="p-2 text-right">
                    ${chk.passed 
                        ? `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">PASS ✓</span>`
                        : `<span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/40">FAIL ✗</span>`}
                </td>
            </tr>
        `).join("");

        certificateCard.innerHTML = `
            <div class="bg-gradient-to-br from-slate-900 to-indigo-950/40 border border-cyan-500/30 rounded-2xl p-5 shadow-2xl space-y-4">
                <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                    <div class="flex items-center space-x-2">
                        <div class="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold">✓</div>
                        <div>
                            <h3 class="text-sm font-bold text-white">Task Completion Certificate</h3>
                            <span class="text-[10px] text-slate-400 font-mono">Proof Receipt: <strong class="text-amber-400">${bundle.receipt_id}</strong></span>
                        </div>
                    </div>
                    <span class="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                        STATUS: ${bundle.status.toUpperCase()}
                    </span>
                </div>

                <div class="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                    <div class="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                        <span class="text-[10px] text-slate-500 uppercase block">Total Steps</span>
                        <span class="font-bold text-white font-mono text-sm">${bundle.total_steps}</span>
                    </div>
                    <div class="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                        <span class="text-[10px] text-slate-500 uppercase block">Retries Handled</span>
                        <span class="font-bold text-emerald-400 font-mono text-sm">${bundle.retries_attempted}</span>
                    </div>
                    <div class="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                        <span class="text-[10px] text-slate-500 uppercase block">Extracted Amount</span>
                        <span class="font-bold text-cyan-400 font-mono text-sm">$${Number(inv.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                    </div>
                    <div class="bg-slate-950/80 p-2.5 rounded-lg border border-slate-800">
                        <span class="text-[10px] text-slate-500 uppercase block">Verified Due Date</span>
                        <span class="font-bold text-white font-mono text-sm">${inv.due_date || "N/A"}</span>
                    </div>
                </div>

                <!-- Verifications Table -->
                <div class="space-y-1.5">
                    <span class="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center">
                        <i class="fa-solid fa-check-double text-cyan-400 mr-1.5"></i> Independent Verification Checks
                    </span>
                    <div class="bg-slate-950/80 rounded-xl border border-slate-800 overflow-hidden">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-slate-900 text-slate-400 text-[10px] uppercase font-semibold border-b border-slate-800">
                                <tr>
                                    <th class="p-2">Check Description</th>
                                    <th class="p-2">Expected</th>
                                    <th class="p-2">Actual Outcome</th>
                                    <th class="p-2 text-right">Result</th>
                                </tr>
                            </thead>
                            <tbody>${checksHtml}</tbody>
                        </table>
                    </div>
                </div>

                <div class="p-3 bg-slate-950/90 rounded-xl border border-slate-800/80 text-xs text-slate-300">
                    <strong class="text-white block mb-0.5">Concise Summary:</strong>
                    ${bundle.summary_text}
                </div>
            </div>
        `;

        traceContainer.scrollTop = traceContainer.scrollHeight;
    }

    // Load Drive Files & Documents
    async function loadDriveFiles() {
        try {
            const res = await fetch("/api/drive/files");
            const data = await res.json();
            const container = document.getElementById("driveFilesList");
            if (!container) return;
            
            if (data.files.length === 0) {
                container.innerHTML = `<div class="text-slate-500 text-xs italic">No documents found in drive.</div>`;
                return;
            }

            container.innerHTML = data.files.map(f => {
                const isPdf = f.type === ".pdf";
                const icon = isPdf ? "fa-file-pdf text-red-400" : (f.type === ".json" ? "fa-file-code text-amber-400" : "fa-file-lines text-indigo-400");
                const viewUrl = `/api/drive/view/${encodeURIComponent(f.rel_path)}`;
                return `
                    <div class="p-2.5 rounded-xl bg-slate-900 border border-slate-800/80 hover:border-slate-700 flex items-center justify-between transition">
                        <div class="flex items-center space-x-2.5 overflow-hidden">
                            <i class="fa-solid ${icon} text-lg"></i>
                            <div class="overflow-hidden">
                                <div class="text-xs font-semibold text-slate-200 truncate">${f.name}</div>
                                <div class="text-[10px] text-slate-500 font-mono">${(f.size / 1024).toFixed(1)} KB</div>
                            </div>
                        </div>
                        <a href="${viewUrl}" target="_blank" class="px-2.5 py-1 rounded-md text-[11px] font-medium bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 transition flex items-center space-x-1 shrink-0">
                            <span>Open ${isPdf ? "PDF" : "File"}</span>
                            <i class="fa-solid fa-arrow-up-right-from-square text-[9px]"></i>
                        </a>
                    </div>
                `;
            }).join("");
        } catch (e) {
            console.error("Failed to load drive files", e);
        }
    }

    // Tab switcher
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.onclick = () => {
            const target = btn.dataset.tab;
            document.querySelectorAll(".tab-btn").forEach(b => {
                b.className = "tab-btn px-3 py-1.5 rounded-lg text-xs font-semibold text-slate-400 hover:text-white hover:bg-slate-800";
            });
            btn.className = "tab-btn px-3 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white";

            document.getElementById("tabContent-invoices").classList.toggle("hidden", target !== "invoices");
            document.getElementById("tabContent-files").classList.toggle("hidden", target !== "files");
            document.getElementById("tabContent-audit").classList.toggle("hidden", target !== "audit");
            document.getElementById("tabContent-support").classList.toggle("hidden", target !== "support");

            if (target === "files") {
                loadDriveFiles();
            }
        };
    });

    // Reset button
    btnReset.onclick = async () => {
        try {
            await fetch("/api/reset", {method: "POST"});
            await refreshErpState();
            await loadDriveFiles();
            alert("Simulated enterprise environment & database reset successfully.");
        } catch (e) {
            console.error(e);
        }
    };

    btnRefreshErp.onclick = () => {
        refreshErpState();
        loadDriveFiles();
    };

    // Initial load
    loadScenarios();
    refreshErpState();
    loadDriveFiles();
    setInterval(refreshErpState, 3000);
});
