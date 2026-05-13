
from run_ERs import *

master_df = pd.DataFrame()

coop = "Mumberes"

crop = "Maize"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 7.413,
    moist_content = 0.13,
    harvest_index = 0.48,
    rs_ratio = 0.1,
	manure = 0.5,
	clay_content = 59.623077,
	soc_content = 119.082923,
	bd_content = 1.015000,
	fao_type = 'NTh',
	coop = 'Mumberes',
	S_P = 0,
	S_S = 1,
	S_R = 1,
	S_E = 1
)

master_df[crop] = results

crop = "Potato"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 4.448,
    moist_content = 0.75,
    harvest_index = 0.75,
    rs_ratio = 0.2,
    manure = 0.5,
    clay_content = 59.623077,
    soc_content = 119.082923,
    bd_content = 1.015000,
    fao_type = 'NTh',
    coop = 'Mumberes',
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 0 
)

master_df[crop] = results

master_df.to_excel(f"aggregate_{coop}_results.xlsx", index=False)



