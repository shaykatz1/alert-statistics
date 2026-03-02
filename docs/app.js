let rawRows = [];

let launchByHourChart;
let shelterByHourChart;
let aircraftByHourChart;
let compareTwoLaunchTotalsChart;
let compareTwoShelterTotalsChart;
let compareTwoHourlyLaunchesChart;
let compareTwoHourlyShelterChart;

const $ = (id) => document.getElementById(id);

function typeLabel(t) {
  if (t === "launch") return "שיגור";
  if (t === "shelter_enter") return "כניסה למרחב מוגן";
  if (t === "shelter_exit") return "יציאה ממרחב מוגן";
  if (t === "aircraft") return "חדירת כלי טיס";
  if (t === "infiltration") return "חדירת מחבלים";
  return t;
}

function classifyAlert(title, category) {
  const t = title || "";
  // Check for event end FIRST (before checking event type)
  if (category === 13 || t.includes("ניתן לצאת") || t.includes("האירוע הסתיים") || t.includes("החשש הוסר")) return "shelter_exit";
  if (category === 14 || t.includes("בדקות הקרובות צפויות להתקבל התרעות") || t.includes("היכנסו") || t.includes("להיכנס")) return "shelter_enter";
  if (category === 1 || t.includes("ירי רקטות וטילים")) return "launch";
  if (category === 2 || t.includes("חדירת כלי טיס עוין") || t.includes("כלי טיס עוין")) return "aircraft";
  if (category === 10 || t.includes("חדירת מחבלים")) return "infiltration";
  return "other";
}

function toCsv(rows) {
  const headers = ["datetime", "alert_type", "title", "category", "settlements_count", "settlements"];
  const escape = (val) => `"${String(val ?? "").replaceAll('"', '""')}"`;
  const lines = [headers.join(",")];
  rows.forEach((row) => lines.push(headers.map((h) => escape(h === "alert_type" ? typeLabel(row[h]) : row[h])).join(",")));
  return "\ufeff" + lines.join("\n");
}

function fillSelect(selectEl, values, placeholder) {
  const first = document.createElement("option");
  first.value = "";
  first.textContent = placeholder;
  selectEl.appendChild(first);
  values.forEach((v) => {
    const opt = document.createElement("option");
    opt.value = v;
    opt.textContent = v;
    selectEl.appendChild(opt);
  });
}

function setupAutocomplete(inputEl, values) {
  const dropdownId = inputEl.id + "-dropdown";
  const dropdown = $(dropdownId);
  if (!dropdown) {
    console.error("Dropdown not found for", inputEl.id);
    return;
  }

  let allValues = [...values].sort();
  let selectedIndex = -1;

  // Store the selected value
  inputEl.dataset.selectedValue = "";

  function highlightMatch(text, query) {
    if (!query) return text;
    const index = text.toLowerCase().indexOf(query.toLowerCase());
    if (index === -1) return text;
    return text.substring(0, index) +
           '<strong>' + text.substring(index, index + query.length) + '</strong>' +
           text.substring(index + query.length);
  }

  function filterAndShow() {
    const query = inputEl.value.trim();
    const queryLower = query.toLowerCase();
    
    // Filter: prioritize starts-with, then includes
    let filtered;
    if (query) {
      const startsWith = allValues.filter((v) => v.toLowerCase().startsWith(queryLower));
      const contains = allValues.filter((v) => !v.toLowerCase().startsWith(queryLower) && v.toLowerCase().includes(queryLower));
      filtered = [...startsWith, ...contains];
    } else {
      filtered = allValues.slice(0, 100); // Show first 100 when empty
    }

    dropdown.innerHTML = "";
    
    if (filtered.length === 0) {
      dropdown.innerHTML = '<div class="autocomplete-empty">לא נמצאו תוצאות</div>';
      dropdown.classList.add("show");
      return;
    }

    const itemsToShow = filtered.slice(0, 100); // Limit display for performance
    itemsToShow.forEach((val, idx) => {
      const item = document.createElement("div");
      item.className = "autocomplete-item";
      item.innerHTML = highlightMatch(val, query);
      item.dataset.value = val;
      if (idx === selectedIndex) item.classList.add("highlighted");
      
      item.addEventListener("mousedown", (e) => {
        e.preventDefault();
        selectItem(val);
      });
      
      dropdown.appendChild(item);
    });

    if (filtered.length > 100) {
      const more = document.createElement("div");
      more.className = "autocomplete-empty";
      more.textContent = `+ ${filtered.length - 100} תוצאות נוספות - המשך להקליד`;
      dropdown.appendChild(more);
    }

    dropdown.classList.add("show");
    selectedIndex = -1;
  }

  function selectItem(value) {
    inputEl.value = value;
    inputEl.dataset.selectedValue = value;
    dropdown.classList.remove("show");
    selectedIndex = -1;
  }

  function hideDropdown() {
    setTimeout(() => {
      dropdown.classList.remove("show");
      selectedIndex = -1;
    }, 150);
  }

  inputEl.addEventListener("input", () => {
    inputEl.dataset.selectedValue = "";
    filterAndShow();
  });

  inputEl.addEventListener("focus", () => {
    filterAndShow();
  });

  inputEl.addEventListener("blur", hideDropdown);

  inputEl.addEventListener("keydown", (e) => {
    const items = dropdown.querySelectorAll(".autocomplete-item");
    
    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (items.length > 0) {
        selectedIndex = Math.min(selectedIndex + 1, items.length - 1);
        items.forEach((item, idx) => {
          item.classList.toggle("highlighted", idx === selectedIndex);
        });
        items[selectedIndex]?.scrollIntoView({ block: "nearest" });
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (items.length > 0) {
        selectedIndex = Math.max(selectedIndex - 1, 0);
        items.forEach((item, idx) => {
          item.classList.toggle("highlighted", idx === selectedIndex);
        });
        items[selectedIndex]?.scrollIntoView({ block: "nearest" });
      }
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (selectedIndex >= 0 && items[selectedIndex]) {
        selectItem(items[selectedIndex].dataset.value);
      } else if (items.length === 1) {
        selectItem(items[0].dataset.value);
      }
    } else if (e.key === "Escape") {
      dropdown.classList.remove("show");
      selectedIndex = -1;
    }
  });

  // Helper to get the selected value
  inputEl.getSelectedValue = function() {
    return this.dataset.selectedValue || "";
  };

  // Helper to set values
  inputEl.setValues = function(newValues) {
    allValues = [...newValues].sort();
  };
}

function selectedValues(selectEl) {
  return Array.from(selectEl.selectedOptions).map((o) => o.value).filter(Boolean);
}

function formatMinutesToHHMM(minutes) {
  const total = Math.max(0, Math.round(Number(minutes) || 0));
  const hh = Math.floor(total / 60);
  const mm = total % 60;
  return `${String(hh).padStart(2, "0")}:${String(mm).padStart(2, "0")}`;
}

function updateRangeVisibility() {
  $("customRange").style.display = $("rangeMode").value === "custom" ? "grid" : "none";
}

function prepareRows(rows) {
  const now = new Date();
  const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);

  return rows
    .map((r) => {
      const dt = new Date((r.alertDate || "").replace(" ", "T"));
      const category = Number(r.category || 0);
      const alert_type = classifyAlert(r.title || "", category);
      return {
        settlement: String(r.data || "").trim(),
        title: String(r.title || ""),
        category,
        alert_dt: dt,
        alert_type,
      };
    })
    .filter((r) => !Number.isNaN(r.alert_dt.getTime()))
    .filter((r) => r.alert_dt >= weekAgo && r.alert_dt <= now)
    .filter((r) => ["launch", "shelter_enter", "shelter_exit", "aircraft", "infiltration"].includes(r.alert_type))
    .map((r) => {
      const yyyy = r.alert_dt.getFullYear();
      const mm = String(r.alert_dt.getMonth() + 1).padStart(2, "0");
      const dd = String(r.alert_dt.getDate()).padStart(2, "0");
      const HH = String(r.alert_dt.getHours()).padStart(2, "0");
      const MM = String(r.alert_dt.getMinutes()).padStart(2, "0");
      const SS = String(r.alert_dt.getSeconds()).padStart(2, "0");
      const date = `${yyyy}-${mm}-${dd}`;
      const datetime = `${date} ${HH}:${MM}:${SS}`;
      return {
        ...r,
        hour: r.alert_dt.getHours(),
        date,
        datetime,
        event_key: `${datetime}|${r.title}|${r.category}`,
      };
    });
}

function applyRangeFilter(rows) {
  const mode = $("rangeMode").value;
  const now = new Date();
  if (mode === "week") return { rows, rangeStart: null, rangeEnd: null };

  const mapDays = { last_1d: 1, last_2d: 2, last_3d: 3, last_4d: 4 };
  if (mapDays[mode]) {
    const rangeStart = new Date(now.getTime() - mapDays[mode] * 24 * 60 * 60 * 1000);
    return {
      rows: rows.filter((r) => r.alert_dt >= rangeStart && r.alert_dt <= now),
      rangeStart,
      rangeEnd: now,
    };
  }

  if (mode === "custom") {
    const startDate = $("startDate").value;
    const endDate = $("endDate").value;
    const hourFrom = Math.max(0, Math.min(23, Number($("hourFrom").value || 0)));
    const hourTo = Math.max(0, Math.min(23, Number($("hourTo").value || 23)));

    let out = rows.filter((r) => r.hour >= hourFrom && r.hour <= hourTo);
    let rangeStart = null;
    let rangeEnd = null;

    if (startDate && endDate) {
      let s = new Date(`${startDate}T00:00:00`);
      let e = new Date(`${endDate}T23:59:59`);
      if (e < s) [s, e] = [e, s];
      out = out.filter((r) => r.alert_dt >= s && r.alert_dt <= e);
      rangeStart = new Date(`${s.toISOString().slice(0, 10)}T${String(hourFrom).padStart(2, "0")}:00:00`);
      rangeEnd = new Date(`${e.toISOString().slice(0, 10)}T${String(hourTo).padStart(2, "0")}:59:59`);
    }

    return { rows: out, rangeStart, rangeEnd };
  }

  return { rows, rangeStart: null, rangeEnd: null };
}

function extractShelterStays(rows, rangeStart, rangeEnd) {
  const now = new Date();
  const effectiveEnd = rangeEnd || now;
  const data = rows
    .filter((r) => r.alert_type === "shelter_enter" || r.alert_type === "shelter_exit")
    .sort((a, b) => a.alert_dt - b.alert_dt);

  const bySettlement = new Map();
  data.forEach((r) => {
    if (!bySettlement.has(r.settlement)) bySettlement.set(r.settlement, []);
    bySettlement.get(r.settlement).push(r);
  });

  const stays = [];
  for (const [settlement, arr] of bySettlement.entries()) {
    let openAt = null;
    for (const row of arr) {
      if (row.alert_type === "shelter_enter") {
        if (!openAt) openAt = row.alert_dt;
        continue;
      }
      if (row.alert_type === "shelter_exit" && openAt) {
        let start = openAt;
        let end = row.alert_dt;
        if (rangeStart) start = start > rangeStart ? start : rangeStart;
        if (rangeEnd) end = end < rangeEnd ? end : rangeEnd;
        if (end > start) stays.push({ settlement, start_dt: start, end_dt: end, duration_minutes: (end - start) / 60000 });
        openAt = null;
      }
    }

    if (openAt) {
      let start = openAt;
      let end = effectiveEnd;
      if (rangeStart) start = start > rangeStart ? start : rangeStart;
      if (rangeEnd) end = end < rangeEnd ? end : rangeEnd;
      if (end > start) stays.push({ settlement, start_dt: start, end_dt: end, duration_minutes: (end - start) / 60000 });
    }
  }

  return stays;
}

function summarizeShelter(stays) {
  const map = new Map();
  stays.forEach((s) => {
    if (!map.has(s.settlement)) map.set(s.settlement, { settlement: s.settlement, shelter_minutes: 0, stay_count: 0 });
    const cur = map.get(s.settlement);
    cur.shelter_minutes += s.duration_minutes;
    cur.stay_count += 1;
  });

  return Array.from(map.values()).map((x) => ({
    settlement: x.settlement,
    shelter_minutes: Math.round(x.shelter_minutes),
    shelter_hours: Math.round((x.shelter_minutes / 60) * 100) / 100,
    stay_count: x.stay_count,
    avg_stay_minutes: x.stay_count ? Math.round((x.shelter_minutes / x.stay_count) * 10) / 10 : 0,
  }));
}

function countSheltersWithoutThreats(rows, settlement) {
  // Count first shelter_enter of each stay that were not followed by launch/aircraft within 30 minutes
  // Uses same logic as extractShelterStays - only counts first entry until exit
  const allEvents = rows.filter((r) => r.settlement === settlement && 
    (r.alert_type === "shelter_enter" || r.alert_type === "shelter_exit" || 
     r.alert_type === "launch" || r.alert_type === "aircraft"))
    .sort((a, b) => a.alert_dt - b.alert_dt);
  
  if (allEvents.length === 0) {
    return { shelters_without_threats: 0, total_shelter_entries: 0 };
  }
  
  let openAt = null;
  let totalEntries = 0;
  let withoutThreats = 0;
  
  for (const event of allEvents) {
    const typ = event.alert_type;
    const at = event.alert_dt;
    
    // First shelter_enter of a stay
    if (typ === "shelter_enter" && openAt === null) {
      openAt = at;
      totalEntries++;
      
      // Check if there's a threat before (10 min) or after (30 min) this entry
      // Before: the launch/aircraft that caused the shelter alert
      // After: threats during the shelter stay
      const threatsRelated = allEvents.filter((e) => 
        (e.alert_type === "launch" || e.alert_type === "aircraft") &&
        e.alert_dt >= at - (10 * 60 * 1000) && // 10 minutes before
        e.alert_dt <= at + (30 * 60 * 1000) // 30 minutes after
      );
      
      if (threatsRelated.length === 0) {
        withoutThreats++;
      }
    }
    // Subsequent shelter_enter while already in shelter - ignore
    else if (typ === "shelter_enter" && openAt !== null) {
      continue;
    }
    // Exit from shelter
    else if (typ === "shelter_exit" && openAt !== null) {
      openAt = null;
    }
  }
  
  return { shelters_without_threats: withoutThreats, total_shelter_entries: totalEntries };
}

function getSettlementStats(summary, stays, settlement, allRows) {
  if (!settlement) return { 
    settlement: null, 
    total_shelter_minutes: 0, 
    avg_stay_minutes: 0, 
    stay_count: 0, 
    longest_stay_minutes: 0, 
    longest_stay_start: null, 
    longest_stay_end: null,
    shelters_without_threats: 0,
    total_shelter_entries: 0
  };
  
  const row = summary.find((x) => x.settlement === settlement);
  const subset = stays.filter((s) => s.settlement === settlement).sort((a, b) => b.duration_minutes - a.duration_minutes);
  
  if (!row) return { 
    settlement, 
    total_shelter_minutes: 0, 
    avg_stay_minutes: 0, 
    stay_count: 0, 
    longest_stay_minutes: 0, 
    longest_stay_start: null, 
    longest_stay_end: null,
    shelters_without_threats: 0,
    total_shelter_entries: 0
  };
  
  const longest = subset[0];
  const toDt = (d) => {
    const yyyy = d.getFullYear();
    const mm = String(d.getMonth() + 1).padStart(2, "0");
    const dd = String(d.getDate()).padStart(2, "0");
    const HH = String(d.getHours()).padStart(2, "0");
    const MM = String(d.getMinutes()).padStart(2, "0");
    const SS = String(d.getSeconds()).padStart(2, "0");
    return `${yyyy}-${mm}-${dd} ${HH}:${MM}:${SS}`;
  };

  // Calculate shelters without threats
  const withoutThreatsData = countSheltersWithoutThreats(allRows, settlement);

  return {
    settlement,
    total_shelter_minutes: row.shelter_minutes,
    avg_stay_minutes: row.avg_stay_minutes,
    stay_count: row.stay_count,
    longest_stay_minutes: longest ? Math.round(longest.duration_minutes) : 0,
    longest_stay_start: longest ? toDt(longest.start_dt) : null,
    longest_stay_end: longest ? toDt(longest.end_dt) : null,
    shelters_without_threats: withoutThreatsData.shelters_without_threats,
    total_shelter_entries: withoutThreatsData.total_shelter_entries,
  };
}

function uniqueEvents(rows) {
  const map = new Map();
  rows.forEach((r) => {
    if (!map.has(r.event_key)) {
      map.set(r.event_key, {
        event_key: r.event_key,
        datetime: r.datetime,
        title: r.title,
        category: r.category,
        alert_type: r.alert_type,
        hour: r.hour,
        settlements: new Set([r.settlement]),
      });
    } else {
      map.get(r.event_key).settlements.add(r.settlement);
    }
  });

  return Array.from(map.values()).map((x) => ({
    datetime: x.datetime,
    title: x.title,
    category: x.category,
    alert_type: x.alert_type,
    hour: x.hour,
    settlements_count: x.settlements.size,
    settlements: Array.from(x.settlements).sort().slice(0, 15).join(", "),
  }));
}

function hourlyCountsFromEvents(events) {
  const counts = new Array(24).fill(0);
  events.forEach((e) => { counts[e.hour] += 1; });
  return counts.map((count, hour) => ({ hour, count }));
}

function hourlyShelterMinutes(stays) {
  const buckets = new Array(24).fill(0);
  stays.forEach((s) => {
    let current = new Date(s.start_dt);
    const end = s.end_dt;
    while (current < end) {
      const nextHour = new Date(current);
      nextHour.setMinutes(0, 0, 0);
      nextHour.setHours(nextHour.getHours() + 1);
      const segmentEnd = end < nextHour ? end : nextHour;
      buckets[current.getHours()] += (segmentEnd - current) / 60000;
      current = segmentEnd;
    }
  });
  return buckets.map((minutes, hour) => ({ hour, minutes: Math.round(minutes) }));
}

function compareHourlyTwo(rows, stays, a, b) {
  const emptyHours = () => Array.from({ length: 24 }, (_, h) => h);
  const launchesA = new Array(24).fill(0);
  const launchesB = new Array(24).fill(0);
  const shelterA = new Array(24).fill(0);
  const shelterB = new Array(24).fill(0);

  const launchSeen = new Set();
  rows.filter((r) => r.alert_type === "launch" && (r.settlement === a || r.settlement === b)).forEach((r) => {
    const k = `${r.settlement}|${r.event_key}`;
    if (launchSeen.has(k)) return;
    launchSeen.add(k);
    if (r.settlement === a) launchesA[r.hour] += 1;
    if (r.settlement === b) launchesB[r.hour] += 1;
  });

  stays.filter((s) => s.settlement === a || s.settlement === b).forEach((s) => {
    let current = new Date(s.start_dt);
    const end = s.end_dt;
    while (current < end) {
      const nextHour = new Date(current);
      nextHour.setMinutes(0, 0, 0);
      nextHour.setHours(nextHour.getHours() + 1);
      const segmentEnd = end < nextHour ? end : nextHour;
      const mins = (segmentEnd - current) / 60000;
      if (s.settlement === a) shelterA[current.getHours()] += mins;
      if (s.settlement === b) shelterB[current.getHours()] += mins;
      current = segmentEnd;
    }
  });

  const launches = [
    ...emptyHours().map((hour) => ({ settlement: a, hour, count: launchesA[hour] })),
    ...emptyHours().map((hour) => ({ settlement: b, hour, count: launchesB[hour] })),
  ];
  const shelter = [
    ...emptyHours().map((hour) => ({ settlement: a, hour, minutes: Math.round(shelterA[hour]) })),
    ...emptyHours().map((hour) => ({ settlement: b, hour, minutes: Math.round(shelterB[hour]) })),
  ];

  return { launches, shelter };
}

function renderTable(rows) {
  const body = $("rowsBody");
  body.innerHTML = "";
  rows.slice(0, 500).forEach((row) => {
    const tr = document.createElement("tr");
    [row.datetime, typeLabel(row.alert_type), row.title, row.category, row.settlements_count, row.settlements].forEach((value) => {
      const td = document.createElement("td");
      td.textContent = value;
      tr.appendChild(td);
    });
    body.appendChild(tr);
  });
}

function renderFocusedSettlementStats(stats) {
  $("sTotalShelter").textContent = formatMinutesToHHMM(stats.total_shelter_minutes || 0);
  $("sAvgStay").textContent = formatMinutesToHHMM(stats.avg_stay_minutes || 0);
  $("sStayCount").textContent = Number(stats.stay_count || 0).toLocaleString("he-IL");
  $("sLongestStay").textContent = formatMinutesToHHMM(stats.longest_stay_minutes || 0);
  $("sLongestStayWhen").textContent = stats.longest_stay_start && stats.longest_stay_end ? `${stats.longest_stay_start} עד ${stats.longest_stay_end}` : "-";
  
  // Display shelter entries without threats
  const withoutThreats = stats.shelters_without_threats || 0;
  const totalEntries = stats.total_shelter_entries || 0;
  const percentage = totalEntries > 0 ? Math.round((withoutThreats / totalEntries) * 100) : 0;
  $("sSheltersWithoutThreats").textContent = totalEntries > 0 ? `${withoutThreats} מתוך ${totalEntries} (${percentage}%)` : "-";
}

function renderCompareSettlementStats(targetId, stats) {
  const settlement = stats?.settlement || "לא נבחר יישוב";
  const withoutThreats = stats?.shelters_without_threats || 0;
  const totalEntries = stats?.total_shelter_entries || 0;
  const percentage = totalEntries > 0 ? Math.round((withoutThreats / totalEntries) * 100) : 0;
  const withoutThreatsText = totalEntries > 0 ? `${withoutThreats} מתוך ${totalEntries} (${percentage}%)` : "-";
  
  $(targetId).innerHTML = `
    <div><strong>יישוב:</strong> ${settlement}</div>
    <div><strong>סה"כ זמן:</strong> ${formatMinutesToHHMM(stats?.total_shelter_minutes || 0)}</div>
    <div><strong>ממוצע לשהייה:</strong> ${formatMinutesToHHMM(stats?.avg_stay_minutes || 0)}</div>
    <div><strong>מספר שהיות:</strong> ${Number(stats?.stay_count || 0).toLocaleString("he-IL")}</div>
    <div><strong>כניסות ללא שיגור:</strong> ${withoutThreatsText}</div>
    <div><strong>שהייה ארוכה:</strong> ${formatMinutesToHHMM(stats?.longest_stay_minutes || 0)}</div>
    <div><strong>מתי:</strong> ${stats?.longest_stay_start && stats?.longest_stay_end ? `${stats.longest_stay_start} עד ${stats.longest_stay_end}` : "-"}</div>
  `;
}

function drawBar(id, labels, values, label, color) {
  return new Chart($(id), {
    type: "bar",
    data: { labels, datasets: [{ label, data: values, backgroundColor: color }] },
    options: { responsive: true, plugins: { legend: { display: false } } },
  });
}

function drawHourlyTwoSettlements(id, data, a, b, valueKey) {
  const labels = Array.from({ length: 24 }, (_, h) => `${String(h).padStart(2, "0")}:00`);
  const build = (settlement) => {
    const arr = new Array(24).fill(0);
    data.filter((x) => x.settlement === settlement).forEach((x) => { arr[x.hour] = x[valueKey] || 0; });
    return arr;
  };

  return new Chart($(id), {
    type: "bar",
    data: {
      labels,
      datasets: [
        { label: a || "יישוב א'", data: build(a), backgroundColor: "#0f8b4c" },
        { label: b || "יישוב ב'", data: build(b), backgroundColor: "#20639b" },
      ],
    },
    options: { responsive: true, plugins: { legend: { display: true, position: "bottom" } }, scales: { y: { beginAtZero: true } } },
  });
}

function destroyCharts() {
  [
    launchByHourChart,
    shelterByHourChart,
    aircraftByHourChart,
    compareTwoLaunchTotalsChart,
    compareTwoShelterTotalsChart,
    compareTwoHourlyLaunchesChart,
    compareTwoHourlyShelterChart,
  ].forEach((c) => c && c.destroy());
}

function runDashboard() {
  const prepared = prepareRows(rawRows);
  const availableSettlements = Array.from(new Set(prepared.map((r) => r.settlement))).filter(Boolean).sort();

  if (!$("settlementSelect").dataset.filled) {
    setupAutocomplete($("settlementSelect"), availableSettlements);
    setupAutocomplete($("compareSettlementA"), availableSettlements);
    setupAutocomplete($("compareSettlementB"), availableSettlements);
    const dates = Array.from(new Set(prepared.map((r) => r.date))).sort();
    if (dates.length) {
      $("startDate").value = dates[0];
      $("endDate").value = dates[dates.length - 1];
    }
    $("settlementSelect").dataset.filled = "1";
  }

  const { rows: baseFiltered, rangeStart, rangeEnd } = applyRangeFilter(prepared);
  const stays = extractShelterStays(baseFiltered, rangeStart, rangeEnd);
  const shelterSummary = summarizeShelter(stays);

  const minShelter = Math.max(0, Number($("minShelterMinutes").value || 0));
  const maxShelter = Number($("maxShelterMinutes").value || -1);
  let allowedSettlements = new Set(shelterSummary.filter((s) => s.shelter_minutes >= minShelter && (maxShelter < 0 || s.shelter_minutes <= maxShelter)).map((s) => s.settlement));
  let afterDuration = baseFiltered.filter((r) => allowedSettlements.has(r.settlement));
  let staysAfterDuration = stays.filter((s) => allowedSettlements.has(s.settlement));

  const selectedSettlement = $("settlementSelect").getSelectedValue ? $("settlementSelect").getSelectedValue() : $("settlementSelect").value;
  if (selectedSettlement) {
    afterDuration = afterDuration.filter((r) => r.settlement === selectedSettlement);
    staysAfterDuration = staysAfterDuration.filter((s) => s.settlement === selectedSettlement);
  }

  const selectedTypes = selectedValues($("typeSelect"));
  const filteredForEvents = selectedTypes.length ? afterDuration.filter((r) => selectedTypes.includes(r.alert_type)) : afterDuration;

  const uniq = uniqueEvents(filteredForEvents);
  const typeCounts = { launch: 0, shelter_enter: 0, shelter_exit: 0, aircraft: 0, infiltration: 0 };
  uniq.forEach((e) => { typeCounts[e.alert_type] = (typeCounts[e.alert_type] || 0) + 1; });

  const launchByHour = hourlyCountsFromEvents(uniqueEvents(afterDuration.filter((r) => r.alert_type === "launch")));
  const aircraftByHour = hourlyCountsFromEvents(uniqueEvents(afterDuration.filter((r) => r.alert_type === "aircraft")));
  const shelterByHour = hourlyShelterMinutes(staysAfterDuration);

  const statsSettlement = selectedSettlement || null;
  const selectedStats = getSettlementStats(shelterSummary, stays, statsSettlement, baseFiltered);

  const compareA = $("compareSettlementA").getSelectedValue ? $("compareSettlementA").getSelectedValue() : $("compareSettlementA").value;
  const compareB = $("compareSettlementB").getSelectedValue ? $("compareSettlementB").getSelectedValue() : $("compareSettlementB").value;
  const pairRows = baseFiltered.filter((r) => r.settlement === compareA || r.settlement === compareB);
  const pairStays = stays.filter((s) => s.settlement === compareA || s.settlement === compareB);
  const pairLaunchUnique = uniqueEvents(pairRows.filter((r) => r.alert_type === "launch"));

  const launchTotals = [
    { settlement: compareA, count: pairLaunchUnique.filter((x) => x.settlements.includes(compareA)).length },
    { settlement: compareB, count: pairLaunchUnique.filter((x) => x.settlements.includes(compareB)).length },
  ];

  const shelterMinutesBySettlement = new Map();
  pairStays.forEach((s) => shelterMinutesBySettlement.set(s.settlement, (shelterMinutesBySettlement.get(s.settlement) || 0) + s.duration_minutes));
  const shelterTotals = [
    { settlement: compareA, minutes: Math.round(shelterMinutesBySettlement.get(compareA) || 0) },
    { settlement: compareB, minutes: Math.round(shelterMinutesBySettlement.get(compareB) || 0) },
  ];

  const pairHourly = compareHourlyTwo(baseFiltered, stays, compareA, compareB);
  const compareStatsA = getSettlementStats(shelterSummary, stays, compareA || null, baseFiltered);
  const compareStatsB = getSettlementStats(shelterSummary, stays, compareB || null, baseFiltered);

  $("mLaunch").textContent = Number(typeCounts.launch || 0).toLocaleString("he-IL");
  $("mEnter").textContent = Number(typeCounts.shelter_enter || 0).toLocaleString("he-IL");
  $("mExit").textContent = Number(typeCounts.shelter_exit || 0).toLocaleString("he-IL");
  $("mAircraft").textContent = Number(typeCounts.aircraft || 0).toLocaleString("he-IL");
  renderFocusedSettlementStats(selectedStats);

  destroyCharts();
  launchByHourChart = drawBar("launchByHourChart", launchByHour.map((x) => `${String(x.hour).padStart(2, "0")}:00`), launchByHour.map((x) => x.count), "שיגורים לפי שעה", "#0f8b4c");
  shelterByHourChart = drawBar("shelterByHourChart", shelterByHour.map((x) => `${String(x.hour).padStart(2, "0")}:00`), shelterByHour.map((x) => x.minutes), "שהייה במרחב מוגן לפי שעה", "#2c6e49");
  aircraftByHourChart = drawBar("aircraftByHourChart", aircraftByHour.map((x) => `${String(x.hour).padStart(2, "0")}:00`), aircraftByHour.map((x) => x.count), "כלי טיס לפי שעה", "#20639b");

  compareTwoLaunchTotalsChart = drawBar("compareTwoLaunchTotalsChart", launchTotals.map((x) => x.settlement), launchTotals.map((x) => x.count), "כמות שיגורים כוללת", "#0f8b4c");
  compareTwoShelterTotalsChart = drawBar("compareTwoShelterTotalsChart", shelterTotals.map((x) => x.settlement), shelterTotals.map((x) => x.minutes), "זמן שהיה כולל (דקות)", "#20639b");

  compareTwoHourlyLaunchesChart = drawHourlyTwoSettlements("compareTwoHourlyLaunchesChart", pairHourly.launches, compareA, compareB, "count");
  compareTwoHourlyShelterChart = drawHourlyTwoSettlements("compareTwoHourlyShelterChart", pairHourly.shelter, compareA, compareB, "minutes");

  renderCompareSettlementStats("compareStatsA", compareStatsA);
  renderCompareSettlementStats("compareStatsB", compareStatsB);
  renderTable(uniq.sort((a, b) => (a.datetime < b.datetime ? 1 : -1)));

  const csv = toCsv(uniq);
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  $("csvLink").href = URL.createObjectURL(blob);
  $("csvLink").download = "oref_alerts_last_7_days_unique_events.csv";
}

async function bootstrap() {
  const [dataRes, metaRes] = await Promise.all([
    fetch("./data/alerts_history.json", { cache: "no-store" }),
    fetch("./data/metadata.json", { cache: "no-store" }).catch(() => null),
  ]);

  rawRows = await dataRes.json();
  let metaText = "מקור: snapshot מ-AlertsHistory.json";
  if (metaRes && metaRes.ok) {
    const meta = await metaRes.json();
    const updated = meta.updated_at_utc ? new Date(meta.updated_at_utc).toLocaleString("he-IL") : "-";
    metaText = `מקור: ${meta.source || "AlertsHistory.json"} | עודכן: ${updated}`;
  }
  $("sourceText").textContent = metaText;

  $("rangeMode").addEventListener("change", () => { updateRangeVisibility(); runDashboard(); });
  $("applyBtn").addEventListener("click", runDashboard);
  $("compareBtn").addEventListener("click", runDashboard);

  updateRangeVisibility();
  runDashboard();
}

bootstrap().catch((e) => {
  alert(`שגיאה בטעינת הנתונים: ${e.message}`);
});
