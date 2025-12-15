
from run_rothc import run_rothc

run_rothc(
    starting_soil_carbon=75.5463,
    clay= 26.5882,
    temp=[28.03, 28.23, 28.99, 28.81, 27.48, 26.32, 25.21, 25.33, 25.85, 26.91, 27.89, 28.33], 
    rain=[58.92, 34.15, 90.21, 147.31, 198.2, 50.81, 59.89, 54.71, 58.92, 58.92, 159.12, 189.65],
    evap=[155, 144, 160, 147, 135, 114, 107, 107, 112, 140, 146, 154],
	total_years=40,
    start_year=2026,
	depth=30,
    pc=[0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 0, 0],
    dpm_rpm=1.44,
    carbon_input_project=18.505859375,          # annual input
    farmyard_manure_project=5.0,
    carbon_input_baseline = 18.505859375,         # annual input
    farmyard_manure_baseline=5.0,      # annual input
    month_output_path="month_results.xlsx",
    year_output_path="year_results.xlsx",
    write_files=True
)
