import pandas as pd

# === Configuration ===
input_excel = "Kenya_SOC_data.xlsx"            # Path to your Excel file
coop_col = "Cooperative"
bd_col = "BD (g/cm3)"
c_col = "C (%)"
clay_col = "%Clay (%)"
depth_cm = 30                         # depth sampled (cm)

# === Load Excel file ===
df = pd.read_excel(input_excel)

# === Group by Cooperative ===
grouped = df.groupby(coop_col)

# === Compute SOC for each cooperative ===
results = []

for coop_name, group in grouped:
    avg_bd = group[bd_col].mean()
    avg_c  = group[c_col].mean()
    avg_clay = group[clay_col].mean()
    median_c = group[c_col].median()
    # SOC formula: BD * C * depth
    soc = avg_bd * avg_c * depth_cm

    results.append((coop_name, avg_bd, avg_c, avg_clay, soc))

# === Print results ===
print("\nAverage SOC per Cooperative")
print("--------------------------------------------")
for coop_name, avg_bd, avg_c, avg_clay, soc in results:
    print(f"Cooperative: {coop_name}")
    print(f"  Avg BD (g/cm³):    {avg_bd:.4f}")
    print(f"  Avg C (%):         {avg_c:.4f}")
    print(f"  Median C (%):      {median_c:.4f}")
    print(f"  Avg clay (%):      {avg_clay:.4f}")
    print(f"  Avg SOC (tons/ha): {soc:.4f}\n")

