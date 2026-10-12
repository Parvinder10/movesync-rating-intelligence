/**
 * MoveSync Rating Intelligence — Interactive Dashboard Client
 * Powers evidence exploration, prioritization registers, MoM comparisons, and action tracking.
 */

let currentPeriod = "2026-10";
let evidencePage = 1;
const evidenceLimit = 20;

let overviewRatingChart = null;
let overviewThemeChart = null;
let momTrendChart = null;

// Initialize when DOM is ready
document.addEventListener("DOMContentLoaded", async () => {
  if (window.lucide) {
    lucide.createIcons();
  }

  setupTabNavigation();
  setupEventListeners();

  await loadAppInfo();
  await loadPeriodOptions();
  await loadOverviewData();
  await loadEvidenceData();
  await loadPrioritiesData();
  await loadMomData();
  await loadActionsData();
  await loadReportsData();
});

function setupTabNavigation() {
  const tabs = document.querySelectorAll(".nav-tab");
  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      const targetId = tab.getAttribute("data-tab");
      switchTab(targetId);
    });
  });
}

function switchTab(targetId) {
  document.querySelectorAll(".nav-tab").forEach(t => {
    const isActive = t.getAttribute("data-tab") === targetId;
    t.classList.toggle("active", isActive);
    t.classList.toggle("text-blue-400", isActive);
    t.classList.toggle("border-blue-500", isActive);
    t.classList.toggle("text-slate-400", !isActive);
    t.classList.toggle("border-transparent", !isActive);
  });

  document.querySelectorAll(".tab-content").forEach(c => {
    c.classList.toggle("hidden", c.id !== targetId);
  });

  if (window.lucide) {
    lucide.createIcons();
  }
}

function setupEventListeners() {
  // Evidence filters
  document.getElementById("applyFiltersBtn")?.addEventListener("click", () => {
    evidencePage = 1;
    loadEvidenceData();
  });
  document.getElementById("resetFiltersBtn")?.addEventListener("click", () => {
    document.getElementById("filterQuery").value = "";
    document.getElementById("filterScore").value = "";
    document.getElementById("filterTheme").value = "";
    document.getElementById("filterPeriod").value = "";
    evidencePage = 1;
    loadEvidenceData();
  });

  document.getElementById("prevPageBtn")?.addEventListener("click", () => {
    if (evidencePage > 1) {
      evidencePage--;
      loadEvidenceData();
    }
  });
  document.getElementById("nextPageBtn")?.addEventListener("click", () => {
    evidencePage++;
    loadEvidenceData();
  });

  // Priorities period select
  document.getElementById("priorityPeriodSelect")?.addEventListener("change", (e) => {
    loadPrioritiesData(e.target.value);
  });

  // MoM run compare
  document.getElementById("runMomCompareBtn")?.addEventListener("click", () => {
    const curr = document.getElementById("momCurrentPeriodSelect").value;
    const prev = document.getElementById("momPreviousPeriodSelect").value;
    loadMomData(curr, prev);
  });

  // Run modal triggers
  const runModal = document.getElementById("runModal");
  document.getElementById("openRunModalBtn")?.addEventListener("click", () => {
    runModal.classList.remove("hidden");
  });
  document.getElementById("closeRunModalBtn")?.addEventListener("click", () => {
    runModal.classList.add("hidden");
  });
  document.getElementById("cancelModalBtn")?.addEventListener("click", () => {
    runModal.classList.add("hidden");
  });

  // Execute monthly run
  document.getElementById("executeRunBtn")?.addEventListener("click", executeMonthlyRun);

  // Action modal triggers
  const actionModal = document.getElementById("actionModal");
  document.getElementById("closeActionModalBtn")?.addEventListener("click", () => {
    actionModal.classList.add("hidden");
  });
  document.getElementById("cancelActionModalBtn")?.addEventListener("click", () => {
    actionModal.classList.add("hidden");
  });
  document.getElementById("saveActionChangesBtn")?.addEventListener("click", saveActionChanges);
}

// -------------------------------------------------------------
// API Data Loaders
// -------------------------------------------------------------

async function loadAppInfo() {
  try {
    const res = await fetch("/api/app-info");
    const data = await res.json();
    document.getElementById("appTitle").textContent = data.title || "MoveInSync";
    document.getElementById("appPackageId").textContent = data.app_id || "com.moveinsync.ets";
    document.getElementById("appDev").textContent = data.developer || "MoveInSync";
    document.getElementById("appGenre").textContent = data.genre || "Maps & Navigation";
    document.getElementById("appInstalls").textContent = data.installs || "1,000,000+";
    document.getElementById("storeRating").textContent = `${data.store_rating.toFixed(2)}★`;
  } catch (err) {
    console.error("Failed to load app info:", err);
  }
}

async function loadPeriodOptions() {
  try {
    const res = await fetch("/api/investigation/runs");
    const data = await res.json();
    const periods = (data.runs || []).map(r => r.reporting_period);

    if (periods.length > 0) {
      currentPeriod = periods[0];
      document.getElementById("currentPeriodDisplay").textContent = currentPeriod;
    }

    const populateSelect = (selectId, defaultVal) => {
      const select = document.getElementById(selectId);
      if (!select) return;
      select.innerHTML = "";
      periods.forEach(p => {
        const opt = document.createElement("option");
        opt.value = p;
        opt.textContent = p;
        if (p === defaultVal) opt.selected = true;
        select.appendChild(opt);
      });
    };

    populateSelect("filterPeriod", "");
    populateSelect("priorityPeriodSelect", currentPeriod);
    populateSelect("momCurrentPeriodSelect", currentPeriod);
    populateSelect("momPreviousPeriodSelect", periods[1] || currentPeriod);
  } catch (err) {
    console.error("Failed to load period options:", err);
  }
}

async function loadOverviewData() {
  try {
    const res = await fetch("/api/investigation/latest");
    if (!res.ok) return;
    const data = await res.json();
    const run = data.run;
    const issues = data.issues || [];

    document.getElementById("sampleRating").textContent = `${run.sample_rating.toFixed(2)}★`;
    const critShare = (run.critical_review_count / Math.max(1, run.period_review_count) * 100).toFixed(1);
    document.getElementById("criticalShare").textContent = `${critShare}%`;

    // 1. Overview Rating Chart
    renderOverviewRatingChart(run.rating_distribution);

    // 2. Overview Theme Chart
    renderOverviewThemeChart(issues);

    // 3. Overview Priorities Table
    const tbody = document.getElementById("overviewPrioritiesTbody");
    tbody.innerHTML = "";
    issues.slice(0, 5).forEach(issue => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition";
      tr.innerHTML = `
        <td class="py-2.5 px-3 font-bold text-slate-900">#${issue.priority_rank}</td>
        <td class="py-2.5 px-3">
          <div class="font-semibold text-slate-800">${issue.theme_name}</div>
          <div class="text-[10px] text-slate-400 font-mono">${issue.theme_code}</div>
        </td>
        <td class="py-2.5 px-3 font-semibold text-rose-600">${issue.prevalence_pct.toFixed(1)}% <span class="text-[10px] text-slate-400">(${issue.critical_count} revs)</span></td>
        <td class="py-2.5 px-3 font-mono">${issue.avg_rating.toFixed(2)}★</td>
        <td class="py-2.5 px-3 font-black text-slate-900">${issue.priority_score.toFixed(2)}</td>
        <td class="py-2.5 px-3 text-slate-500 max-w-xs truncate" title="${issue.root_cause_hypothesis || ''}">${issue.root_cause_hypothesis || 'N/A'}</td>
        <td class="py-2.5 px-3">
          <button class="text-blue-600 hover:text-blue-800 font-medium" onclick="switchTab('tab-priorities')">Details</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to load overview data:", err);
  }
}

function renderOverviewRatingChart(dist) {
  const ctx = document.getElementById("overviewRatingChart")?.getContext("2d");
  if (!ctx) return;

  if (overviewRatingChart) overviewRatingChart.destroy();

  const labels = ["1★", "2★", "3★", "4★", "5★"];
  const sampleCounts = [dist["1"] || 0, dist["2"] || 0, dist["3"] || 0, dist["4"] || 0, dist["5"] || 0];

  overviewRatingChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: "Sample Reviews in Period",
        data: sampleCounts,
        backgroundColor: ["#ef4444", "#f97316", "#eab308", "#3b82f6", "#10b981"],
        borderRadius: 4
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false }
      },
      scales: {
        y: { beginAtZero: true, grid: { color: "#f1f5f9" } },
        x: { grid: { display: false } }
      }
    }
  });
}

function renderOverviewThemeChart(issues) {
  const ctx = document.getElementById("overviewThemeChart")?.getContext("2d");
  if (!ctx) return;

  if (overviewThemeChart) overviewThemeChart.destroy();

  const top6 = issues.slice(0, 6);
  const labels = top6.map(i => i.theme_name);
  const data = top6.map(i => i.prevalence_pct);

  overviewThemeChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: ["#f43f5e", "#fb923c", "#f59e0b", "#3b82f6", "#8b5cf6", "#10b981"],
        borderWidth: 2,
        borderColor: "#ffffff"
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right", labels: { boxWidth: 12, font: { size: 10 } } }
      }
    }
  });
}

async function loadEvidenceData() {
  const query = document.getElementById("filterQuery")?.value || "";
  const score = document.getElementById("filterScore")?.value || "";
  const theme = document.getElementById("filterTheme")?.value || "";
  const period = document.getElementById("filterPeriod")?.value || "";

  const offset = (evidencePage - 1) * evidenceLimit;

  let url = `/api/reviews?limit=${evidenceLimit}&offset=${offset}`;
  if (query) url += `&query=${encodeURIComponent(query)}`;
  if (score) url += `&score=${encodeURIComponent(score)}`;
  if (theme) url += `&theme=${encodeURIComponent(theme)}`;
  if (period) url += `&period=${encodeURIComponent(period)}`;

  // Update export button link
  const exportBtn = document.getElementById("exportReviewsCsvBtn");
  if (exportBtn) {
    exportBtn.href = `/api/export/reviews.csv?period=${encodeURIComponent(period)}`;
  }

  try {
    const res = await fetch(url);
    const data = await res.json();

    document.getElementById("evidenceShowingCount").textContent = data.reviews.length;
    document.getElementById("evidenceTotalCount").textContent = data.total;
    document.getElementById("pageIndicator").textContent = `Page ${evidencePage} of ${Math.max(1, Math.ceil(data.total / evidenceLimit))}`;

    const container = document.getElementById("reviewsContainer");
    container.innerHTML = "";

    if (data.reviews.length === 0) {
      container.innerHTML = `<div class="p-8 text-center text-slate-400 bg-white rounded-xl border border-slate-200">No reviews matched your filters.</div>`;
      return;
    }

    data.reviews.forEach(r => {
      const card = document.createElement("div");
      card.className = "bg-white p-4 rounded-xl border border-slate-200 shadow-sm hover:border-slate-300 transition space-y-2";

      const starColors = ["text-slate-300", "text-rose-500", "text-orange-500", "text-amber-500", "text-blue-500", "text-emerald-500"];
      const starsHtml = "★".repeat(r.score) + "☆".repeat(5 - r.score);

      card.innerHTML = `
        <div class="flex items-center justify-between text-xs">
          <div class="flex items-center space-x-2">
            <span class="font-bold text-sm ${starColors[r.score]}">${starsHtml}</span>
            <span class="font-semibold text-slate-800">${r.user_name || 'Anonymous Commuter'}</span>
            <span class="text-slate-400">•</span>
            <span class="text-slate-500 font-mono text-[11px]">${r.review_date}</span>
            <span class="text-slate-400">•</span>
            <span class="bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded text-[10px] font-mono">v${r.app_version || 'unknown'}</span>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-[10px] uppercase font-bold px-2 py-0.5 rounded ${r.sentiment === 'negative' ? 'bg-rose-50 text-rose-700 border border-rose-200' : (r.sentiment === 'positive' ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-50 text-slate-700')}">
              ${r.sentiment}
            </span>
            <span class="text-[10px] font-semibold bg-blue-50 text-blue-700 px-2 py-0.5 rounded border border-blue-200 font-mono">
              ${r.primary_theme}
            </span>
          </div>
        </div>

        <p class="text-xs text-slate-700 leading-relaxed font-sans bg-slate-50/50 p-2.5 rounded-lg border border-slate-100">
          ${escapeHtml(r.cleaned_content)}
        </p>

        ${r.reply_content ? `
          <div class="mt-2 text-xs bg-indigo-50/70 p-2.5 rounded-lg border border-indigo-100">
            <div class="font-bold text-indigo-900 text-[10px] uppercase tracking-wider mb-0.5">MoveInSync Developer Response:</div>
            <p class="text-slate-700 text-[11px]">${escapeHtml(r.reply_content)}</p>
          </div>
        ` : ''}
      `;
      container.appendChild(card);
    });

    if (window.lucide) lucide.createIcons();
  } catch (err) {
    console.error("Failed to load evidence reviews:", err);
  }
}

async function loadPrioritiesData(period = currentPeriod) {
  try {
    const res = await fetch(`/api/priorities?period=${period}`);
    if (!res.ok) return;
    const data = await res.json();
    const tbody = document.getElementById("prioritiesTableTbody");
    tbody.innerHTML = "";

    data.issues.forEach(item => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition";

      let rankShiftHtml = "";
      if (item.is_new) {
        rankShiftHtml = `<span class="text-[10px] bg-purple-100 text-purple-800 px-1.5 py-0.5 rounded font-mono">NEW</span>`;
      } else if (item.rank_delta > 0) {
        rankShiftHtml = `<span class="text-[10px] text-rose-600 font-bold font-mono">↑ +${item.rank_delta}</span>`;
      } else if (item.rank_delta < 0) {
        rankShiftHtml = `<span class="text-[10px] text-emerald-600 font-bold font-mono">↓ ${item.rank_delta}</span>`;
      } else {
        rankShiftHtml = `<span class="text-[10px] text-slate-400 font-mono">= 0</span>`;
      }

      tr.innerHTML = `
        <td class="py-3 px-3">
          <div class="flex items-center space-x-1.5">
            <span class="text-sm font-bold text-slate-900">#${item.priority_rank}</span>
            ${rankShiftHtml}
          </div>
        </td>
        <td class="py-3 px-3">
          <div class="font-bold text-slate-800 text-xs">${item.theme_name}</div>
          <div class="text-[10px] text-slate-400 font-mono">${item.theme_code}</div>
        </td>
        <td class="py-3 px-3">
          <div class="font-bold text-rose-600">${item.prevalence_pct.toFixed(1)}%</div>
          <div class="text-[10px] text-slate-400">${item.critical_count} critical</div>
        </td>
        <td class="py-3 px-3 font-mono">${item.severity_score.toFixed(1)}</td>
        <td class="py-3 px-3 font-mono">${item.impact_score.toFixed(1)}</td>
        <td class="py-3 px-3 font-mono">${item.confidence_score.toFixed(1)}</td>
        <td class="py-3 px-3 font-mono">${item.effort_score.toFixed(1)}</td>
        <td class="py-3 px-3">
          <span class="text-sm font-black text-slate-900 bg-slate-100 px-2 py-1 rounded border border-slate-200">
            ${item.priority_score.toFixed(2)}
          </span>
        </td>
        <td class="py-3 px-3 text-slate-600 text-[11px] max-w-xs">
          ${item.theme_code === 'FORCED_RATING_MODAL' || item.theme_code === 'AUTH_LOGIN_OTP' ?
            '<b>ACT-001:</b> Decouple rating modal and remove OTP gatekeeper.' :
            (item.theme_code === 'LIVE_TRACKING_GPS' ? '<b>ACT-002:</b> Foreground GPS polling sync.' : '<b>ACT-003:</b> Driver geofence arrival check.')
          }
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to load priorities:", err);
  }
}

async function loadMomData(currPeriod = currentPeriod, prevPeriod = null) {
  try {
    let url = `/api/comparison?current_period=${currPeriod}`;
    if (prevPeriod) url += `&previous_period=${prevPeriod}`;
    const res = await fetch(url);
    const data = await res.json();

    // Delta KPIs
    if (data.volume.delta !== null) {
      document.getElementById("momVolDelta").textContent = `${data.volume.delta >= 0 ? '+' : ''}${data.volume.delta}`;
      document.getElementById("momVolPct").textContent = `(${data.volume.pct_change >= 0 ? '+' : ''}${data.volume.pct_change}%)`;
      document.getElementById("momVolCounts").textContent = `Current: ${data.volume.current} | Previous: ${data.volume.previous}`;
    }

    if (data.rating.delta !== null) {
      document.getElementById("momRatingDelta").textContent = `${data.rating.delta >= 0 ? '+' : ''}${data.rating.delta.toFixed(2)}`;
      document.getElementById("momRatingLevels").textContent = `Current: ${data.rating.current.toFixed(2)}★ | Previous: ${data.rating.previous.toFixed(2)}★`;
    }

    if (data.critical_pct.delta !== null) {
      document.getElementById("momCritDelta").textContent = `${data.critical_pct.delta >= 0 ? '+' : ''}${data.critical_pct.delta.toFixed(1)}`;
      document.getElementById("momCritLevels").textContent = `Current: ${data.critical_pct.current.toFixed(1)}% | Previous: ${data.critical_pct.previous.toFixed(1)}%`;
    }

    // Trajectories Table
    const tbody = document.getElementById("momTrajectoriesTbody");
    tbody.innerHTML = "";
    (data.theme_trajectories || []).forEach(t => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition";

      let statusBadge = "status-persistent";
      if (t.status === "Emerging / New") statusBadge = "status-new";
      else if (t.status === "Improving") statusBadge = "status-improving";
      else if (t.status === "Worsening") statusBadge = "status-worsening";

      tr.innerHTML = `
        <td class="py-2.5 px-3 font-semibold text-slate-800">${t.theme_name}</td>
        <td class="py-2.5 px-3">
          <span class="text-[10px] font-bold px-2 py-0.5 rounded ${statusBadge}">${t.status}</span>
        </td>
        <td class="py-2.5 px-3 font-mono">${t.current_share_pct.toFixed(1)}%</td>
        <td class="py-2.5 px-3 font-mono">${t.previous_share_pct.toFixed(1)}%</td>
        <td class="py-2.5 px-3 font-bold ${t.share_delta_pct > 0 ? 'text-rose-600' : (t.share_delta_pct < 0 ? 'text-emerald-600' : 'text-slate-500')}">
          ${t.share_delta_pct >= 0 ? '+' : ''}${t.share_delta_pct.toFixed(1)}%
        </td>
        <td class="py-2.5 px-3 font-mono text-slate-600">#${t.current_rank || 'N/A'}</td>
      `;
      tbody.appendChild(tr);
    });

    // 12-Month Longitudinal Trend Chart
    await renderMomLongitudinalChart();
  } catch (err) {
    console.error("Failed to load MoM comparison:", err);
  }
}

async function renderMomLongitudinalChart() {
  const ctx = document.getElementById("momTrendChart")?.getContext("2d");
  if (!ctx) return;

  const res = await fetch("/api/investigation/runs");
  const data = await res.json();
  const runs = (data.runs || []).slice().reverse(); // Chronological

  const labels = runs.map(r => r.reporting_period);
  const volumes = runs.map(r => r.period_review_count);
  const ratings = runs.map(r => r.sample_rating);

  if (momTrendChart) momTrendChart.destroy();

  momTrendChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [
        {
          label: "Sample Average Rating (Stars)",
          data: ratings,
          borderColor: "#2563eb",
          backgroundColor: "#2563eb",
          yAxisID: "yRating",
          tension: 0.2,
          pointRadius: 4
        },
        {
          label: "Monthly Review Volume",
          data: volumes,
          type: "bar",
          backgroundColor: "#cbd5e1",
          yAxisID: "yVol",
          borderRadius: 4
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        yRating: {
          type: "linear",
          position: "left",
          min: 3.0,
          max: 5.0,
          grid: { color: "#f8fafc" }
        },
        yVol: {
          type: "linear",
          position: "right",
          beginAtZero: true,
          grid: { display: false }
        }
      }
    }
  });
}

async function loadActionsData() {
  try {
    const res = await fetch("/api/actions");
    const data = await res.json();
    const container = document.getElementById("actionsListContainer");
    container.innerHTML = "";

    (data.actions || []).forEach(act => {
      const card = document.createElement("div");
      card.className = "bg-white p-5 rounded-xl border border-slate-200 shadow-sm space-y-3";

      let statusBadge = "bg-slate-100 text-slate-700";
      if (act.status === "in_progress") statusBadge = "bg-blue-100 text-blue-800 border border-blue-200";
      else if (act.status === "implemented") statusBadge = "bg-emerald-100 text-emerald-800 border border-emerald-200";
      else if (act.status === "investigating") statusBadge = "bg-amber-100 text-amber-800 border border-amber-200";

      let outcomeBadge = "bg-slate-100 text-slate-700";
      if (act.outcome_label === "observed_association") outcomeBadge = "bg-emerald-50 text-emerald-800 border border-emerald-200";
      else if (act.outcome_label === "inconclusive") outcomeBadge = "bg-amber-50 text-amber-800 border border-amber-200";

      card.innerHTML = `
        <div class="flex items-start justify-between">
          <div>
            <div class="flex items-center space-x-2">
              <span class="font-mono font-bold text-xs bg-slate-900 text-white px-2 py-0.5 rounded">${act.action_id}</span>
              <span class="text-xs font-bold ${act.priority_level.startsWith('P0') ? 'badge-p0' : 'badge-p1'} px-2 py-0.5 rounded">${act.priority_level}</span>
              <h4 class="text-sm font-bold text-slate-900">${act.title}</h4>
            </div>
            <div class="text-xs text-slate-500 mt-1">Owner: <span class="font-semibold text-slate-700">${act.owner}</span> | Target Review: <span class="font-mono">${act.target_review_date || 'N/A'}</span></div>
          </div>
          <div class="flex items-center space-x-2">
            <span class="text-xs uppercase font-bold px-2 py-0.5 rounded ${statusBadge}">${act.status.replace('_', ' ')}</span>
            <button class="text-xs px-2.5 py-1 bg-slate-100 hover:bg-slate-200 rounded font-medium text-slate-700" onclick="openEditActionModal('${act.action_id}')">Edit Status</button>
          </div>
        </div>

        <p class="text-xs text-slate-600 leading-relaxed">${act.description}</p>

        <div class="bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs grid grid-cols-1 md:grid-cols-3 gap-3">
          <div>
            <div class="text-[10px] text-slate-400 uppercase font-semibold">Baseline Metric</div>
            <div class="font-bold text-slate-800">${act.baseline_metric_name}: <span class="font-mono text-rose-600">${act.baseline_metric_value}%</span></div>
          </div>
          <div>
            <div class="text-[10px] text-slate-400 uppercase font-semibold">Target vs Latest</div>
            <div class="font-bold text-slate-800">Target: <span class="font-mono text-emerald-600">${act.target_metric_value}%</span> | Latest: <span class="font-mono text-blue-600">${act.latest_metric_value !== null ? act.latest_metric_value + '%' : 'Pending'}</span></div>
          </div>
          <div>
            <div class="text-[10px] text-slate-400 uppercase font-semibold">Outcome Label (Guardrailed)</div>
            <span class="inline-block mt-0.5 text-[11px] font-bold px-2 py-0.5 rounded ${outcomeBadge}">${act.outcome_label.replace('_', ' ')}</span>
          </div>
        </div>

        <div class="text-xs text-slate-500 bg-amber-50/50 p-2 rounded border border-amber-100">
          <b>Evaluation Limitations & Next Step:</b> ${act.limitations || 'N/A'} Next: <i>${act.next_decision || 'N/A'}</i>
        </div>
      `;
      container.appendChild(card);
    });
  } catch (err) {
    console.error("Failed to load actions:", err);
  }
}

async function loadReportsData() {
  try {
    const res = await fetch("/api/reports");
    const data = await res.json();
    const tbody = document.getElementById("reportsTableTbody");
    tbody.innerHTML = "";

    (data.reports || []).forEach(rep => {
      const tr = document.createElement("tr");
      tr.className = "hover:bg-slate-50 transition";
      tr.innerHTML = `
        <td class="py-2.5 px-3 font-bold text-slate-900">${rep.reporting_period}</td>
        <td class="py-2.5 px-3 font-mono text-[11px] text-slate-500">${rep.report_id}</td>
        <td class="py-2.5 px-3 text-slate-500 font-mono text-[11px]">${rep.created_at.slice(0, 19).replace('T', ' ')}</td>
        <td class="py-2.5 px-3 text-slate-600">MoveInSync_Case_Study.pdf (8 Pages)</td>
        <td class="py-2.5 px-3">
          <a href="/api/reports/${rep.reporting_period}/pdf" target="_blank" class="text-blue-600 hover:text-blue-800 font-medium">Download PDF</a>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Failed to load reports archive:", err);
  }
}

// -------------------------------------------------------------
// Interactive Operations Handlers
// -------------------------------------------------------------

async function executeMonthlyRun() {
  const period = document.getElementById("modalPeriodInput").value;
  const liveCollect = document.getElementById("modalLiveCollectCheck").checked;
  const statusArea = document.getElementById("modalStatusArea");
  const btnText = document.getElementById("executeBtnText");

  statusArea.classList.remove("hidden");
  statusArea.className = "p-3 rounded-lg text-xs bg-blue-50 text-blue-800 border border-blue-200";
  statusArea.textContent = `Executing investigation pipeline for ${period}...`;
  btnText.textContent = "Processing...";

  try {
    const res = await fetch("/api/investigation/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ period: period, collect_live: liveCollect })
    });

    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Investigation failed.");

    statusArea.className = "p-3 rounded-lg text-xs bg-emerald-50 text-emerald-800 border border-emerald-200";
    statusArea.textContent = `Success! Investigation for ${period} executed and case study PDF updated.`;
    btnText.textContent = "Completed";

    setTimeout(() => {
      document.getElementById("runModal").classList.add("hidden");
      location.reload();
    }, 1500);
  } catch (err) {
    statusArea.className = "p-3 rounded-lg text-xs bg-rose-50 text-rose-800 border border-rose-200";
    statusArea.textContent = `Error: ${err.message}`;
    btnText.textContent = "Execute Investigation";
  }
}

async function openEditActionModal(actionId) {
  try {
    const res = await fetch("/api/actions");
    const data = await res.json();
    const act = (data.actions || []).find(a => a.action_id === actionId);
    if (!act) return;

    document.getElementById("editActionId").value = act.action_id;
    document.getElementById("editActionModalTitle").textContent = `Update Action: ${act.action_id}`;
    document.getElementById("editActionStatus").value = act.status;
    document.getElementById("editActionEvidence").value = act.verified_evidence || "";
    document.getElementById("editActionOutcome").value = act.outcome_label;
    document.getElementById("editActionDecision").value = act.next_decision || "";

    document.getElementById("actionModal").classList.remove("hidden");
  } catch (err) {
    console.error("Failed to open action modal:", err);
  }
}

async function saveActionChanges() {
  const actionId = document.getElementById("editActionId").value;
  const status = document.getElementById("editActionStatus").value;
  const evidence = document.getElementById("editActionEvidence").value;
  const outcome = document.getElementById("editActionOutcome").value;
  const decision = document.getElementById("editActionDecision").value;

  try {
    const res = await fetch(`/api/actions/${actionId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        status: status,
        verified_evidence: evidence,
        outcome_label: outcome,
        next_decision: decision
      })
    });
    if (!res.ok) throw new Error("Failed to update action");

    document.getElementById("actionModal").classList.add("hidden");
    await loadActionsData();
  } catch (err) {
    alert("Error updating action: " + err.message);
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return str.replace(/[&<>"']/g, m => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[m]);
}
