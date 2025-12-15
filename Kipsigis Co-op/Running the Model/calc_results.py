
from run_rothc import run_rothc

run_rothc(
    starting_soil_carbon=132.1675,
	total_years=40,
    start_year=2026,
    clay=56.4456,
	depth=30,
    temp=[19.73, 20.81, 20.38, 18.79, 17.92, 17.06, 16.8, 17.52, 18.5, 18.83, 18.65, 18.77],
    rain=[134.45, 123.65, 342.27, 563.29, 523.71, 331.1, 253.13, 377.23, 363.2, 416.76, 409.37, 244.8],
    evap=[80, 80, 88, 82, 75, 63, 57, 60, 69, 80, 77, 77],
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
