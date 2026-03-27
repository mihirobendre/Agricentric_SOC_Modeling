import pandas as pd
from pathlib import Path

# ---- user inputs ----
input_path = Path("Kenya_SOC_Data_w_FAO_Soil_Type.csv")
bd_col = "BD (g/cm3)"
soil_col = "FAO Soil Type"
sand_col = "%Sand (%)"
silt_col = "%Silt (%)"
clay_col = "%Clay (%)"
output_dir = Path("soil_type_csvs")
summary_file = Path("soil_type_texture_summary.csv")
# ----------------------

# Read data
df = pd.read_csv(input_path)

# Keep only rows with non-missing bulk density
df_bd = df

# Create output directory if needed
output_dir.mkdir(parents=True, exist_ok=True)

# Get unique soil types (dropping NaN)
soil_types = df_bd[soil_col].dropna().unique()

for st in soil_types:
    # Filter rows for this soil type
    df_soil = df_bd[df_bd[soil_col] == st]

    # Sanitize soil type for filename
    st_safe = str(st).replace(" ", "_").replace("/", "-")

    out_file = output_dir / f"Kenya_SOC_{st_safe}.csv"
    df_soil.to_csv(out_file, index=False)

# ---- compute average texture per soil type ----
texture_means = (
    df_bd
    .groupby(soil_col)[[sand_col, silt_col, clay_col]]
    .mean()
    .reset_index()
)

# Save summary to CSV
texture_means.to_csv(summary_file, index=False)

# Optionally print to screen
print("Average texture per soil type:")
print(texture_means)
print(f"\nSaved per-soil-type CSVs in: {output_dir}")
print(f"Saved texture summary to: {summary_file}")

