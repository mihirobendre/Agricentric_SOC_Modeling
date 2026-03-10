import pandas as pd
from pathlib import Path

# ---- user inputs ----
input_path = Path("Kenya_SOC_Data_w_FAO_Soil_Type.csv")
bd_col = "BD (g/cm3)"
soil_col = "FAO Soil Type"
output_dir = Path("ALL_DATA_soil_type_csvs")
# ----------------------

# Read data
df = pd.read_csv(input_path)
df_bd = df

# Create output directory if needed
output_dir.mkdir(parents=True, exist_ok=True)

# Get unique soil types (dropping NaN)
soil_types = df_bd[soil_col].dropna().unique()

for st in soil_types:
    # Filter rows for this soil type
    df_soil = df_bd[df_bd[soil_col] == st]

    # Sanitize soil type for filename (e.g. replace spaces or slashes)
    st_safe = str(st).replace(" ", "_").replace("/", "-")

    out_file = output_dir / f"Kenya_SOC_{st_safe}.csv"
    df_soil.to_csv(out_file, index=False)

print(f"Wrote {len(soil_types)} CSV files to {output_dir}")

