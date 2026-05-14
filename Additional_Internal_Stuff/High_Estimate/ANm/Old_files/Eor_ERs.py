import numpy as np
from run_rothc import run_rothc
import pandas as pd
from run_rothc import *


# Generic SOC model parameters (change by soil strata):
clay_content = 40.190164
soc_content = 113.941170
bd_content = 0.970714
fao_type = 'ANm'
coop = 'Lanyuak'

#######################################
#### BOLINDER CALCULATIONS C-INPUT ####
#######################################

def Bolinder_CI(C_P, S_P, C_S, S_S, C_R, S_R, C_E, S_E):
    C_I = C_P * S_P + C_S * S_S + C_R * S_R + C_E * S_E
    return C_I

carbon_content = 0.5
root_exudate_ratio = 0.05

bolinder_c_in = 0


# C-input from Maize

crop_type = "Maize"
proportion_crop = 0.4
crop_yield = 2.8911      # yields usually already reported as dry matter
moist_content = 0.13
harvest_index = 0.48    # ratio of dry-yield : total dry aboveground biomass
rs_ratio = 0.1

C_P = crop_yield * carbon_content
S_P = 0

C_S = (C_P * 1/harvest_index - C_P)
S_S = 1

C_R = (C_S + C_P)* rs_ratio
S_R = 1

C_E = (C_P + C_S + C_R) * (root_exudate_ratio)
S_E = 1

c_in = Bolinder_CI(C_P, S_P, C_S, S_S, C_R, S_R, C_E, S_E) * proportion_crop
bolinder_c_in += c_in

print(f"Bolinder C-inp for {crop_type} (~{proportion_crop * 100 :.0f}% of coop.): {c_in:.3f} t/ha")

# C-input from Potato

crop_type = "Potato"
proportion_crop = 0.6
crop_yield = 6.795
moist_content = 0.75
harvest_index = 0.75    # ratio of dry-yield : total dry aboveground biomass
rs_ratio = 0.2

C_P = crop_yield * carbon_content
S_P = 0

C_S = (C_P * 1/harvest_index - C_P)
S_S = 1

C_R = C_P
S_R = 0

C_E = (C_P + C_S + C_R) * (root_exudate_ratio)
S_E = 0

c_in = Bolinder_CI(C_P, S_P, C_S, S_S, C_R, S_R, C_E, S_E) * proportion_crop
bolinder_c_in += c_in

print(f"Bolinder C-inp for {crop_type} (~{proportion_crop * 100 :.0f}% of coop.): {c_in:.3f} t/ha")

print(f"Bolinder C-inp total: {bolinder_c_in:.3f} t/ha\n")


#######################################
### MAINTENANCE C-INPUT CALCULATION ###
#######################################

# Carbon input maintenance

maintenance_c_in, baseline_soc, iters = solve_carbon_input(
	starting_soil_carbon=soc_content,
	clay=clay_content,
	temp=[19.74, 20.79, 20.69, 19.51, 18.51, 17.66, 17.35, 17.85, 18.66, 18.95, 18.75, 18.79],
	rain=[112.34, 218.01, 279.67, 252.53, 313, 225.76, 233.06, 348.24, 360.77,179.14, 57.39, 63.75],
	evap=[80, 80, 88, 82, 75, 63, 57, 60, 69, 80, 77, 77],
	starting_fym = 0.0,
	pc=[0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
	total_years=0,
	start_year=2026,
	tol=1e-2,
	max_iter = 50,
	c_min=0.0,
	c_max=100.0,
	trm = 0.93,
	fao_type = fao_type,
    bd = bd_content
)

print(f"Maintenance C-inp: {maintenance_c_in:.3f} t/ha")
print(f"Baseline SOC: {baseline_soc:.3f} t/ha")


# Compost needed

difference_c_in = maintenance_c_in - bolinder_c_in

carbon_content_compost = 0.5

compost_reqd = difference_c_in * 1/carbon_content_compost

#print(f"Short of {difference_c_in:.3f} t/ha C-input")
#print(f"Compost needed: {compost_reqd:.3f} t/ha")



#######################################
##### ROTH-C MODEL RUNS + ER CALC #####
#######################################

# Project model run

output_months_project, output_years_project = run_rothc(
	starting_soil_carbon=soc_content,
	total_years=40,
	start_year=2026,
	clay=clay_content,
	depth=30,
	temp = [19.74, 20.79, 20.69, 19.51, 18.51, 17.66, 17.35, 17.85, 18.66, 18.95, 18.75, 18.79],
	rain=[112.34, 218.01, 279.67, 252.53, 313, 225.76, 233.06, 348.24, 360.77,179.14, 57.39, 63.75],
	evap=[80, 80, 88, 82, 75, 63, 57, 60, 69, 80, 77, 77],
	pc = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
	dpm_rpm = 1.44,
	carbon_input = maintenance_c_in,			# annual input
	farmyard_manure = 0.0,
	carbon_input_eqm = None,		  # annual input
	farmyard_manure_eqm = 0.0,	   # annual input
	additional_c_in = None,
	trm = 0.93,
	fao_type = fao_type,
    bd = bd_content
)


# Baseline model run

output_months_baseline, output_years_baseline = run_rothc(
	starting_soil_carbon=soc_content,
	total_years=40,
	start_year=2026,
	clay=clay_content,
	depth=30,
	temp = [19.74, 20.79, 20.69, 19.51, 18.51, 17.66, 17.35, 17.85, 18.66, 18.95, 18.75, 18.79],
	rain=[112.34, 218.01, 279.67, 252.53, 313, 225.76, 233.06, 348.24, 360.77,179.14, 57.39, 63.75],
	evap=[80, 80, 88, 82, 75, 63, 57, 60, 69, 80, 77, 77],
	pc = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
	dpm_rpm = 1.44,
	carbon_input = bolinder_c_in,			 # annual input
	farmyard_manure = 0.0,
	carbon_input_eqm = None,		  # annual input
	farmyard_manure_eqm = 0.0,	   # annual input
	additional_c_in = None,
	trm = 1.0,
	fao_type = fao_type,
	bd = bd_content
)

combined = pd.DataFrame({
	"Year": output_years_baseline["Year"],
	"SOC Baseline (t/ha)": output_years_baseline["SOC_t_C_ha"],
	"SOC Project (t/ha)": output_years_project["SOC_t_C_ha"],
	})

combined["SOC Difference (t/ha)"] = (
	combined["SOC Project (t/ha)"] - combined["SOC Baseline (t/ha)"]
	)

combined["Delta SOC (t/ha)"] = (
	combined["SOC Difference (t/ha)"] - combined["SOC Difference (t/ha)"].shift(1)
	)

combined["ERs (tCO2e/ha)"] = (
	combined["Delta SOC (t/ha)"] * 44/12
	)

total_ERs = combined['ERs (tCO2e/ha)'].sum()

total_years = 40

avg_annual_ERs = total_ERs/total_years

print(f'\nTotal ERs: {total_ERs:.3f} tCO2e/ha')

print(f'Average annual ERs: {avg_annual_ERs:.3f} tCO2e/ha/yr')

combined.to_excel(f"{coop}_results.xlsx", index=False)



