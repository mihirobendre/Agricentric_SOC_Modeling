
from run_rothc import run_rothc

run_rothc(
    starting_soil_carbon=109.4188,
    total_years=40,
    start_year=2026,
    clay=40.6063,
    depth=30,
    temp=[19.77, 20.55, 20.56, 19.22, 18.23, 17.6, 17.6, 18.25, 19.04, 19.87, 19.62, 19.33],
    rain=[165.56, 125.3, 248.43, 358.69, 151.28, 133.89, 81.28, 107.27, 107.88,166.75, 247.22, 236.94],
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
