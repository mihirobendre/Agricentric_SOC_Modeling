"""
Per-point SOC data preparation and RothC run pipeline.
VM0042 §8.6 — uncertainty estimated on a per-sample-point basis.

All 174 sample points are included. Points whose crop type has no directly
defined parameter set receive the simple arithmetic average of all crop
C-input parameters within their (cooperative, FAO soil type) stratum.

Pipeline:
  1. Impute missing BD with cooperative-level mean of measured points.
  2. Compute SOC stock (t C/ha) at 0-30 cm.
  3. Assign crop parameters: direct match if crop is known, stratum average otherwise.
  4. Write one filtered CSV per cooperative to per_coop_filtered/.
  5. Call run_ER_by_crop() per point; save one CSV per point to per_point_results/.
  6. Write run_log.csv (audit trail) and skipped_points.csv (errors only).

Run: python prepare_and_run_points.py  (same directory as run_ERs.py)
"""

from run_ERs import *
import os

# ---------------------------------------------------------------------------
# 0. Configuration
# ---------------------------------------------------------------------------

DATA_PATH  = "Kenya_SOC_Data_w_FAO_Soil_Type.csv"
OUTPUT_DIR = "per_point_results"
COOP_DIR   = "per_coop_filtered"
DEPTH_CM   = 30.0      # 0–30 cm per VM0042

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(COOP_DIR,   exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Direct crop mapping (raw field value -> canonical key)
#    Points not in this map fall back to the stratum average.
# ---------------------------------------------------------------------------

CROP_MAP = {
    "Maize":        "Maize",
    "Corn":         "Maize",
    "Potato":       "Potato",
    "Irish Potato": "Potato",
    "Wheat":        "Wheat",
    "Barley":       "Barley",
    "Peas":         "Beans",
    "Beans":        "Beans",
    "Tea":          "Tea",
}

# ---------------------------------------------------------------------------
# 2. Crop parameter table: CROP_PARAMS[(coop, fao_soil)][mapped_crop]
#    All values taken verbatim from aggregate_ERs.py files.
#    Optional "_note" key is stripped before calling run_ER_by_crop().
#
#    S_P/S_S/S_R/S_E flags:
#      S_P = Ploughing (stubble incorporation)
#      S_S = Stubble / residue retention on field
#      S_R = Root carbon input included
#      S_E = Extra organic input (manure)
# ---------------------------------------------------------------------------

CROP_PARAMS = {

    # --- Eor Emayian (ANm) ------------------------------------------------
    ("Eor Emayian", "ANm"): {
        "Maize": dict(
            crop_type="Maize",  crop_yield=2.8911,  moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
        ),
        "Potato": dict(
            crop_type="Potato", crop_yield=4.448,   moist_content=0.75,
            harvest_index=0.75, rs_ratio=0.2,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=0,
        ),
        "Beans": dict(
            crop_type="Beans",  crop_yield=0.526,   moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
            _note="Beans proxy: Lanyuak Barley params (no Beans block in Eor)",
        ),
        # Stratum average across Maize, Potato, Beans — used for all other crops
        "_avg": dict(
            crop_type="Average", crop_yield=2.6217,  moist_content=0.336667,
            harvest_index=0.57,  rs_ratio=0.133333,  manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=0.666667,
            _note="Stratum average: mean of Maize, Potato, Beans params",
        ),
    },

    # --- Lanyuak (ANm) ----------------------------------------------------
    ("Lanyuak", "ANm"): {
        "Maize": dict(
            crop_type="Maize",  crop_yield=0.607,   moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
        ),
        "Wheat": dict(
            crop_type="Wheat",  crop_yield=0.526,   moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
        ),
        "Barley": dict(
            crop_type="Barley", crop_yield=0.526,   moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
        ),
        "Potato": dict(
            crop_type="Potato", crop_yield=20.2343, moist_content=0.75,
            harvest_index=0.75, rs_ratio=0.2,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=0,
        ),
        "Beans": dict(
            crop_type="Beans",  crop_yield=0.526,   moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
            _note="Beans proxy: Barley params (same Lanyuak block)",
        ),
        # Stratum average across Maize, Wheat, Barley, Potato, Beans
        "_avg": dict(
            crop_type="Average", crop_yield=4.48386, moist_content=0.254,
            harvest_index=0.534, rs_ratio=0.12,      manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=0.8,
            _note="Stratum average: mean of Maize, Wheat, Barley, Potato, Beans params",
        ),
    },

    # --- Mumberes NTh (Nitisol humic) ------------------------------------
    ("Mumberes", "NTh"): {
        "Maize": dict(
            crop_type="Maize",  crop_yield=7.413,   moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
        ),
        "Potato": dict(
            crop_type="Potato", crop_yield=4.448,   moist_content=0.75,
            harvest_index=0.75, rs_ratio=0.2,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=0,
        ),
        "Beans": dict(
            crop_type="Beans",  crop_yield=0.526,   moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
            _note="Beans proxy: Lanyuak Barley params (no Beans in Mumberes NTh block)",
        ),
        # Stratum average across Maize, Potato, Beans
        "_avg": dict(
            crop_type="Average", crop_yield=4.129,   moist_content=0.336667,
            harvest_index=0.57,  rs_ratio=0.133333,  manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=0.666667,
            _note="Stratum average: mean of Maize, Potato, Beans params",
        ),
    },

    # --- Mumberes NTu (Nitisol eutric) -----------------------------------
    ("Mumberes", "NTu"): {
        "Maize": dict(
            crop_type="Maize",  crop_yield=7.413,   moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
        ),
        "Potato": dict(
            crop_type="Potato", crop_yield=4.448,   moist_content=0.75,
            harvest_index=0.75, rs_ratio=0.2,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=0,
        ),
        "Beans": dict(
            crop_type="Beans",  crop_yield=0.526,   moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
            _note="Beans proxy: Lanyuak Barley params (no Beans in Mumberes NTu block)",
        ),
        # Stratum average across Maize, Potato, Beans
        "_avg": dict(
            crop_type="Average", crop_yield=4.129,   moist_content=0.336667,
            harvest_index=0.57,  rs_ratio=0.133333,  manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=0.666667,
            _note="Stratum average: mean of Maize, Potato, Beans params",
        ),
    },

    # --- Kabianga (NTu) --------------------------------------------------
    # Defined crops: Tea + Maize (Corn->Maize).
    # Stratum average is over both Tea and Maize.
    ("Kabianga", "NTu"): {
        "Tea": dict(
            crop_type="Tea",    crop_yield=18.73284, moist_content=0.777778,
            harvest_index=0.2,  rs_ratio=0.2,        manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
        ),
        "Maize": dict(
            crop_type="Maize",  crop_yield=7.413,    moist_content=0.13,
            harvest_index=0.48, rs_ratio=0.1,        manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
            _note="Kabianga Maize: using Mumberes NTu yield (no Kabianga Maize block defined)",
        ),
        # Stratum average across Tea and Maize
        "_avg": dict(
            crop_type="Average", crop_yield=13.07292, moist_content=0.453889,
            harvest_index=0.34,  rs_ratio=0.15,       manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1.0,
            _note="Stratum average: mean of Tea and Maize params",
        ),
    },

    # --- Kipsigis (NTu) --------------------------------------------------
    # Only one defined crop (Tea). Average == Tea params.
    ("Kipsigis", "NTu"): {
        "Tea": dict(
            crop_type="Tea",    crop_yield=20.75688, moist_content=0.777778,
            harvest_index=0.2,  rs_ratio=0.2,        manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
        ),
        # Stratum average == Tea (only defined crop)
        "_avg": dict(
            crop_type="Average", crop_yield=20.75688, moist_content=0.777778,
            harvest_index=0.2,   rs_ratio=0.2,        manure=0.5,
            S_P=0, S_S=1, S_R=1, S_E=1,
            _note="Stratum average == Tea params (only defined crop in Kipsigis)",
        ),
    },
}

# ---------------------------------------------------------------------------
# 3. Helper: resolve crop parameters for a given point
# ---------------------------------------------------------------------------

def get_crop_params(coop, fao_type, raw_crop):
    """
    Return (params_dict, param_source_label) for a point.
    Tries direct mapped crop first; falls back to stratum average.
    """
    stratum = CROP_PARAMS.get((coop, fao_type), {})
    mapped  = CROP_MAP.get(raw_crop)

    if mapped and mapped in stratum:
        p = dict(stratum[mapped])
        note = p.pop("_note", "")
        return p, mapped, note

    # Fall back to stratum average
    avg = stratum.get("_avg")
    if avg:
        p = dict(avg)
        note = p.pop("_note", f"Stratum average for ({coop}, {fao_type})")
        return p, "stratum_avg", note

    return None, None, f"No params and no average defined for ({coop}, {fao_type})"

# ---------------------------------------------------------------------------
# 4. Load data
# ---------------------------------------------------------------------------

df = pd.read_csv(DATA_PATH)
print(f"Loaded {len(df)} sample points.\n")

# ---------------------------------------------------------------------------
# 5. BD imputation: cooperative-level mean of measured points
# ---------------------------------------------------------------------------

bd_means = (
    df.dropna(subset=["BD (g/cm3)"])
    .groupby("Cooperative")["BD (g/cm3)"]
    .mean()
)

print("BD cooperative means (used for imputation where BD not measured):")
for coop, mean_bd in bd_means.items():
    n_meas  = df[(df["Cooperative"] == coop) & df["BD (g/cm3)"].notna()].shape[0]
    n_total = df[df["Cooperative"] == coop].shape[0]
    print(f"  {coop:<15}: {mean_bd:.4f} g/cm³  ({n_meas}/{n_total} measured)")
print()

def impute_bd(row):
    if pd.notna(row["BD (g/cm3)"]):
        return row["BD (g/cm3)"]
    return bd_means.get(row["Cooperative"], df["BD (g/cm3)"].mean())

df["BD_imputed"]     = df.apply(impute_bd, axis=1)
df["BD_was_imputed"] = df["BD (g/cm3)"].isna()

# ---------------------------------------------------------------------------
# 6. Compute SOC stock (t C/ha) at 0–30 cm
#    SOC_stock = C(%) / 100 * BD (g/cm³) * depth_cm * 100
#    = C_frac * BD * 30 * 100  →  t C/ha
# ---------------------------------------------------------------------------

df["SOC_stock_tCha"] = (df["C (%)"] / 100.0) * df["BD_imputed"] * DEPTH_CM * 100.0

print(f"SOC stock (t C/ha) at {int(DEPTH_CM)} cm — all {len(df)} points:")
print(df["SOC_stock_tCha"].describe().round(3))
print()

# ---------------------------------------------------------------------------
# 7. Write per-cooperative filtered CSVs (all points, no exclusions)
# ---------------------------------------------------------------------------

for coop, grp in df.groupby("Cooperative"):
    safe_name = coop.replace(" ", "_")
    fname = os.path.join(COOP_DIR, f"{safe_name}_points.csv")
    grp.to_csv(fname, index=False)
    print(f"Written: {fname}  ({len(grp)} points)")
print()

# ---------------------------------------------------------------------------
# 8. Run RothC per point; save ONE CSV per point
# ---------------------------------------------------------------------------

run_log = []
skipped = []

for _, row in df.iterrows():
    coop        = row["Cooperative"]
    fao_type    = row["FAO Soil Type"]
    raw_crop    = row["Crop"]
    sample_code = row["Sample_Code"]
    clay        = row["%Clay (%)"]
    soc_stock   = row["SOC_stock_tCha"]
    bd          = row["BD_imputed"]

    crop_kwargs, param_source, note = get_crop_params(coop, fao_type, raw_crop)

    if crop_kwargs is None:
        skipped.append({
            "Sample_Code":   sample_code,
            "Cooperative":   coop,
            "FAO Soil Type": fao_type,
            "Crop":          raw_crop,
            "reason":        note,
        })
        continue

    # Merge crop params with point-level soil inputs
    kwargs = dict(
        **crop_kwargs,
        clay_content = clay,
        soc_content  = soc_stock,
        bd_content   = bd,
        fao_type     = fao_type,
        coop         = coop,
    )

    try:
        results  = run_ER_by_crop(**kwargs)
        out_path = os.path.join(OUTPUT_DIR, f"{sample_code}.csv")
        results.to_csv(out_path, index=False)

        run_log.append({
            "Sample_Code":    sample_code,
            "Cooperative":    coop,
            "FAO_type":       fao_type,
            "Crop_raw":       raw_crop,
            "param_source":   param_source,
            "clay_pct":       round(clay, 3),
            "SOC_tCha":       round(soc_stock, 3),
            "BD_gcm3":        round(bd, 4),
            "BD_was_imputed": row["BD_was_imputed"],
            "crop_yield":     crop_kwargs.get("crop_yield"),
            "param_note":     note,
            "output_file":    f"{sample_code}.csv",
        })

    except Exception as e:
        skipped.append({
            "Sample_Code":   sample_code,
            "Cooperative":   coop,
            "FAO Soil Type": fao_type,
            "Crop":          raw_crop,
            "reason":        str(e),
        })

# ---------------------------------------------------------------------------
# 9. Write logs
# ---------------------------------------------------------------------------

log_df = pd.DataFrame(run_log)
log_df.to_csv("run_log.csv", index=False)

print(f"Successfully ran RothC for {len(run_log)} / {len(df)} points.")

if skipped:
    skip_df = pd.DataFrame(skipped)
    skip_df.to_csv("skipped_points.csv", index=False)
    print(f"Skipped {len(skipped)} points (errors only) — see skipped_points.csv")
    print(skip_df.to_string(index=False))
else:
    print("No points skipped — all points completed successfully.")

# Summary of param sources
src_counts = log_df["param_source"].value_counts()
print(f"\nParam source breakdown:")
print(src_counts.to_string())

print()
print("Output locations:")
print(f"  Per-point CSVs        : {OUTPUT_DIR}/  ({len(run_log)} files, one per Sample_Code)")
print(f"  Per-coop filtered CSVs: {COOP_DIR}/")
print(f"  Run log               : run_log.csv")
