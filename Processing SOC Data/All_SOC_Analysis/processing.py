import pandas as pd

# --- SETTINGS ---
excel_file = "All_SOC_Data.xlsx"     # Replace with your Excel file
sheet_name = "Sheet1"             # Replace with your sheet name
bd_col = "BD (g/cm3)"        # Column containing bulk density values
c_col = "C (%)"
# --- LOAD EXCEL ---
df = pd.read_excel(excel_file, sheet_name=sheet_name)

# --- CLEAN + CONVERT TO NUMERIC ---
df[bd_col] = pd.to_numeric(df[bd_col], errors="coerce")
df[c_col] = pd.to_numeric(df[c_col], errors="coerce")
# --- CALCULATE AVERAGE ---
average_bd = df[bd_col].mean()
average_c = df[c_col].mean()

depth = 30 # cm
total_SOC = average_c/100 * average_bd * depth * 100

print(f"Average {bd_col}: {average_bd:.4f} g/cm³")
print(f"Average {c_col}: {average_c:.4f} %")
print(f"Average SOC: {total_SOC:.4f} tons/ha")

