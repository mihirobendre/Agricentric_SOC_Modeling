import pandas as pd
import os

# === Configuration ===
input_excel = "Kenya_SOC_data.xlsx"          # Path to your Excel file
output_folder = "Data_by_coop"  # Folder to store the output CSVs
column_name = "Cooperative"         # Column to group/sort by

# === Create output directory if it doesn't exist ===
os.makedirs(output_folder, exist_ok=True)

def sanitize_filename(name):
    """Remove illegal characters from filenames."""
    return "".join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip()

# === Load Excel file ===
df = pd.read_excel(input_excel)


# === Sort dataframe by the 'Cooperative' column ===
df_sorted = df.sort_values(by=column_name)

# === Group by each Cooperative and save as separate CSV ===
for coop_name, group_df in df_sorted.groupby(column_name):
    safe_name = sanitize_filename(str(coop_name))
    output_path = os.path.join(output_folder, f"{safe_name}.csv")
    
    group_df.to_csv(output_path, index=False)
    print(f"Saved: {output_path}")

print("Done! All cooperatives exported.")

