import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from mental_health_panel import build_mental_health_panel


OUTPUT_PATH = Path(__file__).resolve().parent.parent / "dashboards" / "mental_health_sql_dashboard.html"
SQL_SCRIPT_PATH = Path(__file__).resolve().parent.parent / "sql" / "queries.sql"


def parse_sql_sections(sql_text):
    sections = {}
    current_title = None
    current_lines = []

    for line in sql_text.splitlines():
        heading = re.match(r"^--\s+\d+\.\s+(.*)$", line)
        if heading:
            if current_title and current_lines:
                key = re.sub(r"[^a-z0-9]+", "_", current_title.lower()).strip("_")
                sections[key] = "\n".join(current_lines).strip()
            current_title = heading.group(1).strip()
            current_lines = []
        elif current_title and not line.startswith("--"):
            current_lines.append(line)

    if current_title and current_lines:
        key = re.sub(r"[^a-z0-9]+", "_", current_title.lower()).strip("_")
        sections[key] = "\n".join(current_lines).strip()

    return sections


def frame_to_records(df, digits=4):
    clean = df.copy()
    numeric_cols = clean.select_dtypes(include=["number"]).columns
    clean[numeric_cols] = clean[numeric_cols].round(digits)
    clean = clean.replace({np.nan: None})
    return clean.to_dict(orient="records")


def run_query(conn, query, digits=4):
    return frame_to_records(pd.read_sql_query(query, conn), digits=digits)


def build_sql_dashboard_payload():
    panel = build_mental_health_panel()
    conn = sqlite3.connect(":memory:")
    panel.to_sql("mental_health_panel", conn, index=False, if_exists="replace")

    sql_sections = parse_sql_sections(SQL_SCRIPT_PATH.read_text(encoding="utf-8"))

    query_results = {
        name: run_query(conn, query)
        for name, query in sql_sections.items()
    }

    panel_query = """
    SELECT
        Entity,
        Code,
        Year,
        continent,
        population,
        mental_prev,
        depression_prev,
        daly_share,
        depression_gender_gap,
        mental_gender_gap,
        anxiety_prev,
        alcohol_prev,
        drug_prev,
        eating_prev,
        schizophrenia_prev,
        bipolar_prev,
        burden_ratio
    FROM mental_health_panel
    ORDER BY Entity, Year
    """

    recent_profile_query = """
    WITH recent AS (
        SELECT
            Entity,
            Code,
            continent,
            AVG(mental_prev) AS avg_mental_prev,
            AVG(daly_share) AS avg_daly_share,
            AVG(depression_gender_gap) AS avg_depression_gap
        FROM mental_health_panel
        WHERE Year BETWEEN 2015 AND 2019
        GROUP BY Entity, Code, continent
    )
    SELECT
        Entity,
        Code,
        continent,
        avg_mental_prev,
        avg_daly_share,
        avg_depression_gap,
        CASE
            WHEN avg_mental_prev >= 15 AND avg_daly_share >= 7 THEN 'High prevalence / High burden'
            WHEN avg_mental_prev >= 15 AND avg_daly_share < 7 THEN 'High prevalence / Lower burden'
            WHEN avg_mental_prev < 15 AND avg_daly_share >= 7 THEN 'Lower prevalence / High burden'
            ELSE 'Lower prevalence / Lower burden'
        END AS profile_band
    FROM recent
    ORDER BY avg_daly_share DESC, avg_mental_prev DESC
    """

    payload = {
        "summary": {
            "rows": int(len(panel)),
            "countries": int(panel["Code"].nunique()),
            "start_year": int(panel["Year"].min()),
            "end_year": int(panel["Year"].max()),
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        },
        "metric_labels": {
            "mental_prev": "Mental prevalence (%)",
            "depression_prev": "Depression prevalence (%)",
            "daly_share": "DALY share (%)",
            "depression_gender_gap": "Depression gender gap",
            "burden_ratio": "Burden ratio",
            "anxiety_prev": "Anxiety prevalence (%)",
            "alcohol_prev": "Alcohol prevalence (%)",
            "drug_prev": "Drug prevalence (%)",
            "eating_prev": "Eating-disorder prevalence (%)",
        },
        "panel": run_query(conn, panel_query),
        "recent_profiles": run_query(conn, recent_profile_query),
        "query_results": query_results,
    }

    conn.close()
    return payload


HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Mental Health SQL Dashboard</title>
  <style>
    :root {
      --bg: #11161d;
      --bg-alt: #182230;
      --panel: rgba(16, 24, 34, 0.86);
      --panel-strong: rgba(13, 19, 28, 0.95);
      --line: rgba(196, 211, 226, 0.12);
      --ink: #f3f0e8;
      --muted: #a4b0bd;
      --mint: #65c3ba;
      --amber: #d8a84d;
      --rose: #f07f74;
      --ice: #8cb8ff;
      --radius: 24px;
      --shadow: 0 22px 70px rgba(0, 0, 0, 0.28);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      color: var(--ink);
      font-family: "Avenir Next", "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(140, 184, 255, 0.16), transparent 24%),
        radial-gradient(circle at top right, rgba(101, 195, 186, 0.15), transparent 24%),
        linear-gradient(180deg, #0d1218 0%, #11161d 45%, #182230 100%);
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      background-image:
        linear-gradient(rgba(255, 255, 255, 0.02) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.02) 1px, transparent 1px);
      background-size: 26px 26px;
      pointer-events: none;
    }

    .page-shell {
      width: min(1360px, calc(100% - 32px));
      margin: 24px auto 48px;
      position: relative;
    }

    .hero,
    .panel {
      background: var(--panel);
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }

    .hero {
      padding: 34px;
      background:
        linear-gradient(135deg, rgba(101, 195, 186, 0.12), transparent 34%),
        linear-gradient(315deg, rgba(240, 127, 116, 0.12), transparent 38%),
        var(--panel-strong);
    }

    .eyebrow {
      color: var(--mint);
      text-transform: uppercase;
      letter-spacing: 0.18em;
      font-size: 0.78rem;
      font-weight: 700;
      margin-bottom: 14px;
    }

    .hero h1 {
      margin: 0 0 10px;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: clamp(2rem, 4vw, 3.6rem);
      line-height: 0.98;
      letter-spacing: -0.03em;
      max-width: 12ch;
    }

    .hero p {
      margin: 0;
      color: var(--muted);
      max-width: 72ch;
      line-height: 1.65;
    }

    .hero-meta {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-top: 24px;
    }

    .hero-chip {
      padding: 10px 14px;
      border-radius: 999px;
      background: rgba(255, 255, 255, 0.06);
      border: 1px solid rgba(255, 255, 255, 0.08);
      color: var(--ink);
      font-size: 0.92rem;
    }

    .hero-chip strong {
      color: white;
    }

    .panel {
      padding: 22px;
      margin-top: 18px;
    }

    .panel h2 {
      margin: 0 0 8px;
      font-family: "Iowan Old Style", "Palatino Linotype", serif;
      font-size: 1.55rem;
      letter-spacing: -0.02em;
    }

    .section-copy,
    .chart-caption,
    .scope-note,
    .footer-note {
      color: var(--muted);
      line-height: 1.55;
    }

    .controls-grid,
    .kpi-grid,
    .main-grid,
    .secondary-grid,
    .sql-grid,
    .summary-grid,
    .query-card-grid {
      display: grid;
      gap: 18px;
    }

    .controls-grid {
      grid-template-columns: repeat(5, minmax(0, 1fr));
      align-items: end;
    }

    .kpi-grid {
      grid-template-columns: repeat(5, minmax(0, 1fr));
    }

    .main-grid,
    .secondary-grid {
      grid-template-columns: 1.35fr 1fr;
    }

    .sql-grid,
    .summary-grid {
      grid-template-columns: 1fr 1fr;
    }

    .query-card-grid {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }

    label {
      display: block;
      margin-bottom: 8px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-size: 0.82rem;
      font-weight: 700;
    }

    select {
      width: 100%;
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.06);
      color: var(--ink);
      font: inherit;
    }

    .kpi-card,
    .query-card,
    .profile-card,
    .mini-note {
      border-radius: 20px;
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.04);
    }

    .kpi-card {
      padding: 18px;
      min-height: 132px;
    }

    .kpi-label {
      color: var(--muted);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      font-weight: 700;
    }

    .kpi-value {
      margin-top: 14px;
      font-size: clamp(1.7rem, 3vw, 2.45rem);
      font-weight: 700;
      letter-spacing: -0.04em;
    }

    .kpi-footnote {
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.92rem;
      line-height: 1.45;
    }

    .chart-shell {
      min-height: 360px;
    }

    .legend {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
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
      border: 1px solid rgba(255, 255, 255, 0.08);
      background: rgba(255, 255, 255, 0.03);
    }

    table {
      width: 100%;
      min-width: 520px;
      border-collapse: collapse;
    }

    th,
    td {
      padding: 12px 14px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.07);
      text-align: left;
    }

    th {
      color: var(--muted);
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      background: rgba(255, 255, 255, 0.04);
    }

    .query-card {
      padding: 16px;
    }

    .query-title {
      margin: 0 0 10px;
      color: var(--ink);
      font-size: 1.02rem;
    }

    .query-card ul {
      margin: 0;
      padding-left: 18px;
      color: var(--muted);
      line-height: 1.5;
    }

    .profile-card {
      padding: 18px;
      margin-bottom: 12px;
    }

    .profile-title {
      margin: 0 0 8px;
      font-size: 1.08rem;
      color: var(--ink);
    }

    .profile-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 14px;
    }

    .profile-metric {
      padding: 12px;
      border-radius: 14px;
      background: rgba(255, 255, 255, 0.04);
    }

    .profile-metric span {
      display: block;
      color: var(--muted);
      font-size: 0.75rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .profile-metric strong {
      display: block;
      margin-top: 6px;
      font-size: 1.12rem;
    }

    .empty-state {
      display: grid;
      place-items: center;
      min-height: 240px;
      border-radius: 18px;
      border: 1px dashed rgba(255, 255, 255, 0.12);
      color: var(--muted);
      text-align: center;
      padding: 24px;
      background: rgba(255, 255, 255, 0.03);
    }

    .mini-note {
      padding: 16px;
      margin-top: 14px;
      color: var(--muted);
      font-size: 0.95rem;
      line-height: 1.5;
    }

    @media (max-width: 1120px) {
      .controls-grid,
      .kpi-grid,
      .main-grid,
      .secondary-grid,
      .sql-grid,
      .summary-grid,
      .query-card-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>
  <div class="page-shell">
    <section class="hero">
      <div class="eyebrow">SQL-first companion dashboard</div>
      <h1>Mental Health SQL Comparison Dashboard</h1>
      <p>
        This dashboard is powered by the reusable SQL project queries. It still lets you compare countries directly,
        but the core summaries, tables, and headline metrics all come from SQLite result sets built from the same merged panel as the notebooks.
      </p>
      <div class="hero-meta" id="heroMeta"></div>
    </section>

    <section class="panel">
      <h2>Controls</h2>
      <p class="section-copy">
        Use the filters to change the country-comparison views. The SQL summary sections below remain anchored to the reusable query outputs from the SQL project.
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
      <h2>SQL Headline Cards</h2>
      <p class="section-copy">
        These pull from the query outputs and the SQL-loaded panel so you can get the project story quickly before drilling into countries.
      </p>
      <div class="kpi-grid" id="kpiGrid"></div>
    </section>

    <div class="main-grid">
      <section class="panel">
        <h2>Country Trend Comparison</h2>
        <p class="chart-caption">
          This uses the SQL-loaded panel table for head-to-head country trends on the selected metric, with a scope mean as a reference line.
        </p>
        <div class="chart-shell" id="trendChart"></div>
      </section>

      <section class="panel">
        <h2>Snapshot Comparison</h2>
        <p class="chart-caption">
          Selected countries are compared on the chosen snapshot year, and the recent profile band is pulled from the SQL classification logic.
        </p>
        <div id="comparisonTable"></div>
        <div id="recentProfileCards" style="margin-top: 14px;"></div>
      </section>
    </div>

    <div class="secondary-grid">
      <section class="panel">
        <h2>Snapshot Ranking</h2>
        <p class="chart-caption">
          This ranking comes from the SQL-loaded country-year table and updates instantly with the current year, continent, and metric selections.
        </p>
        <div class="chart-shell" id="rankingChart"></div>
      </section>

      <section class="panel">
        <h2>Burden vs Prevalence</h2>
        <p class="chart-caption">
          Use this to see where selected countries sit relative to the rest of the current scope on mental prevalence and DALY burden.
        </p>
        <div class="chart-shell" id="scatterChart"></div>
      </section>
    </div>

    <div class="sql-grid">
      <section class="panel">
        <h2>Global Trend Query</h2>
        <p class="chart-caption">
          This chart comes directly from the reusable SQL query for yearly global prevalence trends.
        </p>
        <div class="chart-shell" id="globalTrendChart"></div>
      </section>

      <section class="panel">
        <h2>Reusable SQL Highlights</h2>
        <p class="chart-caption">
          These small cards summarize the top rows from the most interview-friendly SQL queries in the companion project.
        </p>
        <div class="query-card-grid" id="queryHighlights"></div>
      </section>
    </div>

    <div class="summary-grid">
      <section class="panel">
        <h2>Continent Summary Query</h2>
        <p class="chart-caption">
          The continent table below is the same 2019 regional summary built in the SQL project.
        </p>
        <div id="continentSummary"></div>
      </section>

      <section class="panel">
        <h2>Profile Bands and Burden Quintiles</h2>
        <p class="chart-caption">
          These sections come from the SQL classification and window-function style outputs.
        </p>
        <div id="profileBands"></div>
        <div class="mini-note">
          The burden quintile table from the SQL project helps show whether a country sits in the top or bottom burden tier when you cross-check it against the comparison views above.
        </div>
        <div id="quintileTable" style="margin-top: 14px;"></div>
      </section>
    </div>

    <section class="panel">
      <h2>Window Function Result</h2>
      <p class="chart-caption">
        This is the rolling-average SQL query output, useful for spotting countries that moved furthest above their recent three-year baseline.
      </p>
      <div id="rollingTable"></div>
      <div class="footer-note" id="footerNote"></div>
    </section>
  </div>

  <script id="dashboard-data" type="application/json">__DATA_JSON__</script>
  <script>
    const payload = JSON.parse(document.getElementById("dashboard-data").textContent);
    const records = payload.panel;
    const recentProfiles = payload.recent_profiles;
    const queryResults = payload.query_results;
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
      mint: "#65c3ba",
      amber: "#d8a84d",
      rose: "#f07f74",
      ice: "#8cb8ff",
      ink: "#f3f0e8",
      muted: "#a4b0bd",
      line: "rgba(196, 211, 226, 0.14)",
      grid: "rgba(196, 211, 226, 0.08)",
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

    function makeOptionMarkup(values, selectedValue) {
      return values
        .map((value) => {
          const selected = value === selectedValue ? " selected" : "";
          return `<option value="${escapeHtml(value)}"${selected}>${escapeHtml(value)}</option>`;
        })
        .join("");
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
        .map((row) => ({ x: row.Year, y: Number(row[metric]) }))
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

    function renderHero() {
      document.getElementById("heroMeta").innerHTML = [
        `<div class="hero-chip"><strong>${formatInt.format(summary.countries)}</strong> countries</div>`,
        `<div class="hero-chip"><strong>${formatInt.format(summary.rows)}</strong> country-year rows</div>`,
        `<div class="hero-chip"><strong>${summary.start_year}-${summary.end_year}</strong> SQL comparison window</div>`,
        `<div class="hero-chip"><strong>${Object.keys(queryResults).length}</strong> reusable query blocks</div>`,
      ].join("");
      document.getElementById("footerNote").textContent =
        "SQL dashboard generated at " + summary.generated_at + ".";
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
          ? `Snapshot scope: all countries in ${state.year}.`
          : `Snapshot scope: ${state.continent} countries in ${state.year}.`;
      document.getElementById("scopeNote").textContent =
        scopeText + " All headline summary cards below are grounded in the SQL query outputs.";
    }

    function renderKpis() {
      const scopeRows = getScopeRows();
      const global2019 = queryResults.global_yearly_prevalence_trend.slice(-1)[0];
      const biggestIncrease = queryResults.countries_with_the_largest_change_in_mental_prevalence_from_1990_to_2019[0];
      const widestGap = queryResults.highest_depression_gender_gaps_in_2019[0];
      const topBurden = queryResults.daly_burden_ranking_in_2019[0];

      const cards = [
        {
          label: "Countries in scope",
          value: formatInt.format(scopeRows.length),
          footnote: "Filtered from the SQL-loaded country-year table.",
        },
        {
          label: "2019 weighted mental prev",
          value: formatMetric("mental_prev", global2019.weighted_mental_prev),
          footnote: "From the global yearly prevalence trend SQL query.",
        },
        {
          label: "Largest 1990-2019 increase",
          value: biggestIncrease.Entity,
          footnote: formatMetric("mental_prev", biggestIncrease.abs_change) + " absolute change from the SQL country-change query.",
        },
        {
          label: "Widest 2019 depression gap",
          value: widestGap.Entity,
          footnote: formatMetric("depression_gender_gap", widestGap.depression_gender_gap) + " from the SQL gender-gap ranking.",
        },
        {
          label: "Highest 2019 burden ratio",
          value: topBurden.Entity,
          footnote: "Burden ratio " + formatMetric("burden_ratio", topBurden.burden_ratio) + " from the SQL burden ranking.",
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
      const margin = { top: 18, right: 20, bottom: 48, left: 62 };
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
          <text x="${margin.left - 12}" y="${y + 4}" text-anchor="end" font-size="11" fill="${colors.muted}">
            ${escapeHtml(formatNumber.format(value))}
          </text>
        `;
      }).join("");

      const xAxisLabels = xTicks
        .map((year) => {
          const x = scaleX(year);
          return `
            <line x1="${x}" y1="${height - margin.bottom}" x2="${x}" y2="${height - margin.bottom + 6}" stroke="${colors.line}" />
            <text x="${x}" y="${height - margin.bottom + 22}" text-anchor="middle" font-size="11" fill="${colors.muted}">
              ${year}
            </text>
          `;
        })
        .join("");

      const paths = series
        .map((entry) => {
          const dash = entry.dashed ? ' stroke-dasharray="7 6"' : "";
          const polyline = entry.points.map((point) => `${scaleX(point.x)},${scaleY(point.y)}`).join(" ");
          const circles = entry.points
            .map(
              (point) =>
                `<circle cx="${scaleX(point.x)}" cy="${scaleY(point.y)}" r="3.2" fill="${entry.color}" opacity="0.92"></circle>`
            )
            .join("");
          return `
            <polyline fill="none" stroke="${entry.color}" stroke-width="3"${dash} points="${polyline}"></polyline>
            ${circles}
          `;
        })
        .join("");

      container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" width="100%" height="100%" role="img" aria-label="${escapeHtml(yLabel)} line chart">
          ${gridLines}
          <line x1="${margin.left}" y1="${height - margin.bottom}" x2="${width - margin.right}" y2="${height - margin.bottom}" stroke="${colors.line}" />
          <line x1="${margin.left}" y1="${margin.top}" x2="${margin.left}" y2="${height - margin.bottom}" stroke="${colors.line}" />
          ${xAxisLabels}
          ${paths}
          <text x="${width / 2}" y="${height - 10}" text-anchor="middle" font-size="12" fill="${colors.muted}">Year</text>
          <text x="18" y="${height / 2}" transform="rotate(-90 18 ${height / 2})" text-anchor="middle" font-size="12" fill="${colors.muted}">
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
      const height = 48 + topRows.length * rowHeight;
      const margin = { top: 12, right: 20, bottom: 18, left: 190 };
      const maxValue = Math.max(...topRows.map((row) => Number(row[metric]) || 0), 0.001);
      const scaleX = (value) =>
        margin.left + (Number(value) / maxValue) * (width - margin.left - margin.right);

      const bars = topRows
        .map((row, index) => {
          const y = margin.top + index * rowHeight;
          const selected = row.Entity === state.countryA || row.Entity === state.countryB;
          const color = row.Entity === state.countryA ? colors.mint : row.Entity === state.countryB ? colors.rose : colors.ice;
          const barWidth = scaleX(row[metric]) - margin.left;
          return `
            <text x="${margin.left - 12}" y="${y + 18}" text-anchor="end" font-size="12" fill="${colors.ink}" font-weight="${selected ? 700 : 500}">
              ${escapeHtml(row.Entity)}
            </text>
            <rect x="${margin.left}" y="${y + 4}" width="${barWidth}" height="18" rx="9" fill="${color}" opacity="${selected ? 1 : 0.72}"></rect>
            <text x="${scaleX(row[metric]) + 8}" y="${y + 18}" font-size="12" fill="${colors.muted}">
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
      const margin = { top: 16, right: 20, bottom: 48, left: 60 };
      let xMin = Math.min(...points.map((point) => point.x)) - 0.4;
      let xMax = Math.max(...points.map((point) => point.x)) + 0.4;
      let yMin = Math.min(...points.map((point) => point.y)) - 0.4;
      let yMax = Math.max(...points.map((point) => point.y)) + 0.4;

      const scaleX = (value) =>
        margin.left + ((value - xMin) / (xMax - xMin || 1)) * (width - margin.left - margin.right);
      const scaleY = (value) =>
        height - margin.bottom - ((value - yMin) / (yMax - yMin || 1)) * (height - margin.top - margin.bottom);

      const xMean = averageValue(rows, "mental_prev");
      const yMean = averageValue(rows, "daly_share");

      const dots = points
        .map((point) => {
          const selected = point.name === state.countryA || point.name === state.countryB;
          const color = point.name === state.countryA ? colors.mint : point.name === state.countryB ? colors.rose : colors.ice;
          const radius = selected ? 6 : 3.8;
          const opacity = selected ? 1 : 0.42;
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
          ${dots}
          <text x="${width / 2}" y="${height - 10}" text-anchor="middle" font-size="12" fill="${colors.muted}">Mental prevalence (%)</text>
          <text x="18" y="${height / 2}" transform="rotate(-90 18 ${height / 2})" text-anchor="middle" font-size="12" fill="${colors.muted}">
            DALY share (%)
          </text>
        </svg>
        <div class="legend">
          <span class="legend-item"><span class="legend-swatch" style="background:${colors.mint};"></span>${escapeHtml(state.countryA)}</span>
          <span class="legend-item"><span class="legend-swatch" style="background:${colors.rose};"></span>${escapeHtml(state.countryB)}</span>
          <span class="legend-item"><span class="legend-swatch" style="background:${colors.ice};"></span>Other countries in scope</span>
        </div>
      `;
    }

    function renderComparisonTable() {
      const snapshotRows = records.filter((row) => row.Year === state.year);
      const left = snapshotRows.find((row) => row.Entity === state.countryA);
      const right = snapshotRows.find((row) => row.Entity === state.countryB);
      const leftProfile = recentProfiles.find((row) => row.Entity === state.countryA);
      const rightProfile = recentProfiles.find((row) => row.Entity === state.countryB);

      const metrics = [
        ["continent", "Continent"],
        ["mental_prev", "Mental prevalence"],
        ["depression_prev", "Depression prevalence"],
        ["daly_share", "DALY share"],
        ["depression_gender_gap", "Depression gap"],
        ["burden_ratio", "Burden ratio"],
        ["profile_band", "Recent profile band"],
      ];

      const rows = metrics
        .map(([key, label]) => {
          const leftValue =
            key === "continent"
              ? left?.continent ?? "n/a"
              : key === "profile_band"
                ? leftProfile?.profile_band ?? "n/a"
                : formatMetric(key, left?.[key]);
          const rightValue =
            key === "continent"
              ? right?.continent ?? "n/a"
              : key === "profile_band"
                ? rightProfile?.profile_band ?? "n/a"
                : formatMetric(key, right?.[key]);
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
      const selectedProfiles = recentProfiles.filter(
        (row) => row.Entity === state.countryA || row.Entity === state.countryB
      );

      document.getElementById("recentProfileCards").innerHTML = selectedProfiles
        .map(
          (profile) => `
            <div class="profile-card">
              <h3 class="profile-title">${escapeHtml(profile.Entity)} · ${escapeHtml(profile.profile_band)}</h3>
              <div class="profile-grid">
                <div class="profile-metric">
                  <span>2015-2019 Mental Prev</span>
                  <strong>${escapeHtml(formatMetric("mental_prev", profile.avg_mental_prev))}</strong>
                </div>
                <div class="profile-metric">
                  <span>2015-2019 DALY Share</span>
                  <strong>${escapeHtml(formatMetric("daly_share", profile.avg_daly_share))}</strong>
                </div>
                <div class="profile-metric">
                  <span>Avg Depression Gap</span>
                  <strong>${escapeHtml(formatMetric("depression_gender_gap", profile.avg_depression_gap))}</strong>
                </div>
                <div class="profile-metric">
                  <span>Continent</span>
                  <strong>${escapeHtml(profile.continent ?? "n/a")}</strong>
                </div>
              </div>
            </div>
          `
        )
        .join("");
    }

    function renderGlobalTrend() {
      const globalRows = queryResults.global_yearly_prevalence_trend.map((row) => ({
        Year: Number(row.Year),
        avg_mental_prev: Number(row.avg_mental_prev),
        weighted_mental_prev: Number(row.weighted_mental_prev),
        avg_depression_prev: Number(row.avg_depression_prev),
      }));

      renderLineChart("globalTrendChart", [
        {
          name: "Country mean mental prevalence",
          color: colors.ice,
          points: globalRows.map((row) => ({ x: row.Year, y: row.avg_mental_prev })),
        },
        {
          name: "Population-weighted mental prevalence",
          color: colors.amber,
          points: globalRows.map((row) => ({ x: row.Year, y: row.weighted_mental_prev })),
        },
        {
          name: "Country mean depression prevalence",
          color: colors.mint,
          points: globalRows.map((row) => ({ x: row.Year, y: row.avg_depression_prev })),
        },
      ], "Global prevalence (%)");
    }

    function renderQueryHighlights() {
      const biggestIncrease = queryResults.countries_with_the_largest_change_in_mental_prevalence_from_1990_to_2019.slice(0, 3);
      const widestGap = queryResults.highest_depression_gender_gaps_in_2019.slice(0, 3);
      const highestBurden = queryResults.daly_burden_ranking_in_2019.slice(0, 3);

      const cards = [
        {
          title: "Largest prevalence increases",
          rows: biggestIncrease.map((row) => `${row.Entity}: ${formatMetric("mental_prev", row.abs_change)}`),
        },
        {
          title: "Widest 2019 depression gaps",
          rows: widestGap.map((row) => `${row.Entity}: ${formatMetric("depression_gender_gap", row.depression_gender_gap)}`),
        },
        {
          title: "Highest 2019 burden ratios",
          rows: highestBurden.map((row) => `${row.Entity}: ${formatMetric("burden_ratio", row.burden_ratio)}`),
        },
      ];

      document.getElementById("queryHighlights").innerHTML = cards
        .map(
          (card) => `
            <div class="query-card">
              <h3 class="query-title">${escapeHtml(card.title)}</h3>
              <ul>${card.rows.map((row) => `<li>${escapeHtml(row)}</li>`).join("")}</ul>
            </div>
          `
        )
        .join("");
    }

    function renderSimpleTable(containerId, rows, columns) {
      const container = document.getElementById(containerId);
      const head = columns.map((column) => `<th>${escapeHtml(column.label)}</th>`).join("");
      const body = rows
        .map((row) => {
          const cells = columns
            .map((column) => {
              const value = typeof column.render === "function" ? column.render(row) : row[column.key];
              return `<td>${escapeHtml(value)}</td>`;
            })
            .join("");
          return `<tr>${cells}</tr>`;
        })
        .join("");

      container.innerHTML = `
        <div class="table-wrap">
          <table>
            <thead><tr>${head}</tr></thead>
            <tbody>${body}</tbody>
          </table>
        </div>
      `;
    }

    function renderContinentSummary() {
      renderSimpleTable(
        "continentSummary",
        queryResults.continent_summary_for_2019,
        [
          { key: "continent", label: "Continent" },
          { key: "countries", label: "Countries", render: (row) => formatInt.format(row.countries) },
          { key: "avg_mental_prev", label: "Avg Mental Prev", render: (row) => formatMetric("mental_prev", row.avg_mental_prev) },
          { key: "avg_depression_gap", label: "Avg Depression Gap", render: (row) => formatMetric("depression_gender_gap", row.avg_depression_gap) },
          { key: "avg_daly_share", label: "Avg DALY Share", render: (row) => formatMetric("daly_share", row.avg_daly_share) },
        ]
      );
    }

    function renderProfileBands() {
      document.getElementById("profileBands").innerHTML = queryResults.recent_profile_classification_for_2015_to_2019
        .map(
          (row) => `
            <div class="profile-card">
              <h3 class="profile-title">${escapeHtml(row.profile_band)}</h3>
              <div class="profile-grid">
                <div class="profile-metric">
                  <span>Countries</span>
                  <strong>${escapeHtml(formatInt.format(row.countries))}</strong>
                </div>
                <div class="profile-metric">
                  <span>Avg Mental Prev</span>
                  <strong>${escapeHtml(formatMetric("mental_prev", row.avg_mental_prev))}</strong>
                </div>
                <div class="profile-metric">
                  <span>Avg DALY Share</span>
                  <strong>${escapeHtml(formatMetric("daly_share", row.avg_daly_share))}</strong>
                </div>
                <div class="profile-metric">
                  <span>Avg Depression Gap</span>
                  <strong>${escapeHtml(formatMetric("depression_gender_gap", row.avg_depression_gap))}</strong>
                </div>
              </div>
            </div>
          `
        )
        .join("");

      renderSimpleTable(
        "quintileTable",
        queryResults.burden_quintiles_using_ntile,
        [
          { key: "burden_quintile", label: "Quintile" },
          { key: "countries", label: "Countries", render: (row) => formatInt.format(row.countries) },
          { key: "avg_burden_ratio", label: "Avg Ratio", render: (row) => formatMetric("burden_ratio", row.avg_burden_ratio) },
          { key: "min_burden_ratio", label: "Min Ratio", render: (row) => formatMetric("burden_ratio", row.min_burden_ratio) },
          { key: "max_burden_ratio", label: "Max Ratio", render: (row) => formatMetric("burden_ratio", row.max_burden_ratio) },
        ]
      );
    }

    function renderRollingTable() {
      renderSimpleTable(
        "rollingTable",
        queryResults.rolling_3_year_average_with_window_functions.slice(0, 12),
        [
          { key: "Entity", label: "Country" },
          { key: "Year", label: "Year" },
          { key: "mental_prev", label: "Mental Prev", render: (row) => formatMetric("mental_prev", row.mental_prev) },
          { key: "mental_prev_3yr_avg", label: "3yr Avg", render: (row) => formatMetric("mental_prev", row.mental_prev_3yr_avg) },
          { key: "deviation_from_recent_avg", label: "Deviation", render: (row) => formatMetric("mental_prev", row.deviation_from_recent_avg) },
        ]
      );
    }

    function renderCountryViews() {
      const trendSeries = [
        {
          name: state.continent === "All" ? "Global mean" : `${state.continent} mean`,
          color: colors.amber,
          dashed: true,
          points: getScopeTrend(state.metric),
        },
        {
          name: state.countryA,
          color: colors.mint,
          points: getCountrySeries(state.countryA, state.metric),
        },
        {
          name: state.countryB,
          color: colors.rose,
          points: getCountrySeries(state.countryB, state.metric),
        },
      ].filter((entry) => entry.points.length);

      renderLineChart("trendChart", trendSeries, metricLabels[state.metric]);

      const rankedRows = getScopeRows()
        .slice()
        .sort((left, right) => Number(right[state.metric]) - Number(left[state.metric]));
      renderBarChart("rankingChart", rankedRows, state.metric);
      renderScatterChart("scatterChart", getScopeRows());
      renderComparisonTable();
      renderRecentProfiles();
    }

    function renderAll() {
      renderControls();
      renderKpis();
      renderCountryViews();
      renderGlobalTrend();
      renderQueryHighlights();
      renderContinentSummary();
      renderProfileBands();
      renderRollingTable();
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


def build_sql_dashboard():
    payload = build_sql_dashboard_payload()
    data_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = HTML_TEMPLATE.replace("__DATA_JSON__", data_json)
    OUTPUT_PATH.write_text(html, encoding="utf-8")
    return OUTPUT_PATH


if __name__ == "__main__":
    built_path = build_sql_dashboard()
    print(f"Built {built_path}")
