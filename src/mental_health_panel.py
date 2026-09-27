import os
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


START_YEAR = 1990
END_YEAR = 2019
RECENT_START_YEAR = 2015


# Keep the sklearn clustering step quiet on systems where joblib cannot read
# the physical core count from the OS.
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")


DISORDER_RENAME_MAP = {
    "Prevalence - Schizophrenia - Sex: Both - Age: Age-standardized (Percent)": "schizophrenia_prev",
    "Prevalence - Bipolar disorder - Sex: Both - Age: Age-standardized (Percent)": "bipolar_prev",
    "Prevalence - Eating disorders - Sex: Both - Age: Age-standardized (Percent)": "eating_prev",
    "Prevalence - Anxiety disorders - Sex: Both - Age: Age-standardized (Percent)": "anxiety_prev",
    "Prevalence - Drug use disorders - Sex: Both - Age: Age-standardized (Percent)": "drug_prev",
    "Prevalence - Depressive disorders - Sex: Both - Age: Age-standardized (Percent)": "depressive_prev",
    "Prevalence - Alcohol use disorders - Sex: Both - Age: Age-standardized (Percent)": "alcohol_prev",
}


RECENT_METRICS = [
    "mental_prev",
    "depression_prev",
    "anxiety_prev",
    "alcohol_prev",
    "drug_prev",
    "eating_prev",
    "schizophrenia_prev",
    "bipolar_prev",
    "daly_share",
    "depression_gender_gap",
]


def _resolve_base_dir(base_dir=None):
    if base_dir is None:
        return Path(__file__).resolve().parent.parent / "data"
    return Path(base_dir).resolve()


def keep_countries(df):
    # Keep the same time window used in the notebooks.
    filtered = df[df["Year"].between(START_YEAR, END_YEAR)].copy()
    code = filtered["Code"].astype(str)
    # Drop OWID rollups so the panel stays country-level.
    return filtered[filtered["Code"].notna() & ~code.str.startswith("OWID_")].copy()


def load_source_tables(base_dir=None):
    root = _resolve_base_dir(base_dir)
    return {
        "mental_total": pd.read_csv(root / "share-with-mental-and-substance-disorders.csv"),
        "depression_total": pd.read_csv(root / "share-with-depression.csv"),
        "daly_share": pd.read_csv(root / "mental-and-substance-use-as-share-of-disease.csv"),
        "disorder_breakdown": pd.read_csv(root / "prevalence-by-mental-and-substance-use-disorder.csv"),
        "depression_by_sex": pd.read_csv(root / "prevalence-of-depression-males-vs-females.csv"),
        "mental_by_sex": pd.read_csv(root / "share-with-mental-or-substance-disorders-by-sex.csv"),
    }


def build_mental_health_panel(base_dir=None):
    raw_tables = load_source_tables(base_dir)

    mental = keep_countries(raw_tables["mental_total"]).rename(
        columns={
            "Prevalence - Mental disorders - Sex: Both - Age: Age-standardized (Percent)": "mental_prev",
        }
    )
    depression = keep_countries(raw_tables["depression_total"]).rename(
        columns={
            "Prevalence - Depressive disorders - Sex: Both - Age: Age-standardized (Percent)": "depression_prev",
        }
    )
    daly = keep_countries(raw_tables["daly_share"]).rename(
        columns={
            "DALYs (Disability-Adjusted Life Years) - Mental disorders - Sex: Both - Age: All Ages (Percent)": "daly_share",
        }
    )
    disorders = keep_countries(raw_tables["disorder_breakdown"]).rename(columns=DISORDER_RENAME_MAP)
    depression_by_sex = keep_countries(raw_tables["depression_by_sex"]).rename(
        columns={
            "Prevalence - Depressive disorders - Sex: Male - Age: Age-standardized (Percent)": "depression_male_prev",
            "Prevalence - Depressive disorders - Sex: Female - Age: Age-standardized (Percent)": "depression_female_prev",
            "Population (historical estimates)": "population",
            "Continent": "continent",
        }
    )
    mental_by_sex = keep_countries(raw_tables["mental_by_sex"]).rename(
        columns={
            "Prevalence - Mental and substance use disorders - Sex: Male - Age: Age-standardized (Percent)": "mental_male_prev",
            "Prevalence - Mental and substance use disorders - Sex: Female - Age: Age-standardized (Percent)": "mental_female_prev",
            "Population (historical estimates)": "population_from_total",
            "Continent": "continent_from_total",
        }
    )

    continent_map = pd.concat(
        [
            depression_by_sex[["Code", "continent"]],
            mental_by_sex[["Code", "continent_from_total"]].rename(
                columns={"continent_from_total": "continent"}
            ),
        ],
        ignore_index=True,
    )
    continent_map = continent_map.dropna().drop_duplicates(subset=["Code"])

    panel = mental[["Entity", "Code", "Year", "mental_prev"]].copy()
    panel = panel.merge(
        depression[["Entity", "Code", "Year", "depression_prev"]],
        on=["Entity", "Code", "Year"],
        how="inner",
    )
    panel = panel.merge(
        daly[["Entity", "Code", "Year", "daly_share"]],
        on=["Entity", "Code", "Year"],
        how="inner",
    )
    panel = panel.merge(
        disorders[
            [
                "Entity",
                "Code",
                "Year",
                "schizophrenia_prev",
                "bipolar_prev",
                "eating_prev",
                "anxiety_prev",
                "drug_prev",
                "depressive_prev",
                "alcohol_prev",
            ]
        ],
        on=["Entity", "Code", "Year"],
        how="inner",
    )
    panel = panel.merge(
        depression_by_sex[
            [
                "Entity",
                "Code",
                "Year",
                "depression_male_prev",
                "depression_female_prev",
                "population",
            ]
        ],
        on=["Entity", "Code", "Year"],
        how="left",
    )
    panel = panel.merge(
        mental_by_sex[["Entity", "Code", "Year", "mental_male_prev", "mental_female_prev"]],
        on=["Entity", "Code", "Year"],
        how="left",
    )
    panel = panel.merge(continent_map, on="Code", how="left")

    panel["depression_gender_gap"] = (
        panel["depression_female_prev"] - panel["depression_male_prev"]
    )
    panel["mental_gender_gap"] = panel["mental_female_prev"] - panel["mental_male_prev"]
    panel["log_population"] = np.where(panel["population"] > 0, np.log10(panel["population"]), np.nan)

    # Keep the same derived ratios used in the notebook outputs.
    panel["depression_share_of_total"] = panel["depression_prev"] / panel["mental_prev"]
    panel["substance_share"] = (
        panel["drug_prev"] + panel["alcohol_prev"]
    ) / panel["mental_prev"]
    panel["severe_share"] = (
        panel["schizophrenia_prev"] + panel["bipolar_prev"]
    ) / panel["mental_prev"]
    panel["anxiety_share"] = panel["anxiety_prev"] / panel["mental_prev"]
    panel["burden_ratio"] = panel["daly_share"] / panel["mental_prev"]

    return panel.sort_values(["Entity", "Year"]).reset_index(drop=True)


def build_recent_profile(panel):
    recent_profile = (
        panel[panel["Year"].between(RECENT_START_YEAR, END_YEAR)]
        .groupby(["Entity", "Code", "continent"], as_index=False)
        .agg({metric: "mean" for metric in RECENT_METRICS})
    )

    scaled_recent = StandardScaler().fit_transform(recent_profile[RECENT_METRICS])

    silhouette_rows = []
    with warnings.catch_warnings():
        # These warnings are environment-specific numeric noise on this machine.
        warnings.filterwarnings("ignore", message=".*physical cores.*", category=UserWarning)
        warnings.filterwarnings("ignore", message=".*encountered in matmul.*", category=RuntimeWarning)

        for k in range(2, 7):
            model = KMeans(n_clusters=k, n_init=20, random_state=42)
            labels = model.fit_predict(scaled_recent)
            silhouette_rows.append(
                {
                    "k": k,
                    "silhouette_score": silhouette_score(scaled_recent, labels),
                }
            )

    silhouette_df = pd.DataFrame(silhouette_rows)
    best_k = int(
        silhouette_df.sort_values(["silhouette_score", "k"], ascending=[False, True]).iloc[0]["k"]
    )

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*encountered in matmul.*", category=RuntimeWarning)
        final_model = KMeans(n_clusters=best_k, n_init=30, random_state=42)
        recent_profile["cluster"] = final_model.fit_predict(scaled_recent)

    cluster_summary = (
        recent_profile.groupby("cluster", as_index=False)
        .agg(
            countries=("Code", "nunique"),
            mental_prev=("mental_prev", "mean"),
            depression_prev=("depression_prev", "mean"),
            daly_share=("daly_share", "mean"),
            depression_gender_gap=("depression_gender_gap", "mean"),
        )
        .sort_values("mental_prev")
        .reset_index(drop=True)
    )

    lower_cluster = int(cluster_summary.iloc[0]["cluster"])
    higher_cluster = int(cluster_summary.iloc[-1]["cluster"])
    cluster_labels = {
        lower_cluster: "Lower burden / lower prevalence",
        higher_cluster: "Higher burden / higher prevalence",
    }

    recent_profile["cluster_label"] = recent_profile["cluster"].map(cluster_labels)
    cluster_summary["cluster_label"] = cluster_summary["cluster"].map(cluster_labels)

    return recent_profile, cluster_summary, silhouette_df, best_k


def _frame_to_records(df, digits=4):
    clean = df.copy()
    numeric_cols = clean.select_dtypes(include=["number"]).columns
    clean[numeric_cols] = clean[numeric_cols].round(digits)
    clean = clean.replace({np.nan: None})
    return clean.to_dict(orient="records")


def build_dashboard_payload(base_dir=None):
    panel = build_mental_health_panel(base_dir)
    recent_profile, cluster_summary, silhouette_df, best_k = build_recent_profile(panel)

    cluster_lookup = recent_profile[["Code", "cluster", "cluster_label"]].drop_duplicates(subset=["Code"])
    panel = panel.merge(cluster_lookup, on="Code", how="left")

    dashboard_columns = [
        "Entity",
        "Code",
        "Year",
        "continent",
        "population",
        "mental_prev",
        "depression_prev",
        "daly_share",
        "depression_gender_gap",
        "mental_gender_gap",
        "anxiety_prev",
        "alcohol_prev",
        "drug_prev",
        "eating_prev",
        "schizophrenia_prev",
        "bipolar_prev",
        "burden_ratio",
        "cluster",
        "cluster_label",
    ]

    return {
        "summary": {
            "rows": int(len(panel)),
            "countries": int(panel["Code"].nunique()),
            "start_year": START_YEAR,
            "end_year": END_YEAR,
            "recent_start_year": RECENT_START_YEAR,
            "best_k": best_k,
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
        "panel": _frame_to_records(panel[dashboard_columns]),
        "recent_profile": _frame_to_records(recent_profile),
        "cluster_summary": _frame_to_records(cluster_summary),
        "silhouette": _frame_to_records(silhouette_df),
    }
