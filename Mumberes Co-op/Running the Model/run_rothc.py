from RothC_src import *

import pandas as pd
import numpy as np
import os

#additional_c_in = 1.346656927

def run_rothc(
	starting_soil_carbon,
	total_years,
	start_year,
	clay,
	depth,
	temp,
	rain,
	evap,
	pc,
	dpm_rpm,
	carbon_input,		   # annual input
	farmyard_manure,
	carbon_input_eqm,		   # annual input
	farmyard_manure_eqm,	   # annual input
	additional_c_in,
	trm
	):
	"""
	Run RothC with user-defined parameters and return monthly and yearly outputs
	as pandas DataFrames. Optionally write them to Excel files.
	"""

	# Ensure working directory is the script directory (as in original code)
	script_dir = os.path.dirname(os.path.abspath(__file__))
	os.chdir(script_dir)
	
	additional_c_in = additional_c_in

	# Set initial pool values
	soc = starting_soil_carbon
	SOC = [soc]

	rpm = (0.1847 * soc + 0.1555) * (clay + 1.2750) ** (-0.1158)
	RPM = [rpm]
	DPM = [dpm_rpm * rpm]
	HUM = [(0.7148 * soc + 0.5069) * (clay + 0.3421) ** 0.0184]
	BIO = [(0.0140 * soc + 0.0075) * (clay + 8.8473) ** 0.0567]
	iom = 0.049 * soc ** 1.139
	IOM = [iom]

	DPM_Rage = [0.0]
	RPM_Rage = [0.0]
	BIO_Rage = [0.0]
	HUM_Rage = [0.0]
	IOM_Rage = [50000.0]

	# Initial soil water content (deficit)
	SWC = [0.0]
	TOC1 = 0.0

	# Number of monthly time steps (original: 12 + total_years * 12)
	nsteps = 12 + total_years * 12

	# Run RothC to equilibrium with baseline inputs
	k = -1
	j = -1

	SOC[0] = DPM[0] + RPM[0] + BIO[0] + HUM[0] + IOM[0]
	timeFact = 12
	test = 100.0

	target_c, baseline_soc, iters = solve_carbon_input(
			starting_soil_carbon=soc,
			clay=clay,
			temp = temp,
			rain = rain,
			evap = evap,
			starting_fym = farmyard_manure_eqm,
			pc= pc,
			total_years= total_years,
			start_year= start_year,
			tol=1e-2,
			max_iter = 50,
			c_min=0.0,
			c_max=100.0,
			trm = trm
	)

	print(f"Maintenance C-in: {target_c:.4f}")
	print(f"SOC: {baseline_soc:.4f}")
	print()	
	
	while test > 1e-6:
		k += 1
		j += 1

		if k == timeFact:
			k = 0

		TEMP = temp[k]
		RAIN = rain[k]
		PEVAP = evap[k] / 0.75
		PC = pc[k]
		DPM_RPM = dpm_rpm

		C_Inp = target_c / 12.0
		FYM_Inp = farmyard_manure_eqm / 12.0
		modernC = 1.0

		Total_Rage = [0.0]

		RothC(
			timeFact, DPM, RPM, BIO, HUM, IOM, SOC,
			DPM_Rage, RPM_Rage, BIO_Rage, HUM_Rage, Total_Rage,
			modernC, clay, depth, TEMP, RAIN, PEVAP, PC,
			DPM_RPM, C_Inp, FYM_Inp, SWC, trm
		)

		# Each year, check convergence of the active pools
		if np.mod(k + 1, timeFact) == 0:
			TOC0 = TOC1
			TOC1 = DPM[0] + RPM[0] + BIO[0] + HUM[0]
			test = abs(TOC1 - TOC0)

	# After equilibrium, start project run
	Total_Delta = (np.exp(-Total_Rage[0] / 8035.0) - 1.0) * 1000.0
	year_list = [[1, j + 1, SOC[0]]]
	month_list = []

	k = 0
	year = start_year
	month = 1
	
	c_in_applied = (target_c + additional_c_in)

	for i in range(timeFact, nsteps):
		TEMP = temp[k]
		RAIN = rain[k]
		PEVAP = evap[k] / 0.75
		PC = pc[k]
		DPM_RPM = dpm_rpm

		C_Inp = c_in_applied / 12.0
		FYM_Inp = farmyard_manure / 12.0
		modernC = 1.0

		RothC(
			timeFact, DPM, RPM, BIO, HUM, IOM, SOC,
			DPM_Rage, RPM_Rage, BIO_Rage, HUM_Rage, Total_Rage,
			modernC, clay, depth, TEMP, RAIN, PEVAP, PC,
			DPM_RPM, C_Inp, FYM_Inp, SWC, trm
		)

		Total_Delta = (np.exp(-Total_Rage[0] / 8035.0) - 1.0) * 1000.0
		
		month_list.insert(
			i - timeFact,
			[year, month, SOC[0]]
		)

		if month == timeFact:
			timeFact_index = int(i / timeFact)
			year_list.insert(
				timeFact_index,
				[year, month, SOC[0]] 
			)
			
			target_c, baseline_soc, iters = solve_carbon_input(
					starting_soil_carbon=SOC[0],
					clay=clay,
					temp = temp,
					rain = rain,
					evap = evap,
					starting_fym = farmyard_manure_eqm,
					pc= pc,
					total_years= total_years,
					start_year= start_year,
					tol=1e-2,
					max_iter = 50,
					c_min=0.0,
					c_max=100.0,
					trm = trm
					)
			
			c_in_applied = (target_c + additional_c_in)

			print(f"Maintenance C-in: {target_c:.4f}")
			print(f"C-in applied: {c_in_applied:.4f}")
			print(f"SOC: {baseline_soc:.4f}")
			print()

		k += 1
		month += 1

		if k == timeFact:
			k = 0
			month = 1
			year += 1

	output_years = pd.DataFrame(
		year_list,
		columns=[
			"Year", "Month","SOC_t_C_ha"
		]
	)

	output_months = pd.DataFrame(
		month_list,
		columns=[
			"Year", "Month","SOC_t_C_ha"
		]  
	)


	# Return dataframes for further use
	return output_months, output_years






def c_input_calculator(
	starting_soil_carbon,
	total_years,
	start_year,
	clay,
	depth,
	temp,
	rain,
	evap,
	pc,
	dpm_rpm,
	carbon_input_eqm,		   # annual input
	farmyard_manure_eqm,	   # annual input
	trm
):
	"""
	Run RothC with user-defined parameters and return monthly and yearly outputs
	as pandas DataFrames. Optionally write them to Excel files.
	"""

	# Ensure working directory is the script directory (as in original code)
	script_dir = os.path.dirname(os.path.abspath(__file__))
	os.chdir(script_dir)

	# Set initial pool values
	soc = starting_soil_carbon
	SOC = [soc]

	rpm = (0.1847 * soc + 0.1555) * (clay + 1.2750) ** (-0.1158)
	RPM = [rpm]
	DPM = [dpm_rpm * rpm]
	HUM = [(0.7148 * soc + 0.5069) * (clay + 0.3421) ** 0.0184]
	BIO = [(0.0140 * soc + 0.0075) * (clay + 8.8473) ** 0.0567]
	iom = 0.049 * soc ** 1.139
	IOM = [iom]

	DPM_Rage = [0.0]
	RPM_Rage = [0.0]
	BIO_Rage = [0.0]
	HUM_Rage = [0.0]
	IOM_Rage = [50000.0]

	# Initial soil water content (deficit)
	SWC = [0.0]
	TOC1 = 0.0

	# Number of monthly time steps (original: 12 + total_years * 12)
	nsteps = 12 + total_years * 12

	# Run RothC to equilibrium with baseline inputs
	k = -1
	j = -1

	SOC[0] = DPM[0] + RPM[0] + BIO[0] + HUM[0] + IOM[0]
	timeFact = 12
	test = 100.0

	while test > 1e-6:
		k += 1
		j += 1

		if k == timeFact:
			k = 0

		TEMP = temp[k]
		RAIN = rain[k]
		PEVAP = evap[k] / 0.75
		PC = pc[k]
		DPM_RPM = dpm_rpm

		C_Inp = carbon_input_eqm / 12.0
		FYM_Inp = farmyard_manure_eqm / 12.0
		modernC = 100.0 / 100.0

		Total_Rage = [0.0]

		RothC(
			timeFact, DPM, RPM, BIO, HUM, IOM, SOC,
			DPM_Rage, RPM_Rage, BIO_Rage, HUM_Rage, Total_Rage,
			modernC, clay, depth, TEMP, RAIN, PEVAP, PC,
			DPM_RPM, C_Inp, FYM_Inp, SWC, trm
		)

		# Each year, check convergence of the active pools
		if np.mod(k + 1, timeFact) == 0:
			TOC0 = TOC1
			TOC1 = DPM[0] + RPM[0] + BIO[0] + HUM[0]
			test = abs(TOC1 - TOC0)

	# After equilibrium, start project run
	Total_Delta = (np.exp(-Total_Rage[0] / 8035.0) - 1.0) * 1000.0
	year_list = [[1, j + 1, DPM[0], RPM[0], BIO[0], HUM[0], IOM[0], SOC[0], Total_Delta]]
	month_list = []


	return SOC[0]









def solve_carbon_input(
	starting_soil_carbon,
	clay,
	temp,
	rain,
	evap,
	starting_fym,
	pc,
	total_years,
	start_year,
	max_iter,
	tol,
	c_min,
	c_max,
	trm
):
	"""
	Find carbon_input such that baseline_soc ≈ starting_soil_carbon.
	Returns (carbon_input, baseline_soc, n_iter).
	"""

	def soc_for_input(c_in):
				
		baseline_soil_carbon = c_input_calculator(
			starting_soil_carbon=starting_soil_carbon,
			total_years=total_years,
			start_year=start_year,
			clay=clay,
			depth=30,
			temp=temp,
			rain=rain,
			evap=evap,
			pc=pc,
			dpm_rpm=1.44,
			carbon_input_eqm = c_in,		  # annual input
			farmyard_manure_eqm=starting_fym,		# annual input
			trm = trm
			)
		return baseline_soil_carbon

	# Evaluate at bounds
	soc_min = soc_for_input(c_min)
	
	soc_max = soc_for_input(c_max)
	

	# If monotonic, check that root is bracketed
	# Adjust logic if model behaves differently
	if (soc_min - starting_soil_carbon) * (soc_max - starting_soil_carbon) > 0:
		raise ValueError(
			"Baseline SOC at bounds does not bracket the target; "
			"adjust c_min and c_max."
		)

	for n in range(max_iter):
		c_mid = 0.5 * (c_min + c_max)
		soc_mid = soc_for_input(c_mid)
		diff = soc_mid - starting_soil_carbon

		if abs(diff) <= tol:
			return c_mid, soc_mid, n + 1

		# Decide which half to keep (assuming SOC increases with C input)
		if (soc_min - starting_soil_carbon) * diff < 0:
			c_max = c_mid
			soc_max = soc_mid
		else:
			c_min = c_mid
			soc_min = soc_mid

	# If max_iter reached, return best estimate
	return c_mid, soc_mid, max_iter



