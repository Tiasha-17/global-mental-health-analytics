-- Mental Health SQL Companion Project
-- Expected table name: mental_health_panel
-- The companion sql_analysis.ipynb notebook builds this table in SQLite.
--
-- Suggested core columns:
-- Entity, Code, Year, continent, population, mental_prev, depression_prev,
-- daly_share, depression_male_prev, depression_female_prev,
-- depression_gender_gap, burden_ratio, schizophrenia_prev, bipolar_prev,
-- eating_prev, anxiety_prev, drug_prev, alcohol_prev

-- 1. Global yearly prevalence trend
SELECT
    Year,
    AVG(mental_prev) AS avg_mental_prev,
    SUM(mental_prev * population) / SUM(population) AS weighted_mental_prev,
    AVG(depression_prev) AS avg_depression_prev
FROM mental_health_panel
GROUP BY Year
ORDER BY Year;

-- 2. Countries with the largest change in mental prevalence from 1990 to 2019
WITH base AS (
    SELECT
        Entity,
        Code,
        MAX(CASE WHEN Year = 1990 THEN mental_prev END) AS mental_prev_1990,
        MAX(CASE WHEN Year = 2019 THEN mental_prev END) AS mental_prev_2019
    FROM mental_health_panel
    GROUP BY Entity, Code
)
SELECT
    Entity,
    Code,
    mental_prev_1990,
    mental_prev_2019,
    mental_prev_2019 - mental_prev_1990 AS abs_change,
    100.0 * (mental_prev_2019 - mental_prev_1990) / mental_prev_1990 AS pct_change
FROM base
WHERE mental_prev_1990 IS NOT NULL
  AND mental_prev_2019 IS NOT NULL
ORDER BY abs_change DESC;

-- 3. Highest prevalence countries in 2019
SELECT
    Entity,
    continent,
    mental_prev,
    depression_prev,
    daly_share
FROM mental_health_panel
WHERE Year = 2019
ORDER BY mental_prev DESC
LIMIT 15;

-- 4. Highest depression gender gaps in 2019
SELECT
    Entity,
    continent,
    depression_male_prev,
    depression_female_prev,
    depression_gender_gap
FROM mental_health_panel
WHERE Year = 2019
ORDER BY depression_gender_gap DESC
LIMIT 15;

-- 5. Continent summary for 2019
SELECT
    continent,
    COUNT(DISTINCT Code) AS countries,
    AVG(mental_prev) AS avg_mental_prev,
    AVG(depression_gender_gap) AS avg_depression_gap,
    AVG(daly_share) AS avg_daly_share
FROM mental_health_panel
WHERE Year = 2019
GROUP BY continent
ORDER BY avg_depression_gap DESC;

-- 6. DALY burden ranking in 2019
SELECT
    Entity,
    continent,
    mental_prev,
    daly_share,
    burden_ratio
FROM mental_health_panel
WHERE Year = 2019
ORDER BY burden_ratio DESC
LIMIT 15;

-- 7. Rolling 3-year average with window functions
WITH rolling AS (
    SELECT
        Entity,
        Code,
        Year,
        mental_prev,
        AVG(mental_prev) OVER (
            PARTITION BY Code
            ORDER BY Year
            ROWS BETWEEN 2 PRECEDING AND CURRENT ROW
        ) AS mental_prev_3yr_avg
    FROM mental_health_panel
)
SELECT
    Entity,
    Year,
    mental_prev,
    mental_prev_3yr_avg,
    mental_prev - mental_prev_3yr_avg AS deviation_from_recent_avg
FROM rolling
WHERE Year >= 2015
ORDER BY deviation_from_recent_avg DESC
LIMIT 20;

-- 8. Burden quintiles using NTILE
WITH burden AS (
    SELECT
        Entity,
        Code,
        continent,
        burden_ratio
    FROM mental_health_panel
    WHERE Year = 2019
),
bucketed AS (
    SELECT
        *,
        NTILE(5) OVER (ORDER BY burden_ratio DESC) AS burden_quintile
    FROM burden
)
SELECT
    burden_quintile,
    COUNT(*) AS countries,
    AVG(burden_ratio) AS avg_burden_ratio,
    MIN(burden_ratio) AS min_burden_ratio,
    MAX(burden_ratio) AS max_burden_ratio
FROM bucketed
GROUP BY burden_quintile
ORDER BY burden_quintile;

-- 9. Recent profile classification for 2015 to 2019
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
),
scored AS (
    SELECT
        *,
        CASE
            WHEN avg_mental_prev >= 15 AND avg_daly_share >= 7 THEN 'High prevalence / High burden'
            WHEN avg_mental_prev >= 15 AND avg_daly_share < 7 THEN 'High prevalence / Lower burden'
            WHEN avg_mental_prev < 15 AND avg_daly_share >= 7 THEN 'Lower prevalence / High burden'
            ELSE 'Lower prevalence / Lower burden'
        END AS profile_band
    FROM recent
)
SELECT
    profile_band,
    COUNT(*) AS countries,
    AVG(avg_mental_prev) AS avg_mental_prev,
    AVG(avg_daly_share) AS avg_daly_share,
    AVG(avg_depression_gap) AS avg_depression_gap
FROM scored
GROUP BY profile_band
ORDER BY countries DESC;
