
from run_ERs import *

master_df = pd.DataFrame()

coop = "Eor"

crop = "Maize"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 2.8911,
    moist_content = 0.13,
    harvest_index = 0.48,
    rs_ratio = 0.1,
	manure = 0.5,
	clay_content = 40.190164,
	soc_content = 113.941170,
	bd_content = 0.970714,
	fao_type = 'ANm',
	coop = 'Eor',
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
	clay_content = 40.190164,
    soc_content = 113.941170,
    bd_content = 0.970714,
    fao_type = 'ANm',
    coop = 'Eor',
	S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 0 
)

master_df[crop] = results

master_df.to_excel(f"aggregate_{coop}_results.xlsx", index=False)






master_df = pd.DataFrame()

coop = "Lanyuak"

crop = "Maize"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 0.607,
    moist_content = 0.13,
    harvest_index = 0.48,
    rs_ratio = 0.1,
    manure = 0.5,
    clay_content = 40.190164,
    soc_content = 113.941170,
    bd_content = 0.970714,
    fao_type = 'ANm',
    coop = coop,
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 1 
)

master_df[crop] = results


crop = "Wheat"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 0.526,
    moist_content = 0.13,
    harvest_index = 0.48,
    rs_ratio = 0.1,
    manure = 0.5,
    clay_content = 40.190164,
    soc_content = 113.941170,
    bd_content = 0.970714,
    fao_type = 'ANm',
    coop = coop,
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 1 
)

master_df[crop] = results


crop = "Barley"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 0.526,
    moist_content = 0.13,
    harvest_index = 0.48,
    rs_ratio = 0.1,
    manure = 0.5,
    clay_content = 40.190164,
    soc_content = 113.941170,
    bd_content = 0.970714,
    fao_type = 'ANm',
    coop = coop,
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 1 
)

master_df[crop] = results


crop = "Potato"
results = run_ER_by_crop(
    crop_type = crop,
    crop_yield = 20.2343,
    moist_content = 0.75,
    harvest_index = 0.75,
    rs_ratio = 0.2,
    manure = 0.5,
    clay_content = 40.190164,
    soc_content = 113.941170,
    bd_content = 0.970714,
    fao_type = 'ANm',
    coop = 'Eor',
    S_P = 0,
    S_S = 1,
    S_R = 1,
    S_E = 0
)

master_df[crop] = results

master_df.to_excel(f"aggregate_{coop}_results.xlsx", index=False)










