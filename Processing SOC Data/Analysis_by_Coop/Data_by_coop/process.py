import pandas as pd
import glob
import os

# Loop through all CSV files in the current directory
for file in glob.glob("*.csv"):
    print(f"Processing: {file}")

    # Read CSV
    df = pd.read_csv(file)

    # Ensure required columns exist
    if "C (%)" not in df.columns or "BD (g/cm3)" not in df.columns:
        print(f"Skipping {file}: Missing required columns.")
        continue

    # Calculate net average BD
    avg_bd = df["BD (g/cm3)"].mean()

    # Create SOC column
    df["SOC (t/ha)"] = df["C (%)"] * avg_bd * 30

    # Save back to CSV (overwrite)
    df.to_csv(file, index=False)

    print(f"Added 'SOC (t/ha)' to {file} (avg BD = {avg_bd:.3f})")

print("Done.")

