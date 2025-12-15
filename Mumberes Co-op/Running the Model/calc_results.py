
from run_rothc import run_rothc

run_rothc(
    starting_soil_carbon=131.63,
    total_years=40,
    start_year=2026,
    clay=59.63,
    depth=30,
    temp=None,
    rain=None,
    evap=None,
    pc=None,
    dpm_rpm=1.44,
    carbon_input_project=18.505859375,          # annual input
    farmyard_manure_project=5.0,
    carbon_input_baseline = 18.505859375,         # annual input
    farmyard_manure_baseline=5.0,      # annual input
    month_output_path="month_results.xlsx",
    year_output_path="year_results.xlsx",
    write_files=True
)
