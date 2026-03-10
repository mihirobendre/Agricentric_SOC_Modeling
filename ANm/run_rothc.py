"""
RothC_run.py  —  Modified RothC run and equilibrium functions
==============================================================

WHAT THIS FILE IS
-----------------
This is the run-control layer for the RothC model.	It contains three
functions:

  run_rothc()		   — spins the model to equilibrium then runs a
						 forward project simulation, returning monthly
						 and annual output DataFrames.

  c_input_calculator() — helper that runs only the equilibrium spin-up
						 and returns the resulting equilibrium SOC for a
						 given annual C input rate.

  solve_carbon_input() — bisection solver that finds the C input which
						 produces the observed starting SOC at equilibrium.

WHAT HAS BEEN MODIFIED (vs document 3 / the original script)
-------------------------------------------------------------
All three modifications flow from adding the HUM saturation cap described
in RothC_src.py.  No logic unrelated to saturation has been changed.

  MODIFICATION 1 — compute_cx() called at start of run_rothc()
				   and c_input_calculator()
	Cx_mgha (the mineralogy-adjusted HUM pool ceiling in Mg C/ha) is
	computed once from the site inputs and then passed into every RothC()
	call throughout that function.	This single value drives the entire
	saturation mechanism inside decomp() in RothC_src.py.

  MODIFICATION 2 — Three new parameters added to all three functions
		fao_type : str	 — FAO soil type code, e.g. "NTu", "ANm"
		bd		 : float — bulk density in g/cm³
		depth	 : float — soil depth in cm
	fao_type and bd are needed by compute_cx() to apply the correct
	mineralogy multiplier and convert Cx from g/kg to Mg/ha.
	depth was previously hardcoded to 30 inside solve_carbon_input();
	it is now an explicit parameter so the function is general.

  MODIFICATION 3 — Output DataFrames gain three new columns
		HUM_t_C_ha	— HUM pool value in Mg C/ha at each timestep
		sat_ratio	— HUM / Cx_mgha (0 = empty, 1 = at ceiling)
		eps_eff		— effective HUM transfer efficiency = 0.54 × (1 – sat_ratio)

  WHY APPLY THE CAP IN THE SPIN-UP AS WELL AS THE FORWARD RUN?
  -------------------------------------------------------------
  It might seem sufficient to only apply the saturation cap in the forward
  (project) simulation.  However, if the spin-up were run without the cap,
  the equilibrium HUM pool could exceed Cx_mgha.  The first timestep of the
  project run would then apply a large correction — HUM is suddenly above its
  ceiling — producing a sharp, unrealistic drop in SOC.  By applying Cx_mgha
  consistently in both spin-up and forward run, the equilibrium HUM value is
  already physically bounded and the transition is smooth.

  WHY TRACK sat_ratio AND eps_eff IN OUTPUT?
  ------------------------------------------
  At the five project cooperatives, current measured saturation ratios are
  0.04–0.13 (4–13% of capacity used).  This means the cap has negligible
  effect on near-term projections.	Tracking these values in the output lets
  you:
	• Confirm the cap is not activating prematurely (a quality-control check)
	• Show transparently in reports at what year and cooperative the
	  saturation constraint begins to suppress sequestration
	• Satisfy MRV (measurement, reporting, verification) requirements that
	  model assumptions are documented and traceable over time

KEY REFERENCES
--------------
  Hassink (1997)	   — Source of the Cx formula
  Six et al. (2002)    — Saturation concept; silt+clay fraction saturates asymptotically
  White et al. (2014)  — ε-regulation method and N-mineralisation implications
  Torn et al. (1997)   — Mineralogy and organic matter stabilisation
  Matus et al. (2014)  — Andosol allophane/imogolite stabilisation capacity
"""

from RothC_src import *

import pandas as pd
import numpy as np
import os


# ===========================================================================
# run_rothc
# ===========================================================================
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
	carbon_input,		   # annual plant C input for the project period
	farmyard_manure,	   # annual FYM C input for the project period
	carbon_input_eqm,	   # annual plant C input for equilibrium spin-up
	farmyard_manure_eqm,   # annual FYM C input for equilibrium spin-up
	additional_c_in,
	trm,
	# ------------------------------------------------------------------
	# NEW PARAMETERS — required for the saturation modification
	# ------------------------------------------------------------------
	fao_type,
	# FAO soil type code for the mineralogy correction.
	# Must match a key in MINERALOGY_MULT (defined in RothC_src.py).
	# Project values:
	#	Mumberes / Kabianga / Kipsigis → "NTu"	(or "NTh" for humic subset)
	#	Lanyuak / Eor Emayian		   → "ANm"
	bd,
	# Bulk density in g/cm³, measured from 0–30 cm composite samples.
	# Used to convert Cx from g C/kg soil to Mg C/ha.
	# Project measured averages:
	#	Mumberes: 1.021   Kabianga: 1.005	Kipsigis: 1.087
	#	Lanyuak:  0.977   Eor Emayian: 0.966
	):
	"""
	Run RothC with user-defined parameters and return monthly and yearly outputs
	as pandas DataFrames. Optionally write them to Excel files.

	This function first spins the model to equilibrium using carbon_input_eqm
	and farmyard_manure_eqm, then runs forward for total_years using the
	project-period inputs carbon_input and farmyard_manure.

	PARAMETERS
	----------
	starting_soil_carbon  : float — observed baseline SOC [Mg C/ha]
	total_years			  : int   — number of years to simulate after spin-up
	start_year			  : int   — calendar year at start of forward run
	clay				  : float — clay content in % (0–100)
	depth				  : float — soil depth in cm (typically 30)
	temp				  : list  — 12-element monthly mean temperature [°C]
	rain				  : list  — 12-element monthly rainfall [mm]
	evap				  : list  — 12-element monthly potential evaporation [mm]
	pc					  : list  — 12-element plant cover flag (0=bare, 1=covered)
	dpm_rpm				  : float — DPM:RPM ratio for incoming plant material
									 (mixed farming/grassland ≈ 1.44; forest ≈ 0.25)
	carbon_input		  : float or None — annual plant C input [Mg C/ha/yr]
							 for project period.  Pass None to solve automatically.
	farmyard_manure		  : float — annual FYM C input [Mg C/ha/yr] project period
	carbon_input_eqm	  : float or None — annual plant C input for spin-up.
							 Pass None to solve automatically.
	farmyard_manure_eqm   : float — annual FYM C input for spin-up
	additional_c_in		  : float — additional C input term (currently unused)
	trm					  : float — tillage/management rate modifier (1.0 = no effect)
	fao_type			  : str   — FAO soil type code (new; see above)
	bd					  : float — bulk density in g/cm³ (new; see above)

	RETURNS
	-------
	output_months : DataFrame — monthly SOC, HUM, sat_ratio, eps_eff
	output_years  : DataFrame — annual	SOC, HUM, sat_ratio, eps_eff
	"""

	# Ensure working directory is the script directory (as in original code)
	script_dir = os.path.dirname(os.path.abspath(__file__))
	os.chdir(script_dir)

	# ------------------------------------------------------------------
	# MODIFICATION 1: Compute the mineralogy-adjusted HUM pool ceiling
	# ------------------------------------------------------------------
	# compute_cx() is defined in RothC_src.py.	It applies the Hassink (1997)
	# formula and then scales it by a mineralogy multiplier appropriate for
	# the FAO soil type.  The result, Cx_mgha, is the maximum amount of
	# carbon the HUM pool can hold given the soil's mineral surface capacity.
	#
	# This value is computed ONCE here and passed unchanged into every RothC()
	# call below — both during the equilibrium spin-up and the forward run.
	# See RothC_src.py → compute_cx() for full derivation and justification.
	#
	# Project reference values (mineralogy-adjusted, measured BD):
	#	Mumberes:	 ~113 Mg C/ha	(NTu ×0.85, BD=1.021)
	#	Kabianga:	 ~110 Mg C/ha	(NTu ×0.85, BD=1.005)
	#	Kipsigis:	 ~117 Mg C/ha	(NTu ×0.85, BD=1.087)
	#	Lanyuak:	 ~264 Mg C/ha	(ANm ×2.50, BD=0.977)
	#	Eor Emayian: ~263 Mg C/ha	(ANm ×2.50, BD=0.966)
	Cx_mgha, cx_gkg, mult = compute_cx(clay, bd, depth, fao_type)
	'''
	print(
		f"[run_rothc] Saturation SOC (Cx) computed: {Cx_mgha:.1f} Mg C/ha "
		#f"(Cx_adj={cx_gkg:.1f} g/kg, mineralogy mult={mult:.2f} for '{fao_type}')"
	)
	'''
	# ------------------------------------------------------------------
	# Set initial pool values  (unchanged from original)
	# ------------------------------------------------------------------
	# These empirical equations (Falloon et al. 1998; Coleman & Jenkinson 1996)
	# partition the observed total SOC across the five active pools as a
	# starting guess.  The equilibrium spin-up then re-distributes them.
	if starting_soil_carbon < Cx_mgha:
		soc = starting_soil_carbon
	else:
		soc = Cx_mgha
	
	SOC = [soc]

	rpm = (0.1847 * soc + 0.1555) * (clay + 1.2750) ** (-0.1158)
	RPM = [rpm]
	DPM = [dpm_rpm * rpm]
	HUM = [(0.7148 * soc + 0.5069) * (clay + 0.3421) ** 0.0184]
	BIO = [(0.0140 * soc + 0.0075) * (clay + 8.8473) ** 0.0567]
	iom = 0.049 * soc ** 1.139	 # Jenkinson (1977) IOM equation
	IOM = [iom]

	DPM_Rage = [0.0]
	RPM_Rage = [0.0]
	BIO_Rage = [0.0]
	HUM_Rage = [0.0]
	IOM_Rage = [50000.0]	# IOM is effectively radiocarbon-dead

	# Initial soil water content (deficit)
	SWC = [0.0]
	TOC1 = 0.0

	# Number of monthly time steps (original: 12 + total_years * 12)
	nsteps = 12 + total_years * 12

	# Run RothC to equilibrium with baseline inputs
	k = -1
	j = -1

	SOC[0] = DPM[0] + RPM[0] + BIO[0] + HUM[0] + IOM[0]   # from orig RothC code
	timeFact = 12
	test = 100.0

	carbon_input_applied = carbon_input_eqm

	if carbon_input_eqm is None:
		# solve_carbon_input() now receives fao_type, bd, and depth so that
		# the saturation cap is consistent inside the bisection search.
		# See solve_carbon_input() below for explanation of why this matters.
		target_c, baseline_soc, iters = solve_carbon_input(
				starting_soil_carbon=soc,
				clay=clay,
				depth=depth,			# was hardcoded to 30 in the original
				temp=temp,
				rain=rain,
				evap=evap,
				starting_fym=farmyard_manure_eqm,
				pc=pc,
				total_years=total_years,
				start_year=start_year,
				tol=1e-2,
				max_iter=50,
				c_min=0.0,
				c_max=100.0,
				trm=trm,
				fao_type=fao_type,		# NEW
				bd=bd,					# NEW
				)

		carbon_input_applied = target_c

	# ------------------------------------------------------------------
	# EQUILIBRIUM SPIN-UP LOOP	(structure unchanged; Cx_mgha added)
	# ------------------------------------------------------------------
	# The model runs on repeat 12-month cycles until the total active carbon
	# (DPM+RPM+BIO+HUM) changes by less than 1×10⁻⁶ Mg/ha between years.
	# That convergence criterion is unchanged.
	#
	# The only change is that RothC() now receives Cx_mgha as its final
	# argument.  This passes through to decomp() in RothC_src.py where the
	# saturation-regulated ε_eff is calculated.  Running the cap during
	# spin-up ensures that the equilibrium HUM value is already physically
	# bounded — preventing an artificial step-change at the start of the
	# project run if the uncapped HUM would have been above Cx_mgha.
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

		C_Inp = carbon_input_applied / 12.0
		FYM_Inp = farmyard_manure_eqm / 12.0
		modernC = 1.0

		Total_Rage = [0.0]

		# MODIFIED call: Cx_mgha added as the final argument.
		# RothC() signature is now:
		#	RothC(...all original args..., Cx_mgha)
		# The returned sat_ratio is discarded during spin-up — we only need
		# convergence here, not timestep diagnostics.
		RothC(
			timeFact, DPM, RPM, BIO, HUM, IOM, SOC,
			DPM_Rage, RPM_Rage, BIO_Rage, HUM_Rage, Total_Rage,
			modernC, clay, depth, TEMP, RAIN, PEVAP, PC,
			DPM_RPM, C_Inp, FYM_Inp, SWC, trm,
			Cx_mgha		 # NEW — HUM pool ceiling passed to decomp()
		)

		# Each year, check convergence of the active pools	(unchanged)
		if np.mod(k + 1, timeFact) == 0:
			TOC0 = TOC1
			TOC1 = DPM[0] + RPM[0] + BIO[0] + HUM[0]
			test = abs(TOC1 - TOC0)

	# After equilibrium, start project run	(unchanged line)
	Total_Delta = (np.exp(-Total_Rage[0] / 8035.0) - 1.0) * 1000.0

	# ------------------------------------------------------------------
	# Initialise output lists with the equilibrium state
	# ------------------------------------------------------------------
	# MODIFIED: year_list now stores HUM, sat_ratio, and eps_eff alongside
	# SOC.	The equilibrium saturation ratio is logged here so the output
	# DataFrame begins at t=0 with meaningful diagnostic values.
	initial_sat = HUM[0] / Cx_mgha
	'''
	print(
		f"[run_rothc] Spin-up converged after {j + 1} steps.  "
		f"Equilibrium HUM={HUM[0]:.2f} Mg/ha, "
		f"sat_ratio={initial_sat:.4f} ({initial_sat*100:.1f}% of Cx)"
	)
	'''

	year_list = [[1, j + 1, SOC[0], HUM[0], initial_sat, 0.54 * (1.0 - initial_sat)]]
	month_list = []

	k = 0
	year = start_year
	month = 1

	carbon_input_applied = carbon_input

	if carbon_input is None:
		target_c, baseline_soc, iters = solve_carbon_input(
			starting_soil_carbon=SOC[0],
			clay=clay,
			depth=depth,			# was hardcoded to 30 in the original
			temp=temp,
			rain=rain,
			evap=evap,
			starting_fym=farmyard_manure_eqm,
			pc=pc,
			total_years=total_years,
			start_year=start_year,
			tol=1e-2,
			max_iter=50,
			c_min=0.0,
			c_max=100.0,
			trm=trm,
			fao_type=fao_type,		# NEW
			bd=bd,					# NEW
			)

		carbon_input_applied = target_c

	# ------------------------------------------------------------------
	# PROJECT SIMULATION LOOP  (structure unchanged; Cx_mgha added)
	# ------------------------------------------------------------------
	for i in range(timeFact, nsteps):
		TEMP = temp[k]
		RAIN = rain[k]
		PEVAP = evap[k] / 0.75
		PC = pc[k]
		DPM_RPM = dpm_rpm

		C_Inp = carbon_input_applied / 12.0
		FYM_Inp = farmyard_manure / 12.0
		modernC = 1.0

		# MODIFIED call: Cx_mgha added.  RothC() now returns sat_ratio
		# (the HUM/Cx ratio at the START of this timestep), which we
		# record in the output for diagnostic and reporting purposes.
		sat_ratio = RothC(
			timeFact, DPM, RPM, BIO, HUM, IOM, SOC,
			DPM_Rage, RPM_Rage, BIO_Rage, HUM_Rage, Total_Rage,
			modernC, clay, depth, TEMP, RAIN, PEVAP, PC,
			DPM_RPM, C_Inp, FYM_Inp, SWC, trm,
			Cx_mgha		 # NEW — HUM pool ceiling passed to decomp()
		)

		Total_Delta = (np.exp(-Total_Rage[0] / 8035.0) - 1.0) * 1000.0

		# Effective HUM transfer efficiency this timestep.
		# Equal to the standard 0.54 when sat_ratio ≈ 0.
		# Approaches 0.0 as HUM nears Cx_mgha.
		eps_eff_val = 0.54 * (1.0 - sat_ratio)

		# MODIFIED: month_list now includes HUM, sat_ratio, eps_eff
		month_list.insert(
			i - timeFact,
			[year, month, SOC[0], HUM[0], sat_ratio, eps_eff_val]
		)

		if month == timeFact:
			timeFact_index = int(i / timeFact)
			# MODIFIED: year_list now includes HUM, sat_ratio, eps_eff
			year_list.insert(
				timeFact_index,
				[year, month, SOC[0], HUM[0], sat_ratio, eps_eff_val]
			)
			'''	
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

			carbon_input_applied = target_c
			'''
		k += 1
		month += 1

		if k == timeFact:
			k = 0
			month = 1
			year += 1

	# ------------------------------------------------------------------
	# BUILD OUTPUT DATAFRAMES  (MODIFIED column set)
	# ------------------------------------------------------------------
	# New columns vs original:
	#
	#	HUM_t_C_ha	— The mineral-protected humic pool in Mg C/ha.
	#				  This is the pool directly affected by the saturation
	#				  cap.	Monitoring it shows whether and when HUM
	#				  approaches the Cx ceiling.
	#
	#	sat_ratio	— HUM / Cx_mgha at each timestep.  Range [0, 1].
	#				  At the five project cooperatives, this starts at
	#				  0.04–0.13.  A value approaching 1.0 would indicate
	#				  the mineral surfaces are nearly fully occupied.
	#
	#	eps_eff		— Effective HUM transfer efficiency = 0.54 × (1 – sat_ratio).
	#				  Equal to 0.54 (the standard RothC value) when far from
	#				  saturation.  Decreases toward 0 as HUM approaches Cx.
	#				  When eps_eff < 0.54, the 'missing' efficiency is
	#				  redirected to CO₂ (see decomp() in RothC_src.py).
	output_years = pd.DataFrame(
		year_list,
		columns=[
			"Year", "Month", "SOC_t_C_ha", "HUM_t_C_ha", "sat_ratio", "eps_eff"
		]
	)

	output_months = pd.DataFrame(
		month_list,
		columns=[
			"Year", "Month", "SOC_t_C_ha", "HUM_t_C_ha", "sat_ratio", "eps_eff"
		]
	)

	# Return dataframes for further use  (unchanged)
	return output_months, output_years


# ===========================================================================
# c_input_calculator
# ===========================================================================
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
	carbon_input_eqm,	   # annual input
	farmyard_manure_eqm,   # annual input
	trm,
	# ------------------------------------------------------------------
	# NEW PARAMETERS — required for the saturation modification
	# ------------------------------------------------------------------
	fao_type,
	# FAO soil type code.  Passed to compute_cx() to apply the correct
	# mineralogy multiplier.  Must match a key in MINERALOGY_MULT.
	bd,
	# Bulk density in g/cm³.  Passed to compute_cx() for unit conversion.
):
	"""
	Run RothC with user-defined parameters and return monthly and yearly outputs
	as pandas DataFrames. Optionally write them to Excel files.

	This function runs only the equilibrium spin-up (no forward project run)
	and returns the equilibrium SOC value.	It is called repeatedly by
	solve_carbon_input() during the bisection search.

	MODIFICATION
	------------
	compute_cx() is called here so that the saturation cap is active during
	the equilibrium spin-up.  This ensures the equilibrium SOC found by the
	bisection solver is consistent with what run_rothc() will produce — both
	use the same physical HUM ceiling.	If the cap were absent here but present
	in run_rothc(), the solver would converge on a C input that produces a
	slightly different SOC than the target, introducing an initialisation error.
	"""

	# Ensure working directory is the script directory (as in original code)
	script_dir = os.path.dirname(os.path.abspath(__file__))
	os.chdir(script_dir)

	# ------------------------------------------------------------------
	# MODIFICATION: Compute Cx_mgha for use throughout this function
	# ------------------------------------------------------------------
	# Identical call to the one in run_rothc().  Must use the same fao_type
	# and bd so the equilibrium and forward runs share the same ceiling.
	Cx_mgha, _, _ = compute_cx(clay, bd, depth, fao_type)

	# Set initial pool values  (unchanged from original)
	if starting_soil_carbon < Cx_mgha:
		soc = starting_soil_carbon
	else:
		soc = Cx_mgha
	
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
		modernC = 100.0 / 100.0   # unchanged from original

		Total_Rage = [0.0]

		# MODIFIED call: Cx_mgha added as the final argument.
		# The saturation cap is active even in this equilibrium-only helper.
		RothC(
			timeFact, DPM, RPM, BIO, HUM, IOM, SOC,
			DPM_Rage, RPM_Rage, BIO_Rage, HUM_Rage, Total_Rage,
			modernC, clay, depth, TEMP, RAIN, PEVAP, PC,
			DPM_RPM, C_Inp, FYM_Inp, SWC, trm,
			Cx_mgha		 # NEW — HUM pool ceiling passed to decomp()
		)

		# Each year, check convergence of the active pools	(unchanged)
		if np.mod(k + 1, timeFact) == 0:
			TOC0 = TOC1
			TOC1 = DPM[0] + RPM[0] + BIO[0] + HUM[0]
			test = abs(TOC1 - TOC0)

	# After equilibrium, start project run	(unchanged lines)
	Total_Delta = (np.exp(-Total_Rage[0] / 8035.0) - 1.0) * 1000.0
	year_list = [[1, j + 1, DPM[0], RPM[0], BIO[0], HUM[0], IOM[0], SOC[0], Total_Delta]]
	month_list = []

	return SOC[0]


# ===========================================================================
# solve_carbon_input
# ===========================================================================
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
	trm,
	# ------------------------------------------------------------------
	# NEW PARAMETERS — required for the saturation modification
	# ------------------------------------------------------------------
	fao_type,
	# FAO soil type code.  Threaded through to c_input_calculator() →
	# compute_cx() so the saturation cap is active during bisection.
	bd,
	# Bulk density in g/cm³.  Threaded through to compute_cx().
	depth=30,
	# Soil depth in cm.  Was hardcoded to 30 inside this function in the
	# original code.  Promoted to an explicit parameter so the function is
	# general and consistent with run_rothc() which uses the depth argument.
):
	"""
	Find carbon_input such that baseline_soc ≈ starting_soil_carbon.
	Returns (carbon_input, baseline_soc, n_iter).

	HOW THE BISECTION WORKS
	-----------------------
	The equilibrium SOC increases monotonically with annual C input (more C
	in → more C stored at steady state).  We evaluate the equilibrium SOC at
	c_min and c_max and verify that starting_soil_carbon lies between them.
	We then repeatedly halve the interval, keeping the half that brackets
	the target, until the equilibrium SOC is within tol Mg/ha of the target.

	MODIFICATION
	------------
	fao_type, bd, and depth are new parameters that are threaded into
	c_input_calculator() → compute_cx().  This is necessary so that the
	bisection search finds the C input that produces the target SOC in a
	model that applies the saturation cap — the same model that run_rothc()
	uses for the forward projection.

	Without this, the solver would find the equilibrium C input for an
	uncapped model, and the initialisation SOC in run_rothc() would be
	slightly inconsistent with starting_soil_carbon once the cap is active.

	depth was previously hardcoded to 30 inside this function.	It is now
	an explicit parameter so that non-standard depths (e.g. 20 cm composites
	from a subset of sites) can be handled without modifying source code.
	"""
	Cx_mgha, _, _ = compute_cx(clay, bd, depth, fao_type)

	# Set initial pool values  (unchanged from original)
	if starting_soil_carbon < Cx_mgha:
		soc = starting_soil_carbon
	else:
		soc = Cx_mgha

	starting_soil_carbon = soc


	def soc_for_input(c_in):
		# c_input_calculator() now receives fao_type, bd, and depth.
		# The saturation cap is therefore active throughout every call
		# made by this bisection loop.
		baseline_soil_carbon = c_input_calculator(
			starting_soil_carbon=soc,
			total_years=total_years,
			start_year=start_year,
			clay=clay,
			depth=depth,			# was hardcoded to 30 in the original
			temp=temp,
			rain=rain,
			evap=evap,
			pc=pc,
			dpm_rpm=1.44,
			carbon_input_eqm=c_in,
			farmyard_manure_eqm=starting_fym,
			trm=trm,
			fao_type=fao_type,		# NEW
			bd=bd,					# NEW
			)
		return baseline_soil_carbon
	
	# Evaluate at bounds  (unchanged logic)
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

	# If max_iter reached, return best estimate  (unchanged)
	return c_mid, soc_mid, max_iter
