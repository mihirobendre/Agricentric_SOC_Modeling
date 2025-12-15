import pandas as pd

# === Configuration ===
input_excel = "Kenya_SOC_data.xlsx"     # Path to your Excel file
column_name = "BD (g/cm3)"     # Column to average

# === Load Excel file ===
df = pd.read_excel(input_excel)

# === Compute average bulk density ===
avg_bd = df[column_name].mean()

print(f"Average {column_name}: {avg_bd}")

