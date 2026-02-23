# Recompute averages separately for BD and C without dropping rows jointly
import pandas as pd

df = pd.read_csv('Kenya_SOC_Data_w_FAO_Soil_Type.csv')

# Average BD using rows where BD present
bd_avg = (
    df.dropna(subset=["BD (g/cm3)"])
      .groupby(["Cooperative","FAO Soil Type"], as_index=False)["BD (g/cm3)"]
      .mean()
      .rename(columns={"BD (g/cm3)":"avg_BD"})
)

# Average C using rows where C present
c_avg = (
    df.dropna(subset=["C (%)"])
      .groupby(["Cooperative","FAO Soil Type"], as_index=False)["C (%)"]
      .mean()
      .rename(columns={"C (%)":"avg_C"})
)

# Merge averages
grouped = pd.merge(bd_avg, c_avg, on=["Cooperative","FAO Soil Type"], how="outer")

# Compute SOC where both exist
grouped["SOC (t/ha)"] = grouped["avg_BD"] * grouped["avg_C"] * 30

pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)

print("Results: ")
print(grouped)


# Making sure all soil types present are analyzed for SOC and BD:

# soil types present in raw
raw = (
    df.groupby(["Cooperative"])["FAO Soil Type"]
    .unique()
    .reset_index()
)

print()
print("All SOC types in Coop (check): ")
print(raw)
