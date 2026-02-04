
from run_rothc import run_rothc
import pandas as pd

starting_soc = 144.0567
clay_content=58.2503

# Project model run
output_months_project, output_years_project = run_rothc(
	starting_soil_carbon=starting_soc,
	total_years=40,
	start_year=2026,
	clay=clay_content,
	depth=30,
	temp = [19.74, 20.79, 20.69, 19.51, 18.51, 17.66, 17.35, 17.85, 18.66, 18.95, 18.75, 18.79],
	rain=[112.34, 218.01, 279.67, 252.53, 313, 225.76, 233.06, 348.24, 360.77,179.14, 57.39, 63.75],
	evap=[80, 80, 88, 82, 75, 63, 57, 60, 69, 80, 77, 77],
	pc = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
	dpm_rpm = 1.44,
	carbon_input = None,			# annual input
	farmyard_manure = 0.0,
	carbon_input_eqm = None,		  # annual input
	farmyard_manure_eqm = 0.0,	   # annual input
	additional_c_in = 0.1,
	trm = 0.93
)



# Baseline model run
output_months_baseline, output_years_baseline = run_rothc(
    starting_soil_carbon=starting_soc,
    total_years=40,
    start_year=2026,
    clay=clay_content,
    depth=30,
    temp = [19.74, 20.79, 20.69, 19.51, 18.51, 17.66, 17.35, 17.85, 18.66, 18.95, 18.75, 18.79],
    rain=[112.34, 218.01, 279.67, 252.53, 313, 225.76, 233.06, 348.24, 360.77,179.14, 57.39, 63.75],
    evap=[80, 80, 88, 82, 75, 63, 57, 60, 69, 80, 77, 77],
    pc = [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
    dpm_rpm = 1.44,
    carbon_input = None,            # annual input
    farmyard_manure = 0.0,
    carbon_input_eqm = None,          # annual input
    farmyard_manure_eqm = 0.0,     # annual input
    additional_c_in = 0.1,
    trm = 1.0
)



with pd.ExcelWriter("year_results.xlsx") as writer:
	output_years_project.to_excel(writer, sheet_name="Project", index=False)
	output_years_baseline.to_excel(writer, sheet_name = "Baseline", index=False)




