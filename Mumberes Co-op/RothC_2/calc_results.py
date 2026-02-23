
from run_rothc import run_rothc

run_rothc(
    starting_soil_carbon=131.63,
    total_years=40,
    start_year=2026,
    clay=59.63,
    depth=30,
    temp=[19.74, 20.79, 20.69, 19.51, 18.51, 17.66, 17.35, 17.85, 18.66, 18.95, 18.75, 18.79],
    rain=[112.34, 218.01, 279.67, 252.53, 313, 225.76, 233.06, 348.24, 360.77,179.14, 57.39, 63.75],
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
