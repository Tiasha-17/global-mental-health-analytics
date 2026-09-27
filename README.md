# Global Mental Health — Prevalence, Burden & Forecasting

A country-year panel covering 202 countries from 1990 to 2019, built from six public health datasets, with forecasting benchmarks, clustering, a SQL companion analysis and two generated dashboards.

```bash
pip install -r requirements.txt
python src/build_dashboard.py && open dashboards/mental_health_dashboard.html
```

---

## What it does

Six separate prevalence and burden tables are merged into one analytical panel (6,060 country-year rows, 27 columns), then used to answer questions that no single source table can answer on its own: how prevalence translates into disease burden, where gender gaps are widest, and whether country trajectories are forecastable.

## Findings

| Metric | Value |
|---|---|
| Panel size | 6,060 country-years, 202 countries, 1990–2019 |
| Mean mental-disorder prevalence | 13.33% |
| Mean depressive-disorder prevalence | 3.95% |
| Mean DALY share from mental disorders | 4.77% |
| Mean depression gender gap (F−M) | 1.56 pp |
| Population-weighted prevalence, 2019 | 13.06% |

**Stable global averages hide large country-level movement.** Country-mean prevalence moved from 13.32% to 13.29% across three decades — essentially flat. Underneath, the United States rose 1.38 pp while Bangladesh fell 1.70 pp.

**Prevalence is a poor proxy for burden.** Eating disorder prevalence correlates with DALY share at 0.714, higher than total mental-disorder prevalence at 0.573. Disorder mix matters more than headline prevalence, which means prioritising countries by prevalence alone would misallocate attention.

**The persistence baseline wins.** A one-step "next year equals this year" forecast scored RMSE 0.0419 against Random Forest at 0.0433 and HistGradientBoosting at 0.0570. The series is smooth and slow-moving, so the naive baseline is genuinely hard to beat — and reporting the ML models as successes without this benchmark would have been misleading.

**Two clusters, cleanly separated.** Silhouette analysis selected k=2: 74 higher-burden countries (15.34% prevalence, 7.62% DALY share) against 128 lower-burden ones (12.09%, 4.08%).

## Why the baseline matters

This is the finding I would lead with in an interview. It would have been easy to report "Random Forest achieved R² 0.9995" and leave it there. That number is real, and it is also meaningless without the persistence comparison — the R² is high because the underlying series barely moves year to year, not because the model learned anything useful.

Running the naive baseline first is what made the result interpretable. Any forecasting work that follows should be measured against 0.0419, not against zero.

## Engineering decisions

**Panel construction is a reusable module.** `src/mental_health_panel.py` builds the merged panel once and is imported by both dashboard generators, so the analysis and the dashboards cannot drift apart.

**Paths resolve from `__file__`.** The module finds `data/` regardless of where the interpreter was launched.

**A SQL companion, not a rewrite.** `sql/queries.sql` answers the same questions using window functions, `NTILE` for burden quintiles and `CASE` for profile classification. Same results, different engine — useful for demonstrating the analysis translates to a database context.

**Self-contained HTML dashboards.** Both dashboards are generated files with no server dependency, so they open directly in a browser.

## Tech stack

Python · pandas · NumPy · scikit-learn · SQLite · matplotlib · seaborn · HTML/CSS/JS

## Repository layout

```
├── src/
│   ├── mental_health_panel.py   # Shared panel construction
│   ├── build_dashboard.py
│   └── build_sql_dashboard.py
├── notebooks/
│   ├── 01_analysis.ipynb        # Trends, gender gaps, forecasting, clustering
│   └── 02_sql_analysis.ipynb    # SQL companion
├── sql/queries.sql
├── dashboards/                  # Generated, self-contained HTML
├── data/                        # Six source CSVs
└── PRESENTATION_SCRIPT.md
```

Notebooks are committed **with outputs**, so the analysis is readable on GitHub without running anything.

## Running it

```bash
pip install -r requirements.txt

jupyter notebook notebooks/01_analysis.ipynb
jupyter notebook notebooks/02_sql_analysis.ipynb

python src/build_dashboard.py
python src/build_sql_dashboard.py
```

## Limitations

- The source bundle has no GDP, income or schooling data, so the intermediate model uses structural proxies (year, log population, continent, gender gap) rather than genuine socioeconomic predictors. It reaches R² 0.744, which is a ceiling imposed by the available features.
- Forecasting is one-step-ahead only.
- The analysis is descriptive and predictive. It does not establish causal drivers.
- Prevalence estimates are themselves modelled figures from the source, not direct measurements, and cross-country differences partly reflect differences in diagnosis and reporting rather than differences in underlying rates.

## What I would do next

- Enrich the panel with GDP per capita, education and unemployment
- Test multi-year forecast horizons where persistence should weaken
- Move the SQL layer to a persistent Postgres workflow

## Data source

[Our World in Data — Mental Health](https://ourworldindata.org/mental-health), built on IHME Global Burden of Disease estimates.

## Licence

MIT
