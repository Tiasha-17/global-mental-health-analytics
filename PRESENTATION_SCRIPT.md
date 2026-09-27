# Mental Health Project Interview and Presentation Guide

## Project Goal
The goal of this analysis is to understand mental health from four angles:

- global prevalence
- country-level change
- gender disparity
- burden and forecasting

I wanted the project to start with descriptive trend analysis, move into gender and structural modeling, and finish with burden analysis, forecasting, clustering, and a SQL companion.

## Why This Project Matters
For a public-health or policy team, country averages alone are not enough. A useful analysis should help answer:

- whether the global picture is actually changing
- which countries are moving the most
- where female versus male gaps are largest
- which countries carry higher burden relative to prevalence
- how much of the pattern can be explained or forecasted with the data available

## Questions I Answered
### Beginner
- How prevalent are mental disorders globally?
- Which countries changed the most from `1990` to `2019`?
- How do the biggest movers compare over time?

### Intermediate
- Where are depression gender gaps widest?
- Which continents show larger average disparities?
- How well do available structural proxies explain mental prevalence?

### Advanced
- Which forecasting model works best for mental-prevalence prediction?
- Which disorder metrics are most associated with DALY burden?
- How do countries cluster by recent mental-health profile?
- How can the same analysis be framed as a SQL project?

## Dataset Snapshot
- `6` source CSV files
- `6,060` country-year rows in the final panel
- `202` countries
- `1990-2019` analysis window
- Measures include total prevalence, disorder mix, depression by gender, population, continent, and DALY share

## My Approach
1. Load all six files and keep country-only rows in the shared time window.
2. Merge prevalence, DALYs, disorder mix, population, and gender-gap features into one panel.
3. Build beginner trend and country-change analysis.
4. Build intermediate gender-gap analysis and structural-proxy models.
5. Compare forecasting models with lagged features.
6. Relate disorder prevalence to DALY burden.
7. Cluster countries by recent mental-health profile.
8. Rebuild the same panel inside SQLite for the SQL companion notebook.

## Metrics To Explain Clearly
- `mental_prev`: total mental-disorder prevalence
- `depression_gender_gap = female prevalence - male prevalence`
- `burden_ratio = daly_share / mental_prev`
- Forecast metrics: `RMSE`, `MAE`, `R2`
- Cluster comparison: average prevalence and average DALY share by cluster

## 60-Second Version
I built a global mental-health analytics project using Python, Jupyter, and SQL. I merged six country-level datasets into one panel covering 202 countries from 1990 to 2019. First, I showed that global mental-disorder prevalence is fairly stable on average, but some countries changed a lot, including strong increases in the United States, Mexico, and Brazil and large declines in Bangladesh and Myanmar. Then I analyzed gender disparities and found that female depression prevalence is consistently higher than male prevalence, with especially wide gaps in countries such as Gambia and Liberia. Finally, I compared forecasting models, related prevalence to DALY burden, and clustered countries into higher-burden and lower-burden groups. I also built a SQL companion notebook that answers the same questions with reusable queries.

## Key Findings To Mention
- Global mental-disorder prevalence stayed near `13.3%` on average across the period
- The United States, Mexico, Brazil, New Zealand, and Spain showed the largest increases from `1990` to `2019`
- Bangladesh, Myanmar, and Finland showed some of the largest declines
- Female depression prevalence was consistently higher than male prevalence across the panel
- The widest `2019` gender gaps appeared in Gambia, Liberia, Spain, Paraguay, and Greenland
- A structural-proxy Random Forest explained a meaningful share of country variation with `R2` around `0.74`
- In forecasting, the persistence baseline was strongest because prevalence changes slowly year to year
- DALY burden was most strongly associated with eating, anxiety, schizophrenia, bipolar, and total mental prevalence measures
- The clustering step separated countries into a higher-burden group and a lower-burden group

## Recommendations
- Track burden and prevalence together instead of treating them as the same thing
- Monitor female-male gaps as a separate policy metric
- Use persistence as the baseline before applying more complex forecasting models
- Add external socioeconomic indicators in the next version for stronger modeling
- Keep the SQL version because it broadens the project’s interview value

## Limitations To Say Honestly
- The source bundle does not include GDP, income, or education data
- The intermediate model therefore uses structural proxies, not full socioeconomic variables
- The forecasting task is one-step ahead and benefits from smooth series
- The analysis is descriptive and predictive, not causal

## If An Interviewer Asks “What Would You Improve Next?”
- add GDP, schooling, unemployment, or inequality data
- test multi-year and shock-period forecasting
- turn the notebook into a dashboard
- store the SQL version in a persistent database instead of in-memory SQLite

## Strong Closing Line
This project shows that I can take messy public-health data, integrate multiple sources into one country-year panel, answer descriptive and predictive questions clearly, and present the same work in both Python and SQL.
