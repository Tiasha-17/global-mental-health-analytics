import json
from datetime import datetime, timezone
from pathlib import Path

from mental_health_panel import build_dashboard_payload


OUTPUT_PATH = Path(__file__).resolve().parent.parent / "dashboards" / "mental_health_dashboard.html"


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mental Health Country Comparison Dashboard</title>
  <style>
    :root {
      --bg: #f5efe6;
      --bg-deep: #dfe8e1;
      --panel: rgba(255, 252, 247, 0.88);
      --panel-strong: rgba(255, 250, 244, 0.96);
      --ink: #1f2a33;
      --muted: #5b6872;
      --line: rgba(22, 47, 64, 0.12);
      --teal: #0f766e;
      --navy: #1f3c58;
      --coral: #d95d39;
      --gold: #ba8a1b;
      --sand: #efe4d5;
      --shadow: 0 18px 60px rgba(28, 42, 56, 0.12);
      --radius: 24px;
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(217, 93, 57, 0.12), transparent 28%),
        radial-gradient(circle at top right, rgba(15, 118, 110, 0.16), transparent 24%),
        linear-gradient(160deg, var(--bg) 0%, #f8f3ea 48%, var(--bg-deep) 100%);
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(31, 60, 88, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(31, 60, 88, 0.03) 1px, transparent 1px);
      background-size: 28px 28px;
      pointer-events: none;
    }

    .page-shell {
      position: relative;
      width: min(1320px, calc(100% - 32px));
      margin: 24px auto 48px;
    }

    .hero,
    .panel {
      backdrop-filter: blur(12px);
      background: var(--panel);
      border: 1px solid rgba(255, 255, 255, 0.65);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
    }

    .hero {
      padding: 32px;
      overflow: hidden;
      position: relative;
      background:
        linear-gradient(135deg, rgba(15, 118, 110, 0.1), transparent 36%),
        linear-gradient(315deg, rgba(217, 93, 57, 0.12), transparent 42%),
        var(--panel-strong);
    }

    .hero h1 {
      margin: 0 0 10px;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      font-size: clamp(2rem, 4vw, 3.5rem);
      line-height: 0.98;
      letter-spacing: -0.03em;
      max-width: 12ch;
    }

    .hero p {
      margin: 0;
      max-width: 72ch;
      color: var(--muted);
      font-size: 1rem;
      line-height: 1.65;
    }

    .hero-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 22px;
    }

    .hero-chip {
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.78);
      border: 1px solid rgba(31, 60, 88, 0.08);
      color: var(--navy);
      font-size: 0.92rem;
      font-weight: 600;
    }

    .hero-chip strong {
      color: var(--ink);
    }

    .panel {
      padding: 22px;
      margin-top: 18px;
    }

    .panel h2 {
      margin: 0 0 8px;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      font-size: 1.55rem;
      letter-spacing: -0.02em;
    }

    .panel p.section-copy {
      margin: 0 0 18px;
      color: var(--muted);
      line-height: 1.55;
    }

    .controls-grid,
    .kpi-grid,
    .main-grid,
    .secondary-grid,
    .cluster-grid {
      display: grid;
      gap: 18px;
    }

    .controls-grid {
      grid-template-columns: repeat(5, minmax(0, 1fr));
      align-items: end;
    }

    .main-grid,
    .secondary-grid {
      grid-template-columns: 1.35fr 1fr;
    }

    .cluster-grid {
      grid-template-columns: 1fr 1fr;
    }

    .kpi-grid {
      grid-template-columns: repeat(5, minmax(0, 1fr));
    }

    label {
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      font-size: 0.83rem;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    select {
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(31, 60, 88, 0.12);
      background: rgba(255, 255, 255, 0.84);
      color: var(--ink);
      font: inherit;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.65);
    }

    .scope-note {
      margin-top: 14px;
      color: var(--muted);
      font-size: 0.95rem;
    }

    .kpi-card {
      padding: 20px;
      border-radius: 20px;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.82), rgba(255, 255, 255, 0.62)),
        var(--sand);
      border: 1px solid rgba(31, 60, 88, 0.08);
      min-height: 130px;
    }

    .kpi-label {
      color: var(--muted);
      font-size: 0.8rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .kpi-value {
      margin-top: 14px;
      font-size: clamp(1.8rem, 3vw, 2.5rem);
      font-weight: 700;
      letter-spacing: -0.04em;
      color: var(--navy);
    }

    .kpi-footnote {
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.5;
    }

    .chart-shell {
      min-height: 360px;
    }

    .chart-caption {
      margin: 0 0 16px;
      color: var(--muted);
      line-height: 1.55;
    }

    .legend {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 16px;
      color: var(--muted);
      font-size: 0.92rem;
    }

    .legend-item {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }

    .legend-swatch {
      width: 12px;
      height: 12px;
      border-radius: 999px;
      display: inline-block;
    }

    .table-wrap {
      overflow-x: auto;
      border-radius: 18px;
      border: 1px solid rgba(31, 60, 88, 0.08);
      background: rgba(255, 255, 255, 0.84);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      min-width: 520px;
    }

    th,
    td {
      padding: 13px 14px;
      border-bottom: 1px solid rgba(31, 60, 88, 0.08);
      text-align: left;
    }

    th {
      color: var(--muted);
      font-size: 0.82rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      background: rgba(239, 228, 213, 0.55);
    }

    td strong {
      color: var(--ink);
    }

    .cluster-card {
      padding: 18px;
      border-radius: 18px;
      border: 1px solid rgba(31, 60, 88, 0.08);
      background: rgba(255, 255, 255, 0.86);
    }

    .cluster-title {
      margin: 0 0 10px;
      font-size: 1.08rem;
      color: var(--navy);
    }

    .cluster-metrics {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
      margin-top: 14px;
    }

    .cluster-metric {
      padding: 12px;
      border-radius: 14px;
      background: rgba(245, 239, 230, 0.75);
    }

    .cluster-metric span {
      display: block;
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .cluster-metric strong {
      display: block;
      margin-top: 8px;
      color: var(--ink);
      font-size: 1.18rem;
      letter-spacing: -0.03em;
    }

    .empty-state {
      display: grid;
      place-items: center;
      min-height: 260px;
      border-radius: 18px;
      border: 1px dashed rgba(31, 60, 88, 0.18);
      color: var(--muted);
      background: rgba(255, 255, 255, 0.5);
      text-align: center;
      padding: 24px;
    }

    .footer-note {
      margin-top: 18px;
      color: var(--muted);
      text-align: right;
      font-size: 0.9rem;
    }

    @media (max-width: 1100px) {
      .controls-grid,
      .kpi-grid,
      .main-grid,
      .secondary-grid,
      .cluster-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="page-shell">
    <section class="hero">
      <h1>Mental Health Country Comparison Dashboard</h1>
      <p>
        Explore the same merged mental-health panel used in the notebooks, but with a faster way
        to compare countries, switch years, inspect gender gaps, and see how prevalence maps to burden.
      </p>
      <div class="hero-meta" id="heroMeta"></div>
    </section>

    <section class="panel">
      <h2>Controls</h2>
      <p class="section-copy">
        Use the snapshot filters to change the ranking, KPI cards, and burden scatter.
        The head-to-head country comparison stays available for any two countries, even across continents.
      </p>
      <div class="controls-grid">
        <div>
          <label for="yearSelect">Snapshot Year</label>
          <select id="yearSelect"></select>
        </div>
        <div>
          <label for="continentSelect">Snapshot Continent</label>
          <select id="continentSelect"></select>
        </div>
        <div>
          <label for="metricSelect">Comparison Metric</label>
          <select id="metricSelect"></select>
        </div>
        <div>
          <label for="countryASelect">Country A</label>
          <select id="countryASelect"></select>
        </div>
        <div>
          <label for="countryBSelect">Country B</label>
          <select id="countryBSelect"></select>
        </div>
      </div>
      <div class="scope-note" id="scopeNote"></div>
    </section>

    <section class="panel">
      <h2>Snapshot Overview</h2>
      <p class="section-copy">
        These cards summarize the countries currently in scope for the selected year and continent filter.
      </p>
      <div class="kpi-grid" id="kpiGrid"></div>
    </section>

    <div class="main-grid">
      <section class="panel">
        <h2>Trend Comparison</h2>
        <p class="chart-caption">
          Compare two countries over time while keeping the selected metric consistent.
          The sand-colored reference line shows the mean for the current continent scope.
        </p>
        <div class="chart-shell" id="trendChart"></div>
      </section>

      <section class="panel">
        <h2>Head to Head</h2>
        <p class="chart-caption">
          This table compares the selected countries on the current snapshot year and also carries the recent cluster label from the advanced notebook section.
        </p>
        <div id="comparisonTable"></div>
        <div style="height: 18px;"></div>
        <div id="recentProfileCards"></div>
      </section>
    </div>

    <div class="secondary-grid">
      <section class="panel">
        <h2>Top Countries by Snapshot Metric</h2>
        <p class="chart-caption">
          Ranking updates from the same filters above, which makes it easier to compare a country against the current peer set.
        </p>
        <div class="chart-shell" id="rankingChart"></div>
      </section>

      <section class="panel">
        <h2>Burden vs Prevalence</h2>
        <p class="chart-caption">
          Each point is a country for the selected year. Selected countries are emphasized so you can see whether they sit above or below the broader burden pattern.
        </p>
        <div class="chart-shell" id="scatterChart"></div>
      </section>
    </div>

    <div class="cluster-grid">
      <section class="panel">
        <h2>Recent Cluster Summary</h2>
        <p class="chart-caption">
          These averages use the notebook’s recent-period clustering window from 2015 to 2019.
        </p>
        <div id="clusterSummary"></div>
      </section>

      <section class="panel">
        <h2>How to Read This</h2>
        <p class="section-copy">
          The dashboard is best for repeated country comparison. Use the trend chart for long-run movement,
          the ranking chart for one-year positioning, and the burden scatter to see whether prevalence and DALY burden move together for your selected countries.
        </p>
        <div class="cluster-card">
          <h3 class="cluster-title">Notebook outputs now translated into dashboard views</h3>
          <div class="cluster-metrics">
            <div class="cluster-metric">
              <span>Beginner</span>
              <strong>Trend line + ranking</strong>
            </div>
            <div class="cluster-metric">
              <span>Intermediate</span>
              <strong>Gender gap + head to head</strong>
            </div>
            <div class="cluster-metric">
              <span>Advanced</span>
              <strong>Burden scatter + clusters</strong>
            </div>
            <div class="cluster-metric">
              <span>Reuse</span>
              <strong>Self-contained HTML</strong>
            </div>
          </div>
        </div>
      </section>
    </div>

    <div class="footer-note" id="footerNote"></div>
  </div>

  <script id="dashboard-data" type="application/json">__DATA_JSON__</script>
  <script>
    const payload = JSON.parse(document.getElementById("dashboard-data").textContent);
    const records = payload.panel;
    const recentProfiles = payload.recent_profile;
    const clusterSummary = payload.cluster_summary;
    const metricLabels = payload.metric_labels;
    const summary = payload.summary;

    const yearValues = [...new Set(records.map((row) => row.Year))].sort((a, b) => a - b);
    const countryValues = [...new Set(records.map((row) => row.Entity))].sort((a, b) => a.localeCompare(b));
    const continentValues = [
      "All",
      ...[...new Set(records.map((row) => row.continent).filter(Boolean))].sort((a, b) => a.localeCompare(b)),
    ];
    const metricOptions = [
      "mental_prev",
      "depression_prev",
      "daly_share",
      "depression_gender_gap",
      "burden_ratio",
      "anxiety_prev",
      "alcohol_prev",
      "drug_prev",
      "eating_prev",
    ];

    const colors = {
      teal: "#0f766e",
      navy: "#1f3c58",
      coral: "#d95d39",
      gold: "#ba8a1b",
      sand: "#b98954",
      line: "rgba(31, 60, 88, 0.18)",
      ink: "#1f2a33",
      mute: "#5b6872",
      grid: "rgba(31, 60, 88, 0.08)",
    };

    const defaultCountryA = countryValues.includes("United States") ? "United States" : countryValues[0];
    let defaultCountryB = countryValues.includes("Australia") ? "Australia" : countryValues[1];
    if (defaultCountryA === defaultCountryB) {
      defaultCountryB = countryValues[2] || countryValues[0];
    }

    const state = {
      year: yearValues[yearValues.length - 1],
      continent: "All",
      metric: "mental_prev",
      countryA: defaultCountryA,
      countryB: defaultCountryB,
    };

    const formatNumber = new Intl.NumberFormat("en-US", {
      maximumFractionDigits: 2,
      minimumFractionDigits: 2,
    });
    const formatInt = new Intl.NumberFormat("en-US");

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    function averageValue(rows, field) {
      const values = rows.map((row) => Number(row[field])).filter((value) => Number.isFinite(value));
      if (!values.length) {
        return null;
      }
      return values.reduce((sum, value) => sum + value, 0) / values.length;
    }

    function weightedAverage(rows, numeratorField, weightField) {
      const pairs = rows
        .map((row) => [Number(row[numeratorField]), Number(row[weightField])])
        .filter(([value, weight]) => Number.isFinite(value) && Number.isFinite(weight) && weight > 0);
      if (!pairs.length) {
        return null;
      }
      const weightedSum = pairs.reduce((sum, [value, weight]) => sum + value * weight, 0);
      const totalWeight = pairs.reduce((sum, [, weight]) => sum + weight, 0);
      return totalWeight ? weightedSum / totalWeight : null;
    }

    function formatMetric(metric, value) {
      if (value === null || value === undefined || !Number.isFinite(Number(value))) {
        return "n/a";
      }
      if (metric === "burden_ratio") {
        return formatNumber.format(Number(value));
      }
      if (metric.endsWith("_gap")) {
        return formatNumber.format(Number(value)) + " pts";
      }
      return formatNumber.format(Number(value)) + "%";
    }

    function getScopeRows() {
      return records.filter((row) => {
        if (row.Year !== state.year) {
          return false;
        }
        if (state.continent !== "All" && row.continent !== state.continent) {
          return false;
        }
        return true;
      });
    }

    function getCountrySeries(country, metric) {
      return records
        .filter((row) => row.Entity === country)
        .map((row) => ({ x: row.Year, y: Number(row[metric]), continent: row.continent }))
        .filter((row) => Number.isFinite(row.y));
    }

    function getScopeTrend(metric) {
      return yearValues
        .map((year) => {
          const rows = records.filter((row) => {
            if (row.Year !== year) {
              return false;
            }
            if (state.continent !== "All" && row.continent !== state.continent) {
              return false;
            }
            return true;
          });
          return { x: year, y: averageValue(rows, metric) };
        })
        .filter((row) => row.y !== null);
    }

    function makeOptionMarkup(values, selectedValue) {
      return values
        .map((value) => {
          const selected = value === selectedValue ? " selected" : "";
          return `<option value="${escapeHtml(value)}"${selected}>${escapeHtml(value)}</option>`;
        })
        .join("");
    }

    function renderHero() {
      const heroMeta = document.getElementById("heroMeta");
      heroMeta.innerHTML = [
        `<div class="hero-chip"><strong>${formatInt.format(summary.countries)}</strong> countries</div>`,
        `<div class="hero-chip"><strong>${formatInt.format(summary.rows)}</strong> country-year rows</div>`,
        `<div class="hero-chip"><strong>${summary.start_year}-${summary.end_year}</strong> comparison window</div>`,
        `<div class="hero-chip"><strong>${summary.best_k}</strong> recent clusters</div>`,
      ].join("");
      document.getElementById("footerNote").textContent =
        "Generated from the notebook-aligned panel on " + summary.generated_at + ".";
    }

    function renderControls() {
      document.getElementById("yearSelect").innerHTML = makeOptionMarkup(yearValues, state.year);
      document.getElementById("continentSelect").innerHTML = makeOptionMarkup(continentValues, state.continent);
      document.getElementById("metricSelect").innerHTML = metricOptions
        .map((metric) => {
          const selected = metric === state.metric ? " selected" : "";
          return `<option value="${metric}"${selected}>${escapeHtml(metricLabels[metric])}</option>`;
        })
        .join("");
      document.getElementById("countryASelect").innerHTML = makeOptionMarkup(countryValues, state.countryA);
      document.getElementById("countryBSelect").innerHTML = makeOptionMarkup(countryValues, state.countryB);

      const scopeText =
        state.continent === "All"
          ? `Showing all countries in ${state.year}.`
          : `Showing ${state.continent} countries in ${state.year}.`;
      document.getElementById("scopeNote").textContent =
        scopeText + " Trend comparison uses the same metric for both selected countries.";
    }

    function renderKpis() {
      const rows = getScopeRows();
      const cards = [
        {
          label: "Countries in Scope",
          value: formatInt.format(rows.length),
          footnote: "Snapshot peers included after the current continent filter.",
        },
        {
          label: "Avg Mental Prevalence",
          value: formatMetric("mental_prev", averageValue(rows, "mental_prev")),
          footnote: "Simple country mean for the current snapshot.",
        },
        {
          label: "Weighted Mental Prev",
          value: formatMetric("mental_prev", weightedAverage(rows, "mental_prev", "population")),
          footnote: "Population-weighted mental-disorder prevalence for the same scope.",
        },
        {
          label: "Avg Gender Gap",
          value: formatMetric("depression_gender_gap", averageValue(rows, "depression_gender_gap")),
          footnote: "Female minus male depression prevalence gap.",
        },
        {
          label: "Avg DALY Share",
          value: formatMetric("daly_share", averageValue(rows, "daly_share")),
          footnote: "Mean burden share for the selected countries and year.",
        },
      ];

      document.getElementById("kpiGrid").innerHTML = cards
        .map(
          (card) => `
            <div class="kpi-card">
              <div class="kpi-label">${escapeHtml(card.label)}</div>
              <div class="kpi-value">${escapeHtml(card.value)}</div>
              <div class="kpi-footnote">${escapeHtml(card.footnote)}</div>
            </div>
          `
        )
        .join("");
    }

    function renderLineChart(containerId, series, yLabel) {
      const container = document.getElementById(containerId);
      const allPoints = series.flatMap((entry) => entry.points);
      if (!allPoints.length) {
        container.innerHTML = '<div class="empty-state">No data available for this chart.</div>';
        return;
      }

      const width = 760;
      const height = 330;
      const margin = { top: 20, right: 20, bottom: 48, left: 60 };
      const xMin = Math.min(...allPoints.map((point) => point.x));
      const xMax = Math.max(...allPoints.map((point) => point.x));
      const yValues = allPoints.map((point) => point.y);
      let yMin = Math.min(...yValues);
      let yMax = Math.max(...yValues);
      if (yMin === yMax) {
        yMin -= 1;
        yMax += 1;
      }
      const padding = (yMax - yMin) * 0.12;
      yMin -= padding;
      yMax += padding;

      const scaleX = (value) =>
        margin.left + ((value - xMin) / (xMax - xMin || 1)) * (width - margin.left - margin.right);
      const scaleY = (value) =>
        height - margin.bottom - ((value - yMin) / (yMax - yMin || 1)) * (height - margin.top - margin.bottom);

      const yTicks = 5;
      const xTicks = yearValues.filter((year, index) => index % 5 === 0 || index === yearValues.length - 1);

      const gridLines = Array.from({ length: yTicks + 1 }, (_, tick) => {
        const value = yMin + ((yMax - yMin) / yTicks) * tick;
        const y = scaleY(value);
        return `
          <line x1="${margin.left}" y1="${y}" x2="${width - margin.right}" y2="${y}" stroke="${colors.grid}" />
          <text x="${margin.left - 12}" y="${y + 4}" text-anchor="end" font-size="11" fill="${colors.mute}">
            ${escapeHtml(formatNumber.format(value))}
          </text>
        `;
      }).join("");

      const xAxisLabels = xTicks
        .map((year) => {
          const x = scaleX(year);
          return `
            <line x1="${x}" y1="${height - margin.bottom}" x2="${x}" y2="${height - margin.bottom + 6}" stroke="${colors.line}" />
            <text x="${x}" y="${height - margin.bottom + 22}" text-anchor="middle" font-size="11" fill="${colors.mute}">
              ${year}
            </text>
          `;
        })
        .join("");

      const paths = series
        .map((entry) => {
          const points = entry.points.map((point) => `${scaleX(point.x)},${scaleY(point.y)}`).join(" ");
          const dash = entry.dashed ? ' stroke-dasharray="7 6"' : "";
          const circles = entry.points
            .map(
              (point) =>
                `<circle cx="${scaleX(point.x)}" cy="${scaleY(point.y)}" r="3.4" fill="${entry.color}" opacity="0.9"></circle>`
            )
            .join("");
          return `
            <polyline fill="none" stroke="${entry.color}" stroke-width="3"${dash} points="${points}"></polyline>
            ${circles}
          `;
        })
        .join("");

      container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" role="img" aria-label="${escapeHtml(yLabel)} trend chart">
          ${gridLines}
          <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" stroke="${colors.line}" />
          <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" stroke="${colors.line}" />
          ${xAxisLabels}
          ${paths}
          <text x="${width / 2}" y="${height - 10}" text-anchor="middle" font-size="12" fill="${colors.mute}">Year</text>
          <text x="18" y="${height / 2}" transform="rotate(-90 18 ${height / 2})" text-anchor="middle" font-size="12" fill="${colors.mute}">
            ${escapeHtml(yLabel)}
          </text>
        </svg>
        <div class="legend">
          ${series
            .map(
              (entry) => `
                <span class="legend-item">
                  <span class="legend-swatch" style="background:${entry.color};"></span>
                  ${escapeHtml(entry.name)}
                </span>
              `
            )
            .join("")}
        </div>
      `;
    }

    function renderBarChart(containerId, rows, metric) {
      const container = document.getElementById(containerId);
      if (!rows.length) {
        container.innerHTML = '<div class="empty-state">No countries match the current snapshot filter.</div>';
        return;
      }

      const topRows = rows.slice(0, 12);
      const width = 760;
      const rowHeight = 34;
      const height = 52 + topRows.length * rowHeight;
      const margin = { top: 10, right: 20, bottom: 24, left: 190 };
      const maxValue = Math.max(...topRows.map((row) => Number(row[metric]) || 0), 0.001);
      const scaleX = (value) =>
        margin.left + (Number(value) / maxValue) * (width - margin.left - margin.right);

      const bars = topRows
        .map((row, index) => {
          const y = margin.top + index * rowHeight;
          const selected = row.Entity === state.countryA || row.Entity === state.countryB;
          const color = row.Entity === state.countryA ? colors.teal : row.Entity === state.countryB ? colors.coral : colors.navy;
          const barWidth = scaleX(row[metric]) - margin.left;
          return `
            <text x="${margin.left - 12}" y="${y + 18}" text-anchor="end" font-size="12" fill="${colors.ink}" font-weight="${selected ? 700 : 500}">
              ${escapeHtml(row.Entity)}
            </text>
            <rect x="${margin.left}" y="${y + 4}" width="${barWidth}" height="18" rx="9" fill="${selected ? color : colors.sand}" opacity="${selected ? 1 : 0.88}"></rect>
            <text x="${scaleX(row[metric]) + 8}" y="${y + 18}" font-size="12" fill="${colors.mute}">
              ${escapeHtml(formatMetric(metric, row[metric]))}
            </text>
          `;
        })
        .join("");

      container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" role="img" aria-label="${escapeHtml(metricLabels[metric])} ranking chart">
          ${bars}
        </svg>
      `;
    }

    function renderScatterChart(containerId, rows) {
      const container = document.getElementById(containerId);
      const points = rows
        .map((row) => ({
          name: row.Entity,
          x: Number(row.mental_prev),
          y: Number(row.daly_share),
        }))
        .filter((row) => Number.isFinite(row.x) && Number.isFinite(row.y));

      if (!points.length) {
        container.innerHTML = '<div class="empty-state">No countries match the current snapshot filter.</div>';
        return;
      }

      const width = 760;
      const height = 330;
      const margin = { top: 16, right: 16, bottom: 48, left: 60 };
      let xMin = Math.min(...points.map((point) => point.x));
      let xMax = Math.max(...points.map((point) => point.x));
      let yMin = Math.min(...points.map((point) => point.y));
      let yMax = Math.max(...points.map((point) => point.y));
      xMin -= 0.4;
      xMax += 0.4;
      yMin -= 0.4;
      yMax += 0.4;

      const scaleX = (value) =>
        margin.left + ((value - xMin) / (xMax - xMin || 1)) * (width - margin.left - margin.right);
      const scaleY = (value) =>
        height - margin.bottom - ((value - yMin) / (yMax - yMin || 1)) * (height - margin.top - margin.bottom);

      const xMean = averageValue(rows, "mental_prev");
      const yMean = averageValue(rows, "daly_share");

      const scatterPoints = points
        .map((point) => {
          const selected = point.name === state.countryA || point.name === state.countryB;
          const color = point.name === state.countryA ? colors.teal : point.name === state.countryB ? colors.coral : colors.navy;
          const radius = selected ? 6 : 3.8;
          const opacity = selected ? 1 : 0.46;
          const label = selected
            ? `<text x="${scaleX(point.x) + 8}" y="${scaleY(point.y) - 8}" font-size="11" fill="${colors.ink}">${escapeHtml(point.name)}</text>`
            : "";
          return `
            <circle cx="${scaleX(point.x)}" cy="${scaleY(point.y)}" r="${radius}" fill="${color}" opacity="${opacity}"></circle>
            ${label}
          `;
        })
        .join("");

      container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" role="img" aria-label="Burden versus prevalence scatter chart">
          <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" stroke="${colors.line}" />
          <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" stroke="${colors.line}" />
          <line x1="${scaleX(xMean)}" y1="${margin.top}" x2="${scaleX(xMean)}" y2="${height - margin.bottom}" stroke="${colors.grid}" stroke-dasharray="6 6" />
          <line x1="${margin.left}" y1="${scaleY(yMean)}" x2="${width - margin.right}" y2="${scaleY(yMean)}" stroke="${colors.grid}" stroke-dasharray="6 6" />
          ${scatterPoints}
          <text x="${width / 2}" y="${height - 10}" text-anchor="middle" font-size="12" fill="${colors.mute}">Mental prevalence (%)</text>
          <text x="18" y="${height / 2}" transform="rotate(-90 18 ${height / 2})" text-anchor="middle" font-size="12" fill="${colors.mute}">
            DALY share (%)
          </text>
        </svg>
        <div class="legend">
          <span class="legend-item"><span class="legend-swatch" style="background:${colors.teal};"></span>${escapeHtml(state.countryA)}</span>
          <span class="legend-item"><span class="legend-swatch" style="background:${colors.coral};"></span>${escapeHtml(state.countryB)}</span>
          <span class="legend-item"><span class="legend-swatch" style="background:${colors.navy};"></span>Other countries in scope</span>
        </div>
      `;
    }

    function renderComparisonTable() {
      const snapshotRows = records.filter((row) => row.Year === state.year);
      const countryA = snapshotRows.find((row) => row.Entity === state.countryA);
      const countryB = snapshotRows.find((row) => row.Entity === state.countryB);
      const metrics = [
        ["continent", "Continent"],
        ["mental_prev", "Mental prevalence"],
        ["depression_prev", "Depression prevalence"],
        ["daly_share", "DALY share"],
        ["depression_gender_gap", "Depression gender gap"],
        ["burden_ratio", "Burden ratio"],
        ["cluster_label", "Recent cluster"],
      ];

      const rows = metrics
        .map(([key, label]) => {
          const leftValue =
            key === "continent" || key === "cluster_label"
              ? countryA?.[key] ?? "n/a"
              : formatMetric(key, countryA?.[key]);
          const rightValue =
            key === "continent" || key === "cluster_label"
              ? countryB?.[key] ?? "n/a"
              : formatMetric(key, countryB?.[key]);
          return `
            <tr>
              <td><strong>${escapeHtml(label)}</strong></td>
              <td>${escapeHtml(leftValue)}</td>
              <td>${escapeHtml(rightValue)}</td>
            </tr>
          `;
        })
        .join("");

      document.getElementById("comparisonTable").innerHTML = `
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Metric</th>
                <th>${escapeHtml(state.countryA)} (${state.year})</th>
                <th>${escapeHtml(state.countryB)} (${state.year})</th>
              </tr>
            </thead>
            <tbody>${rows}</tbody>
          </table>
        </div>
      `;
    }

    function renderRecentProfiles() {
      const profileA = recentProfiles.find((row) => row.Entity === state.countryA);
      const profileB = recentProfiles.find((row) => row.Entity === state.countryB);
      const cards = [profileA, profileB]
        .filter(Boolean)
        .map(
          (profile) => `
            <div class="cluster-card" style="margin-top: 12px;">
              <h3 class="cluster-title">${escapeHtml(profile.Entity)} · ${escapeHtml(profile.cluster_label)}</h3>
              <div class="cluster-metrics">
                <div class="cluster-metric">
                  <span>2015-2019 Mental Prev</span>
                  <strong>${escapeHtml(formatMetric("mental_prev", profile.mental_prev))}</strong>
                </div>
                <div class="cluster-metric">
                  <span>2015-2019 DALY Share</span>
                  <strong>${escapeHtml(formatMetric("daly_share", profile.daly_share))}</strong>
                </div>
                <div class="cluster-metric">
                  <span>Avg Depression Gap</span>
                  <strong>${escapeHtml(formatMetric("depression_gender_gap", profile.depression_gender_gap))}</strong>
                </div>
                <div class="cluster-metric">
                  <span>Anxiety Prev</span>
                  <strong>${escapeHtml(formatMetric("anxiety_prev", profile.anxiety_prev))}</strong>
                </div>
              </div>
            </div>
          `
        )
        .join("");

      document.getElementById("recentProfileCards").innerHTML = cards;
    }

    function renderClusterSummary() {
      document.getElementById("clusterSummary").innerHTML = clusterSummary
        .map(
          (cluster) => `
            <div class="cluster-card" style="margin-bottom: 12px;">
              <h3 class="cluster-title">${escapeHtml(cluster.cluster_label)}</h3>
              <div class="cluster-metrics">
                <div class="cluster-metric">
                  <span>Countries</span>
                  <strong>${escapeHtml(formatInt.format(cluster.countries))}</strong>
                </div>
                <div class="cluster-metric">
                  <span>Mental Prev</span>
                  <strong>${escapeHtml(formatMetric("mental_prev", cluster.mental_prev))}</strong>
                </div>
                <div class="cluster-metric">
                  <span>DALY Share</span>
                  <strong>${escapeHtml(formatMetric("daly_share", cluster.daly_share))}</strong>
                </div>
                <div class="cluster-metric">
                  <span>Depression Gap</span>
                  <strong>${escapeHtml(formatMetric("depression_gender_gap", cluster.depression_gender_gap))}</strong>
                </div>
              </div>
            </div>
          `
        )
        .join("");
    }

    function renderTrendSection() {
      const series = [
        {
          name: state.continent === "All" ? "Global mean" : `${state.continent} mean`,
          color: colors.sand,
          dashed: true,
          points: getScopeTrend(state.metric),
        },
        {
          name: state.countryA,
          color: colors.teal,
          points: getCountrySeries(state.countryA, state.metric),
        },
        {
          name: state.countryB,
          color: colors.coral,
          points: getCountrySeries(state.countryB, state.metric),
        },
      ].filter((entry) => entry.points.length);

      renderLineChart("trendChart", series, metricLabels[state.metric]);
    }

    function renderRankingSection() {
      const rankedRows = getScopeRows()
        .slice()
        .sort((left, right) => Number(right[state.metric]) - Number(left[state.metric]));
      renderBarChart("rankingChart", rankedRows, state.metric);
    }

    function renderScatterSection() {
      renderScatterChart("scatterChart", getScopeRows());
    }

    function renderAll() {
      renderControls();
      renderKpis();
      renderTrendSection();
      renderComparisonTable();
      renderRecentProfiles();
      renderRankingSection();
      renderScatterSection();
      renderClusterSummary();
    }

    function wireControls() {
      document.getElementById("yearSelect").addEventListener("change", (event) => {
        state.year = Number(event.target.value);
        renderAll();
      });
      document.getElementById("continentSelect").addEventListener("change", (event) => {
        state.continent = event.target.value;
        renderAll();
      });
      document.getElementById("metricSelect").addEventListener("change", (event) => {
        state.metric = event.target.value;
        renderAll();
      });
      document.getElementById("countryASelect").addEventListener("change", (event) => {
        state.countryA = event.target.value;
        renderAll();
      });
      document.getElementById("countryBSelect").addEventListener("change", (event) => {
        state.countryB = event.target.value;
        renderAll();
      });
    }

    renderHero();
    renderAll();
    wireControls();
  </script>
</body>
</html>
"""


def build_dashboard():
    payload = build_dashboard_payload()
    payload["summary"]["generated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)

    OUTPUT_PATH.write_text(html, encoding="utf-8")
    return OUTPUT_PATH


if __name__ == "__main__":
    built_path = build_dashboard()
    print(f"Built {built_path}")
