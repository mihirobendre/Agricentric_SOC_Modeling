from run_ERs import *

# ─────────────────────────────────────────────
# Helper: append a crop's results into master_df
# Each crop gets three columns with a shared prefix:
#   "<Crop> - SOC Baseline (tCO2e/ha)"
#   "<Crop> - SOC Project (tCO2e/ha)"
#   "<Crop> - ERs (tCO2e/ha)"
# ─────────────────────────────────────────────
def add_crop(master_df, crop, results):
    # Normalise: run_ERs.py should return a DataFrame, but guard against
    # a stale version that still returns a plain Series (ERs only).
    if isinstance(results, pd.Series):
        results = results.rename("ERs (tCO2e/ha)").to_frame()
    for col in results.columns:
        master_df[f"{crop} - {col}"] = results[col].values
    return master_df


# ══════════════════════════════════════════════
# Cooperative: Kabianga
# ══════════════════════════════════════════════
master_df = pd.DataFrame()
coop = "Kabianga"

crop = "Tea"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 18.73284,
    moist_content = 1 - 1/4.5,
    harvest_index = 0.2,
    rs_ratio = 0.2,
    manure = 0.5,
    clay_content = 58.697,
    soc_content = 137.050440,
    bd_content = 1.033750,
    fao_type = 'NTu',
    coop = coop,
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 1
)
master_df = add_crop(master_df, crop, results)

crop = "Napier"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 296.5266,
    moist_content = 0.8,
    harvest_index = 1,
    rs_ratio = 0.5,
    manure = 0.3,
    clay_content = 58.697,
    soc_content = 137.050440,
    bd_content = 1.033750,
    fao_type = 'NTu',
    coop = coop,
    S_P = 0,
    S_S = 0,
    S_R = 1,
    S_E = 1
)
master_df = add_crop(master_df, crop, results)

master_df.to_excel(f"aggregate_{coop}_results.xlsx", index=False)


# ══════════════════════════════════════════════
# Cooperative: Kipsigis
# ══════════════════════════════════════════════
master_df = pd.DataFrame()
coop = "Kipsigis"

crop = "Tea"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 20.75688,
    moist_content = 1 - 1/4.5,
    harvest_index = 0.2,
    rs_ratio = 0.2,
    manure = 0.5,
    clay_content = 58.697,
    soc_content = 137.050440,
    bd_content = 1.033750,
    fao_type = 'NTu',
    coop = coop,
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 1
)
master_df = add_crop(master_df, crop, results)

master_df.to_excel(f"aggregate_{coop}_results.xlsx", index=False)


# ══════════════════════════════════════════════
# Cooperative: Mumberes
# ══════════════════════════════════════════════
master_df = pd.DataFrame()
coop = "Mumberes"

crop = "Maize"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 7.413,
    moist_content = 0.13,
    harvest_index = 0.48,
    rs_ratio = 0.1,
    manure = 0.5,
    clay_content = 58.697,
    soc_content = 137.050440,
    bd_content = 1.033750,
    fao_type = 'NTu',
    coop = coop,
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 1
)
master_df = add_crop(master_df, crop, results)

crop = "Potato"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 4.448,
    moist_content = 0.75,
    harvest_index = 0.75,
    rs_ratio = 0.2,
    manure = 0.5,
    clay_content = 58.697,
    soc_content = 137.050440,
    bd_content = 1.033750,
    fao_type = 'NTu',
    coop = coop,
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 0
)
master_df = add_crop(master_df, crop, results)

master_df.to_excel(f"aggregate_{coop}_results.xlsx", index=False)
