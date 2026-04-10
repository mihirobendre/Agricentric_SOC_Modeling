"""
VM0042 v2.2 §8.6.1.1.3 — Sampling Error Calculation
=====================================================
Implements Equations 62–64 analytically for stratified random sampling.

Strata = FAO soil type only (3 strata):
  ANm :  9,023.00 ha   61 points  (Lanyuak + Eor Emayian)
  NTh :    333.77 ha   13 points  (Mumberes NTh)
  NTu : 26,012.50 ha  100 points  (Kabianga + Kipsigis + Mumberes NTu)
  Total: 35,369.27 ha  174 points

VM0042 Equations implemented:
  Eq 62:  s²_sampling,Δ,t = Σ_h [ A²_h / (n_h(n_h-1)) * Σ_i (Δ_h,i,t - Δ̄_h,t)² ]
  Eq 63:  s²_Δ̄,t = s²_sampling,Δ,t / A²  +  s²_model
  Eq 64:  s²_model = Σ_h [ (A_h/A)² * s²_model,h ]   (from MVR — set via S2_MODEL below)

Units throughout:
  Δ̂_i,t          tCO2e/ha/yr   (from per-point RothC CSVs)
  s²_sampling,h,t (tCO2e/yr)²  (A²_h scales the within-stratum variance)
  s²_Δ̄,t          (tCO2e/ha/yr)²  (divided by A² in Eq 63)
  s_Δ̄,t           tCO2e/ha/yr
  U%              dimensionless percent

Outputs:
  sampling_error_by_year.csv          — full year-by-year results
  sampling_error_by_stratum_year.csv  — per-stratum variance detail
  sampling_error_summary.csv          — key statistics

Run: python calculate_sampling_error.py
"""

import pandas as pd
import numpy as np
import os

# ---------------------------------------------------------------------------
# 0. Configuration — edit these two values when your MVR is complete
# ---------------------------------------------------------------------------

POINT_RESULTS_DIR = "per_point_results"
SOC_DATA_PATH     = "Kenya_SOC_Data_w_FAO_Soil_Type.csv"
START_YEAR        = 2026
N_YEARS           = 40
T_95              = 1.96   # 95% CI t-value (large-n approximation per VM0042)

# s²_model: area-weighted model prediction variance from your MVR (Eq 64).
# Units: (tCO2e/ha/yr)²
# Set to 0.0 until MVR is complete; replace with the value from Eq 64.
S2_MODEL = 0.0

# ---------------------------------------------------------------------------
# 1. Stratum definitions — soil type only
# ---------------------------------------------------------------------------

STRATA = {
    "ANm":  9_023.00,      # Lanyuak (4,636) + Eor Emayian (4,387)
    "NTh":    333.77,      # Mumberes NTh
    "NTu": 26_012.50,      # Kabianga (15,358) + Kipsigis (9,678) + Mumberes NTu (976.50)
}

TOTAL_AREA_HA = sum(STRATA.values())   # 35,369.27 ha
YEARS         = list(range(START_YEAR, START_YEAR + N_YEARS))

print(f"Project strata (soil type only):")
for soil, area in STRATA.items():
    print(f"  {soil}: {area:>10,.2f} ha")
print(f"  {'TOTAL':}: {TOTAL_AREA_HA:>10,.2f} ha")
print()

# ---------------------------------------------------------------------------
# 2. Load point metadata — assign each point to its soil type stratum
# ---------------------------------------------------------------------------

meta = pd.read_csv(SOC_DATA_PATH)[["Sample_Code", "FAO Soil Type"]].copy()

print("Points per stratum:")
for soil, n in meta.groupby("FAO Soil Type").size().items():
    print(f"  {soil}: {n} points")
print()

# ---------------------------------------------------------------------------
# 3. Load per-point ER time-series
#    Each CSV: one column, N_YEARS rows, values in tCO2e/ha/yr
# ---------------------------------------------------------------------------

print("Loading per-point result CSVs...")
point_data   = {}    # sample_code -> np.array of length N_YEARS
missing_files = []

for sc in meta["Sample_Code"]:
    path = os.path.join(POINT_RESULTS_DIR, f"{sc}.csv")
    if not os.path.exists(path):
        missing_files.append(sc)
        continue
    vals = pd.read_csv(path).iloc[:, 0].values.astype(float)
    if len(vals) >= N_YEARS:
        point_data[sc] = vals[:N_YEARS]
    else:
        padded = np.full(N_YEARS, np.nan)
        padded[:len(vals)] = vals
        point_data[sc] = padded

if missing_files:
    print(f"  WARNING: {len(missing_files)} CSV(s) not found — excluded.")
    print(f"  Missing: {missing_files[:10]}{'...' if len(missing_files) > 10 else ''}")
print(f"  Loaded {len(point_data)} / {len(meta)} CSVs.\n")

available = meta[meta["Sample_Code"].isin(point_data)].copy()

# ---------------------------------------------------------------------------
# 4. Compute per-stratum variance — VM0042 Eq 62
#
#   s²_sampling,h,t = A²_h / (n_h * (n_h - 1))  *  Σ_i (Δ_h,i,t − Δ̄_h,t)²
#
#   s²_sampling,t   = Σ_h  s²_sampling,h,t
# ---------------------------------------------------------------------------

print("Computing sampling error (VM0042 Eq 62)...")

stratum_records   = []
total_s2_sampling = np.zeros(N_YEARS)

for soil, A_h in STRATA.items():

    pts = available[available["FAO Soil Type"] == soil]["Sample_Code"].tolist()
    n_h = len(pts)

    if n_h == 0:
        print(f"  {soil}: no points with results — skipped.")
        continue

    if n_h == 1:
        print(f"  WARNING {soil}: n=1 — within-stratum variance cannot be estimated; set to 0.")
        matrix      = np.stack([point_data[pts[0]]], axis=0)
        delta_bar_h = matrix[0]
        s2_h        = np.zeros(N_YEARS)
        note        = "n=1: variance=0"
    else:
        matrix      = np.stack([point_data[sc] for sc in pts], axis=0)  # (n_h, N_YEARS)
        delta_bar_h = np.nanmean(matrix, axis=0)                          # (N_YEARS,)
        ss_h        = np.nansum((matrix - delta_bar_h[np.newaxis, :]) ** 2, axis=0)
        s2_h        = (A_h ** 2 / (n_h * (n_h - 1))) * ss_h              # (tCO2e/yr)²
        note        = ""

    total_s2_sampling += s2_h

    for t_idx, year in enumerate(YEARS):
        stratum_records.append({
            "Stratum_soil":        soil,
            "Year":                year,
            "A_h_ha":              A_h,
            "n_h":                 n_h,
            "Delta_bar_h_t":       round(float(delta_bar_h[t_idx]), 6),
            "s2_sampling_h_t":     round(float(s2_h[t_idx]), 4),
            "s_sampling_h_t":      round(float(np.sqrt(s2_h[t_idx])), 4),
            "note":                note,
        })

    print(f"  {soil}: n={n_h:>3}, A={A_h:>10,.2f} ha  "
          f"| yr1 Δ̄={delta_bar_h[0]:.4f} tCO2e/ha/yr, "
          f"s={np.sqrt(s2_h[0]):.4f} tCO2e/yr")

print()

# ---------------------------------------------------------------------------
# 5. Area-weighted project mean ER per year
#    Δ̄_t = Σ_h (A_h / A) * Δ̄_h,t
# ---------------------------------------------------------------------------

delta_bar_project = np.zeros(N_YEARS)
for soil, A_h in STRATA.items():
    pts = available[available["FAO Soil Type"] == soil]["Sample_Code"].tolist()
    if not pts:
        continue
    matrix      = np.stack([point_data[sc] for sc in pts], axis=0)
    delta_bar_h = np.nanmean(matrix, axis=0)
    delta_bar_project += (A_h / TOTAL_AREA_HA) * delta_bar_h

# ---------------------------------------------------------------------------
# 6. Combined variance of the areal mean — VM0042 Eq 63
#
#   s²_Δ̄,t = s²_sampling,t / A²  +  s²_model
#
#   U%_t = t_0.05 * s_Δ̄,t / |Δ̄_t| * 100
# ---------------------------------------------------------------------------

s2_delta_bar = total_s2_sampling / (TOTAL_AREA_HA ** 2) + S2_MODEL
s_delta_bar  = np.sqrt(s2_delta_bar)

with np.errstate(divide="ignore", invalid="ignore"):
    U_pct = np.where(
        delta_bar_project != 0,
        T_95 * s_delta_bar / np.abs(delta_bar_project) * 100,
        np.nan,
    )

# ---------------------------------------------------------------------------
# 7. Save outputs
# ---------------------------------------------------------------------------

year_df = pd.DataFrame({
    "Year":                            YEARS,
    "Delta_bar_project_tCO2ehayr":     np.round(delta_bar_project, 6),
    "s2_sampling_tCO2eyr2":            np.round(total_s2_sampling, 4),
    "s2_model":                        S2_MODEL,
    "s2_delta_bar_tCO2ehayr2":         np.round(s2_delta_bar, 10),
    "s_delta_bar_tCO2ehayr":           np.round(s_delta_bar, 8),
    "U_pct_total":                     np.round(U_pct, 4),
    "exceeds_10pct_threshold":         U_pct > 10,
})
year_df.to_csv("sampling_error_by_year.csv", index=False)

stratum_df = pd.DataFrame(stratum_records)
stratum_df.to_csv("sampling_error_by_stratum_year.csv", index=False)

summary = {
    "Total_project_area_ha":        TOTAL_AREA_HA,
    "N_strata":                     len(STRATA),
    "Strata":                       "ANm, NTh, NTu",
    "N_points_loaded":              len(point_data),
    "N_points_missing":             len(missing_files),
    "s2_model_used":                S2_MODEL,
    "Note_s2_model":                "0.0 placeholder — replace with MVR Eq-64 value and re-run",
    "Yr1_Delta_bar_tCO2ehayr":      round(float(delta_bar_project[0]), 4),
    "Yr1_s_delta_bar_tCO2ehayr":    round(float(s_delta_bar[0]), 6),
    "Yr1_U_pct":                    round(float(U_pct[0]), 3),
    "Yr1_exceeds_10pct":            bool(U_pct[0] > 10),
    "VP_yrs1to5_mean_U_pct":        round(float(np.nanmean(U_pct[:5])), 3),
    "VP_yrs1to5_max_U_pct":         round(float(np.nanmax(U_pct[:5])), 3),
}
pd.DataFrame([summary]).T.rename(columns={0: "Value"}).to_csv("sampling_error_summary.csv")

# ---------------------------------------------------------------------------
# 8. Print results table
# ---------------------------------------------------------------------------

print("=" * 72)
print("VM0042 §8.6.1.1.3-4  SAMPLING ERROR RESULTS  (3 strata: ANm/NTh/NTu)")
print("=" * 72)
print(f"  Total area A = {TOTAL_AREA_HA:,.2f} ha  |  "
      f"Points loaded = {len(point_data)}  |  "
      f"s²_model = {S2_MODEL} (placeholder)")
print()
print(f"  {'Year':<6} {'Δ̄ (tCO2e/ha/yr)':>18} {'s_Δ̄ (tCO2e/ha/yr)':>20} {'U%':>8}  {'≤10%?':>6}")
print("  " + "-" * 62)
for _, r in year_df.head(10).iterrows():
    ok = "  ✓" if not r["exceeds_10pct_threshold"] else "  ✗ DEDUCTION"
    print(f"  {int(r['Year']):<6} "
          f"{r['Delta_bar_project_tCO2ehayr']:>18.4f} "
          f"{r['s_delta_bar_tCO2ehayr']:>20.6f} "
          f"{r['U_pct_total']:>7.2f}%{ok}")
print(f"  ... ({N_YEARS} years total — see sampling_error_by_year.csv)")
print()
print("  Outputs written:")
print("    sampling_error_by_year.csv          — full year-by-year results")
print("    sampling_error_by_stratum_year.csv  — per-stratum variance detail")
print("    sampling_error_summary.csv          — summary statistics")
print()
print("  NEXT: set S2_MODEL = <Eq-64 value from MVR> at top of script and re-run")
print("        to get the final combined U% for the VM0042 uncertainty deduction.")
