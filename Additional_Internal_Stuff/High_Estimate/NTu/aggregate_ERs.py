
from run_ERs import *

master_df = pd.DataFrame()

coop = "Kabianga"

crop = "Tea"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 18.73284,
    moist_content = 1 - 1/4.5,
    harvest_index = 0.2,
    rs_ratio = 0.2,
	manure = 0.5,
	clay_content = 58.697,
	soc_content = 137.050440,
	bd_content = 1.033750,
	fao_type = 'NTu',
	coop = coop,
	S_P = 0,
	S_S = 1,
	S_R = 1,
	S_E = 1
)

master_df[crop] = results

crop = "Napier"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 296.5266,
    moist_content = 0.8,
    harvest_index = 1,
    rs_ratio = 0.5,
    manure = 0.3,
    clay_content = 58.697,
    soc_content = 137.050440,
    bd_content = 1.033750,
    fao_type = 'NTu',
    coop = coop,
    S_P = 0,
    S_S = 0,
    S_R = 1,
    S_E = 1
)

master_df[crop] = results

master_df.to_excel(f"aggregate_{coop}_results.xlsx", index=False)





coop = "Kipsigis"

master_df = pd.DataFrame()

crop = "Tea"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 20.75688,
    moist_content = 1 - 1/4.5,
    harvest_index = 0.2,
    rs_ratio = 0.2,
    manure = 0.5,
    clay_content = 58.697,
    soc_content = 137.050440,
    bd_content = 1.033750,
    fao_type = 'NTu',
    coop = coop,
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 1 
)

master_df[crop] = results

master_df.to_excel(f"aggregate_{coop}_results.xlsx", index=False)





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
    clay_content = 58.697,
    soc_content = 137.050440,
    bd_content = 1.033750,
	fao_type = 'NTu',
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
    clay_content = 58.697,
    soc_content = 137.050440,
    bd_content = 1.033750,
    fao_type = 'NTu',
	coop = 'Mumberes',
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 0
)

master_df[crop] = results

master_df.to_excel(f"aggregate_{coop}_results.xlsx", index=False)

