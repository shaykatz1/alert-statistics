let settlementsChart;
let shelterByHourChart;
let aircraftByHourChart;
let compareTwoLaunchTotalsChart;
let compareTwoShelterTotalsChart;
let compareTwoHourlyLaunchesChart;
let compareTwoHourlyShelterChart;

const $ = (id) => document.getElementById(id);

function selectedValues(selectEl) {
  return Array.from(selectEl.selectedOptions).map((o) => o.value).filter(Boolean);
}

function fillSelect(selectEl, values, placeholder) {
  selectEl.innerHTML = "";
  const first = document.createElement("option");
  first.value = "";
  first.textContent = placeholder;
  selectEl.appendChild(first);

  values.forEach((v) => {
    const option = document.createElement("option");
    option.value = v;
    option.textContent = v;
    selectEl.appendChild(option);
  });
}

function typeLabel(t) {
  if (t === "launch") return "שיגור";
  if (t === "shelter_enter") return "כניסה למרחב מוגן";
  if (t === "shelter_exit") return "יציאה ממרחב מוגן";
  if (t === "aircraft") return "חדירת כלי טיס";
  return t;
}

function toCsv(rows) {
  const headers = ["datetime", "alert_type", "title", "category", "settlements_count", "settlements"];
  const escape = (val) => `"${String(val ?? "").replaceAll('"', '""')}"`;
  const lines = [headers.join(",")];
  rows.forEach((row) => {
    lines.push(headers.map((h) => escape(h === "alert_type" ? typeLabel(row[h]) : row[h])).join(","));
  });
  return "\ufeff" + lines.join("\n");
}

function updateRangeVisibility() {
  const mode = $("rangeMode").value;
  $("customRange").style.display = mode === "custom" ? "grid" : "none";
}

function buildUrl() {
  const params = new URLSearchParams();
  const mode = $("rangeMode").value;
  params.set("mode", mode);

  const settlement = $("settlementSelect").value;
  if (settlement) {
    params.set("settlement", settlement);
    params.set("stats_settlement", settlement);
  }

  selectedValues($("typeSelect")).forEach((t) => params.append("alert_type", t));

  params.set("min_shelter_minutes", $("minShelterMinutes").value || "0");
  if ($("maxShelterMinutes").value) {
    params.set("max_shelter_minutes", $("maxShelterMinutes").value);
  }

  const compareA = $("compareSettlementA").value;
  const compareB = $("compareSettlementB").value;
  if (compareA) params.set("compare_a", compareA);
  if (compareB) params.set("compare_b", compareB);

  if (mode === "custom") {
    if ($("startDate").value) params.set("start_date", $("startDate").value);
    if ($("endDate").value) params.set("end_date", $("endDate").value);
    params.set("hour_from", $("hourFrom").value || "0");
    params.set("hour_to", $("hourTo").value || "23");
  }

  return `/api/alerts?${params.toString()}`;
}

function formatMinutesToHHMM(minutes) {
  const total = Math.max(0, Math.round(Number(minutes) || 0));
  const hh = Math.floor(total / 60);
  const mm = total % 60;
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
}

function renderFocusedSettlementStats(stats) {
  const total = stats?.total_shelter_minutes ?? 0;
  const avg = stats?.avg_stay_minutes ?? 0;
  const count = stats?.stay_count ?? 0;
  const longest = stats?.longest_stay_minutes ?? 0;
  const longestStart = stats?.longest_stay_start || "";
  const longestEnd = stats?.longest_stay_end || "";
  $("sTotalShelter").textContent = formatMinutesToHHMM(total);
  $("sAvgStay").textContent = formatMinutesToHHMM(avg);
  $("sStayCount").textContent = Number(count).toLocaleString("he-IL");
  $("sLongestStay").textContent = formatMinutesToHHMM(longest);
  $("sLongestStayWhen").textContent = longestStart && longestEnd ? `${longestStart} עד ${longestEnd}` : "-";
}

function renderCompareSettlementStats(targetId, stats) {
  const settlement = stats?.settlement || "לא נבחר יישוב";
  const total = formatMinutesToHHMM(stats?.total_shelter_minutes ?? 0);
  const avg = formatMinutesToHHMM(stats?.avg_stay_minutes ?? 0);
  const count = Number(stats?.stay_count ?? 0).toLocaleString("he-IL");
  const longest = formatMinutesToHHMM(stats?.longest_stay_minutes ?? 0);
  const start = stats?.longest_stay_start || "";
  const end = stats?.longest_stay_end || "";
  const when = start && end ? `${start} עד ${end}` : "-";

  $(targetId).innerHTML = `
    <div><strong>יישוב:</strong> ${settlement}</div>
    <div><strong>סה"כ זמן:</strong> ${total}</div>
    <div><strong>ממוצע לשהייה:</strong> ${avg}</div>
    <div><strong>מספר שהיות:</strong> ${count}</div>
    <div><strong>שהייה ארוכה:</strong> ${longest}</div>
    <div><strong>מתי:</strong> ${when}</div>
  `;
}

function renderTable(rows) {
  const body = $("rowsBody");
  body.innerHTML = "";
  rows.slice(0, 500).forEach((row) => {
    const tr = document.createElement("tr");
    [
      row.datetime,
      typeLabel(row.alert_type),
      row.title,
      row.category,
      row.settlements_count,
      row.settlements,
    ].forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

function drawBar(ctxId, labels, values, label, color) {
  return new Chart($(ctxId), {
    type: "bar",
    data: { labels, datasets: [{ label, data: values, backgroundColor: color }] },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
}

function drawHourlyTwoSettlements(ctxId, data, settlementA, settlementB, valueKey) {
  const labels = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`);
  const series = (settlement) => {
    const byHour = new Map();
    data.filter((r) => r.settlement === settlement).forEach((r) => byHour.set(r.hour, r[valueKey]));
    return Array.from({ length: 24 }, (_, h) => byHour.get(h) || 0);
  };

  return new Chart($(ctxId), {
    type: "bar",
    data: {
      labels,
      datasets: [
        {
          label: settlementA || "יישוב א'",
          data: series(settlementA),
          backgroundColor: "#0f8b4c",
        },
        {
          label: settlementB || "יישוב ב'",
          data: series(settlementB),
          backgroundColor: "#20639b",
        },
      ],
    },
    options: {
      responsive: true,
      plugins: { legend: { display: true, position: "bottom" } },
      scales: { y: { beginAtZero: true } },
    },
  });
}

function destroyCharts() {
  [
    settlementsChart,
    shelterByHourChart,
    aircraftByHourChart,
    compareTwoLaunchTotalsChart,
    compareTwoShelterTotalsChart,
    compareTwoHourlyLaunchesChart,
    compareTwoHourlyShelterChart,
  ].forEach((c) => c && c.destroy());
}

async function loadData(initial = false) {
  const response = await fetch(buildUrl());
  const data = await response.json();
  if (data.error) throw new Error(data.error);

  const { meta, groups, rows } = data;

  if (initial) {
    fillSelect($("settlementSelect"), meta.available_settlements, "כל היישובים");
    fillSelect($("compareSettlementA"), meta.available_settlements, "בחר יישוב א'");
    fillSelect($("compareSettlementB"), meta.available_settlements, "בחר יישוב ב'");
    if (meta.default_start_date) $("startDate").value = meta.default_start_date;
    if (meta.default_end_date) $("endDate").value = meta.default_end_date;
  }

  $("mLaunch").textContent = Number(meta.type_counts?.launch || 0).toLocaleString("he-IL");
  $("mEnter").textContent = Number(meta.type_counts?.shelter_enter || 0).toLocaleString("he-IL");
  $("mExit").textContent = Number(meta.type_counts?.shelter_exit || 0).toLocaleString("he-IL");
  $("mAircraft").textContent = Number(meta.type_counts?.aircraft || 0).toLocaleString("he-IL");
  renderFocusedSettlementStats(meta.selected_settlement_stats);

  const shelterNote = meta.has_shelter_history
    ? "קיימת היסטוריית כניסה/יציאה למרחב מוגן"
    : "לא זוהתה היסטוריית כניסה/יציאה למרחב מוגן בטווח";
  $("sourceText").textContent = `מקור: ${meta.source} | חלון זמן: ${meta.window_days} ימים | ${shelterNote}`;

  destroyCharts();
  settlementsChart = drawBar(
    "settlementsChart",
    groups.by_hour_launches.map((x) => `${String(x.hour).padStart(2, "0")}:00`),
    groups.by_hour_launches.map((x) => x.count),
    "שיגורים בלבד לפי שעה ביום",
    "#0f8b4c"
  );

  shelterByHourChart = drawBar(
    "shelterByHourChart",
    groups.by_hour_shelter_minutes.map((x) => `${String(x.hour).padStart(2, "0")}:00`),
    groups.by_hour_shelter_minutes.map((x) => x.minutes),
    "זמן שהיה במרחב מוגן לפי שעה ביום (דקות)",
    "#2c6e49"
  );

  aircraftByHourChart = drawBar(
    "threatsByHourChart",
    groups.by_hour_aircraft.map((x) => `${String(x.hour).padStart(2, "0")}:00`),
    groups.by_hour_aircraft.map((x) => x.count),
    "כלי טיס בלבד לפי שעה ביום",
    "#20639b"
  );

  const compareA = $("compareSettlementA").value;
  const compareB = $("compareSettlementB").value;
  compareTwoLaunchTotalsChart = drawBar(
    "compareTwoLaunchTotalsChart",
    (groups.compare_two_launch_totals || []).map((x) => x.settlement),
    (groups.compare_two_launch_totals || []).map((x) => x.count),
    "כמות שיגורים כוללת ב-2 היישובים",
    "#0f8b4c"
  );
  compareTwoShelterTotalsChart = drawBar(
    "compareTwoShelterTotalsChart",
    (groups.compare_two_shelter_totals || []).map((x) => x.settlement),
    (groups.compare_two_shelter_totals || []).map((x) => x.minutes),
    "זמן שהיה כולל (בדקות) ב-2 היישובים",
    "#20639b"
  );
  compareTwoHourlyLaunchesChart = drawHourlyTwoSettlements(
    "compareTwoHourlyLaunchesChart",
    groups.compare_two_hourly_launches || [],
    compareA,
    compareB,
    "count"
  );
  compareTwoHourlyShelterChart = drawHourlyTwoSettlements(
    "compareTwoHourlyShelterChart",
    groups.compare_two_hourly_shelter || [],
    compareA,
    compareB,
    "minutes"
  );
  renderCompareSettlementStats("compareStatsA", groups.compare_two_stats?.a);
  renderCompareSettlementStats("compareStatsB", groups.compare_two_stats?.b);

  renderTable(rows);

  const csv = toCsv(rows);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  $("csvLink").href = URL.createObjectURL(blob);
  $("csvLink").download = "oref_alerts_last_7_days_unique_events.csv";
}

$("rangeMode").addEventListener("change", updateRangeVisibility);
$("applyBtn").addEventListener("click", () => loadData(false));
$("compareBtn").addEventListener("click", () => loadData(false));
updateRangeVisibility();
loadData(true).catch((err) => {
  alert(`שגיאה: ${err.message}`);
});
