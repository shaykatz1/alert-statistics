let rawData = [];
let fullTopLaunches = [];
let fullBottomLaunches = [];
let fullTopShelter = [];
let fullBottomShelter = [];

const $ = (id) => document.getElementById(id);

function formatMinutesToHHMM(minutes) {
  const total = Math.max(0, Math.round(Number(minutes) || 0));
  const hh = Math.floor(total / 60);
  const mm = total % 60;
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
}

function classifyAlert(title, category) {
  const t = title || "";
  if (category === 13 || t.includes("ניתן לצאת") || t.includes("האירוע הסתיים") || t.includes("החשש הוסר")) return "shelter_exit";
  if (category === 14 || t.includes("בדקות הקרובות צפויות להתקבל התרעות") || t.includes("היכנסו") || t.includes("להיכנס")) return "shelter_enter";
  if (category === 1 || t.includes("ירי רקטות וטילים")) return "launch";
  if (category === 2 || t.includes("חדירת כלי טיס עוין") || t.includes("כלי טיס עוין")) return "aircraft";
  if (category === 10 || t.includes("חדירת מחבלים")) return "infiltration";
  return "other";
}

function calculateShelterPeriods(events) {
  const periods = [];
  let openAt = null;

  for (const evt of events) {
    if (evt.alert_type === "shelter_enter" && !openAt) {
      openAt = evt.alert_dt;
    } else if (evt.alert_type === "shelter_exit" && openAt) {
      const duration = (evt.alert_dt - openAt) / 1000 / 60;
      if (duration > 0) {
        periods.push({ start: openAt, end: evt.alert_dt, duration });
      }
      openAt = null;
    }
  }

  if (openAt) {
    const now = new Date();
    const duration = (now - openAt) / 1000 / 60;
    if (duration > 0) {
      periods.push({ start: openAt, end: now, duration });
    }
  }

  return periods;
}

function groupByValue(data, valueKey) {
  const groups = {};
  data.forEach(item => {
    const value = item[valueKey];
    if (!groups[value]) groups[value] = [];
    groups[value].push(item);
  });
  
  const result = Object.entries(groups).map(([value, items]) => ({
    value: parseFloat(value),
    settlements: items.map(i => i.settlement).sort(),
    items
  }));
  
  return result;
}

function renderTable(tbody, groupedData, columns) {
  tbody.innerHTML = "";
  
  let rank = 1;
  groupedData.forEach((group) => {
    const row = tbody.insertRow();
    row.insertCell(0).textContent = rank;
    
    const settlementCell = row.insertCell(1);
    const count = group.settlements.length;
    
    if (count === 1) {
      // יישוב אחד - טקסט רגיל
      settlementCell.textContent = group.settlements[0];
    } else if (count <= 4) {
      // 2-4 ישובים - רשימה אנכית
      settlementCell.innerHTML = group.settlements.join('<br>');
      settlementCell.style.fontSize = '13px';
      settlementCell.style.lineHeight = '1.5';
    } else if (count <= 9) {
      // 5-9 ישובים - 2 עמודות
      settlementCell.innerHTML = `<div style="column-count: 2; column-gap: 12px; font-size: 13px; line-height: 1.5;">${group.settlements.join('<br>')}</div>`;
    } else {
      // 10+ ישובים - 3 עמודות
      settlementCell.innerHTML = `<div style="column-count: 3; column-gap: 10px; font-size: 12px; line-height: 1.4;">${group.settlements.join('<br>')}</div>`;
    }
    
    columns.forEach(col => {
      const cell = row.insertCell();
      const avgItem = group.items[0];
      cell.textContent = col.format(avgItem);
    });
    
    rank++;
  });
}

function renderTopLaunches(data, limit = 10) {
  const sorted = data.sort((a, b) => b.launches - a.launches);
  fullTopLaunches = groupByValue(sorted, 'launches').sort((a, b) => b.value - a.value);
  
  const toShow = fullTopLaunches.slice(0, limit);
  const tbody = $("topLaunchesTable");
  
  renderTable(tbody, toShow, [
    { format: (item) => item.launches.toLocaleString() },
    { format: (item) => formatMinutesToHHMM(item.shelterMinutes) },
    { format: (item) => item.avgStayMinutes > 0 ? item.avgStayMinutes.toFixed(1) + " דק'" : "-" }
  ]);
  
  const expandBtn = $("topLaunchesExpand");
  if (expandBtn) {
    expandBtn.style.display = fullTopLaunches.length > limit ? "block" : "none";
  }
}

function renderBottomLaunches(data, limit = 10) {
  const withLaunches = data.filter(d => d.launches > 0);
  const sorted = withLaunches.sort((a, b) => a.launches - b.launches);
  fullBottomLaunches = groupByValue(sorted, 'launches').sort((a, b) => a.value - b.value);
  
  const toShow = fullBottomLaunches.slice(0, limit);
  const tbody = $("bottomLaunchesTable");
  
  renderTable(tbody, toShow, [
    { format: (item) => item.launches.toLocaleString() },
    { format: (item) => formatMinutesToHHMM(item.shelterMinutes) },
    { format: (item) => item.avgStayMinutes > 0 ? item.avgStayMinutes.toFixed(1) + " דק'" : "-" }
  ]);
  
  const expandBtn = $("bottomLaunchesExpand");
  if (expandBtn) {
    expandBtn.style.display = fullBottomLaunches.length > limit ? "block" : "none";
  }
}

function renderTopShelter(data, limit = 10) {
  const withShelter = data.filter(d => d.shelterMinutes > 0);
  const sorted = withShelter.sort((a, b) => b.shelterMinutes - a.shelterMinutes);
  fullTopShelter = groupByValue(sorted, 'shelterMinutes').sort((a, b) => b.value - a.value);
  
  const toShow = fullTopShelter.slice(0, limit);
  const tbody = $("topShelterTable");
  
  renderTable(tbody, toShow, [
    { format: (item) => formatMinutesToHHMM(item.shelterMinutes) },
    { format: (item) => item.launches.toLocaleString() },
    { format: (item) => item.stayCount.toLocaleString() },
    { format: (item) => item.avgStayMinutes > 0 ? item.avgStayMinutes.toFixed(1) + " דק'" : "-" }
  ]);
  
  const expandBtn = $("topShelterExpand");
  if (expandBtn) {
    expandBtn.style.display = fullTopShelter.length > limit ? "block" : "none";
  }
}

function renderBottomShelter(data, limit = 10) {
  const withShelter = data.filter(d => d.shelterMinutes > 0);
  const sorted = withShelter.sort((a, b) => a.shelterMinutes - b.shelterMinutes);
  fullBottomShelter = groupByValue(sorted, 'shelterMinutes').sort((a, b) => a.value - b.value);
  
  const toShow = fullBottomShelter.slice(0, limit);
  const tbody = $("bottomShelterTable");
  
  renderTable(tbody, toShow, [
    { format: (item) => formatMinutesToHHMM(item.shelterMinutes) },
    { format: (item) => item.launches.toLocaleString() },
    { format: (item) => item.stayCount.toLocaleString() },
    { format: (item) => item.avgStayMinutes > 0 ? item.avgStayMinutes.toFixed(1) + " דק'" : "-" }
  ]);
  
  const expandBtn = $("bottomShelterExpand");
  if (expandBtn) {
    expandBtn.style.display = fullBottomShelter.length > limit ? "block" : "none";
  }
}

function expandTopLaunches() {
  renderTopLaunches(processData(filterData()), Infinity);
  $("topLaunchesExpand").style.display = "none";
}

function expandBottomLaunches() {
  renderBottomLaunches(processData(filterData()), Infinity);
  $("bottomLaunchesExpand").style.display = "none";
}

function expandTopShelter() {
  renderTopShelter(processData(filterData()), Infinity);
  $("topShelterExpand").style.display = "none";
}

function expandBottomShelter() {
  renderBottomShelter(processData(filterData()), Infinity);
  $("bottomShelterExpand").style.display = "none";
}

function processData(filtered) {
  const settlementStats = {};

  filtered.forEach(row => {
    if (!settlementStats[row.settlement]) {
      settlementStats[row.settlement] = {
        settlement: row.settlement,
        launches: 0,
        events: []
      };
    }

    const stats = settlementStats[row.settlement];
    stats.events.push(row);

    if (row.alert_type === "launch") {
      stats.launches++;
    }
  });

  const results = [];
  for (const [settlement, stats] of Object.entries(settlementStats)) {
    stats.events.sort((a, b) => a.alert_dt - b.alert_dt);
    
    const periods = calculateShelterPeriods(stats.events);
    const totalShelterMinutes = periods.reduce((sum, p) => sum + p.duration, 0);
    const avgStayMinutes = periods.length > 0 ? totalShelterMinutes / periods.length : 0;

    results.push({
      settlement,
      launches: stats.launches,
      shelterMinutes: totalShelterMinutes,
      stayCount: periods.length,
      avgStayMinutes,
      longestStay: periods.length > 0 ? Math.max(...periods.map(p => p.duration)) : 0
    });
  }

  return results;
}

function filterData() {
  const mode = $("rangeMode").value;
  const now = new Date();
  let filtered = [...rawData];

  if (mode === "week") {
    const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    filtered = filtered.filter(r => r.alert_dt >= weekAgo);
  } else if (mode.startsWith("last_")) {
    const days = parseInt(mode.split("_")[1].replace("d", ""));
    const daysAgo = new Date(now.getTime() - days * 24 * 60 * 60 * 1000);
    filtered = filtered.filter(r => r.alert_dt >= daysAgo);
  } else if (mode === "custom") {
    const startDate = $("startDate").value;
    const endDate = $("endDate").value;
    const hourFrom = parseInt($("hourFrom").value || "0");
    const hourTo = parseInt($("hourTo").value || "23");

    if (startDate) {
      const start = new Date(startDate + "T00:00:00");
      filtered = filtered.filter(r => r.alert_dt >= start);
    }
    if (endDate) {
      const end = new Date(endDate + "T23:59:59");
      filtered = filtered.filter(r => r.alert_dt <= end);
    }
    filtered = filtered.filter(r => {
      const hour = r.alert_dt.getHours();
      return hour >= hourFrom && hour <= hourTo;
    });
  }

  return filtered;
}

function renderGeneralStats(data) {
  const launches = data.map(d => d.launches);
  const totalSettlements = data.length;
  const totalLaunches = launches.reduce((sum, v) => sum + v, 0);
  const avgLaunches = totalSettlements > 0 ? totalLaunches / totalSettlements : 0;
  
  const sortedLaunches = [...launches].sort((a, b) => a - b);
  const median = sortedLaunches[Math.floor(sortedLaunches.length / 2)] || 0;

  $("totalSettlements").textContent = totalSettlements.toLocaleString();
  $("avgLaunches").textContent = avgLaunches.toFixed(1);
  $("medianLaunches").textContent = median.toFixed(0);
}

function updateRangeVisibility() {
  const mode = $("rangeMode").value;
  $("customRange").style.display = mode === "custom" ? "grid" : "none";
}

function loadAndRender() {
  const filtered = filterData();
  const stats = processData(filtered);

  renderTopLaunches(stats);
  renderBottomLaunches(stats);
  renderTopShelter(stats);
  renderBottomShelter(stats);
  renderGeneralStats(stats);
}

async function loadData() {
  const loadingEl = $("loadingIndicator");
  const errorEl = $("errorIndicator");
  const mainContentEl = $("mainContent");
  
  try {
    if (loadingEl) loadingEl.style.display = "block";
    if (errorEl) errorEl.style.display = "none";
    if (mainContentEl) mainContentEl.style.display = "none";
    
    console.log("Fetching alerts_history.json...");
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 60000);
    
    const response = await fetch("./data/alerts_history.json", { signal: controller.signal });
    clearTimeout(timeoutId);
    
    if (!response.ok) throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    
    console.log("Parsing JSON...");
    const rows = await response.json();
    console.log(`✓ Loaded ${rows.length} records`);
    
    rawData = rows.map(row => ({
      ...row,
      alert_dt: new Date(row.alertDate),
      alert_type: classifyAlert(row.title, row.category),
      settlement: row.data
    })).filter(row => ["launch", "shelter_enter", "shelter_exit", "aircraft", "infiltration"].includes(row.alert_type));

    console.log(`✓ Filtered to ${rawData.length} relevant alerts`);
    
    if (loadingEl) loadingEl.style.display = "none";
    if (mainContentEl) mainContentEl.style.display = "block";
    
    loadAndRender();
  } catch (err) {
    console.error("Failed to load data:", err);
    if (loadingEl) loadingEl.style.display = "none";
    if (errorEl) {
      errorEl.style.display = "block";
      const msgEl = $("errorMessage");
      if (msgEl) {
        if (err.name === 'AbortError') {
          msgEl.textContent = "הטעינה ארכה יותר מ-60 שניות.";
        } else {
          msgEl.textContent = err.message;
        }
      }
    }
  }
}

$("rangeMode").addEventListener("change", () => {
  updateRangeVisibility();
  if (rawData.length > 0) loadAndRender();
});

$("applyBtn").addEventListener("click", () => {
  if (rawData.length > 0) loadAndRender();
});

updateRangeVisibility();
loadData();
