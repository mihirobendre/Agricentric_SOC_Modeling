"""
RothC_src.py  —  Modified RothC source functions
=================================================

WHAT THIS FILE IS
-----------------
This is the core RothC engine: rate-modifying factors, the decomposition step,
and the top-level RothC() function that runs one monthly timestep.

WHAT HAS BEEN MODIFIED (vs the original)
-----------------------------------------
Two additions have been made to incorporate carbon saturation of the HUM pool:

  1.  A mineralogy-adjusted Cx calculation  (compute_cx)
      The Hassink (1997) formula gives the maximum protective carbon capacity
      of a soil based on clay content.  However, it was calibrated on temperate
      soils with smectite/illite mineralogy.  The soils in this project have
      very different clay minerals, so a multiplier is applied per FAO soil
      type before the Cx value is used.

  2.  Saturation-regulated HUM transfer efficiency in decomp()
      Standard RothC uses a fixed efficiency ε = 0.54, meaning 54% of each
      pool's decomposed carbon flows into HUM and 46% into BIO.  This allows
      HUM to grow without bound.  The modification (White et al. 2014,
      following Hassink 1997 and Six et al. 2002) replaces the fixed ε with:

          ε_eff = ε × (1 − HUM / Cx)

      As HUM approaches Cx, ε_eff → 0 and all C that would have gone to HUM
      is instead respired as CO₂.  BIO transfer (0.46) is unaffected — BIO
      is a biologically active pool, not a mineral-protected one.

      Mass balance is preserved:  CO₂ fraction increases by exactly the amount
      that HUM fraction decreases.

KEY REFERENCES
--------------
  Hassink (1997)       — Source of the Cx formula
  Six et al. (2002)    — Saturation concept; silt+clay fraction saturates asymptotically
  White et al. (2014)  — ε-regulation method and N-mineralisation implications
  Torn et al. (1997)   — Mineralogy and organic matter stabilisation
  Matus et al. (2014)  — Andosol allophane/imogolite stabilisation capacity
"""

import pandas as pd
import numpy as np


# ---------------------------------------------------------------------------
# MINERALOGY MULTIPLIERS
# ---------------------------------------------------------------------------
# These scale the raw Hassink Cx formula to account for the clay mineral
# type present in each FAO soil class.  The raw formula was calibrated on
# smectite/illite-dominated temperate soils.
#
# Explanation of each value:
#
#   NTu / NTh  (Nitisol — haplic/humic)
#     Dominant mineral: kaolinite  (~15 m²/g surface area)
#     Kaolinite has far lower specific surface area than smectite (~800 m²/g),
#     so the raw Hassink formula over-predicts protective capacity.
#     Iron/aluminium sesquioxides in Nitisols partially compensate, but not
#     fully.  A –15% correction is applied.
#     → multiplier = 0.85  (Rasmussen et al. 2006; Torn et al. 1997)
#
#   ANm  (Andosol — allophanic)
#     Dominant minerals: allophane and imogolite  (700–1200 m²/g)
#     These short-range-order minerals have exceptionally high surface area
#     and reactivity.  They bind organic carbon far more strongly than
#     kaolinite or even smectite.  Hassink's formula based on clay% alone
#     dramatically under-estimates Cx for Andosols.
#     A ×2.5 multiplier is used as the central estimate; the true range is
#     broadly 2–4×.  For sensitivity analysis, test 2.0× and 3.5× as bounds.
#     → multiplier = 2.50  (Matus et al. 2014; Basile-Doelsch et al. 2005)
#
#   VRe  (Vertisol — smectitic)
#     Dominant mineral: smectite  (~800 m²/g)
#     This is actually close to the soils Hassink calibrated on, but the
#     very high clay content of Vertisols means the raw formula still
#     slightly under-predicts.  +40% is applied.
#     → multiplier = 1.40  (Hassink & Whitmore 1997; Six et al. 2002)
#
#   ARl  (Arenosol — sandy)
#     Low clay, low surface area.  The Hassink formula captures this
#     correctly at face value — no adjustment needed.
#     → multiplier = 1.00
#
#   FRx  (Ferralsol)
#     Similar to Nitisol: kaolinite + high Fe/Al oxide content.
#     Stable micro-aggregates but lower clay% in our dataset.
#     Slight downward adjustment applied.
#     → multiplier = 0.90  (Torn et al. 1997)

MINERALOGY_MULT = {
    "NTu": 0.85,   # Nitisol (haplic/humic) — Mumberes, Kabianga, Kipsigis
    "NTh": 0.85,   # Nitisol (humic)         — Mumberes subset
    "ANm": 2.50,   # Andosol (allophanic)    — Lanyuak, Eor Emayian
    "VRe": 1.40,   # Vertisol (smectite)
    "ARl": 1.00,   # Arenosol (sandy)
    "FRx": 0.90,   # Ferralsol
}

# Site-level reference values for convenience — these are the mineralogy-adjusted
# Cx values derived from measured clay% and bulk density in the project dataset.
# They are NOT hard-coded into the model; compute_cx() recalculates them from
# first principles using your measured inputs.  These are here for quick sanity
# checks only.
#
#   Cooperative     FAO type   Clay%   BD (g/cm³)   Cx_adj (Mg C/ha)
#   Mumberes        NTu/NTh    59.8    1.021        ~113
#   Kabianga        NTu        58.3    1.005        ~110
#   Kipsigis        NTu        56.4    1.087        ~117
#   Lanyuak         ANm        39.7    0.977        ~264
#   Eor Emayian     ANm        40.6    0.966        ~263


# ---------------------------------------------------------------------------
# INITIAL POOL VALUES (global lists — unchanged from original)
# ---------------------------------------------------------------------------
DPM_Rage = [0.0]
RPM_Rage = [0.0]
BIO_Rage = [0.0]
HUM_Rage = [0.0]
IOM_Rage = [50000.0]


# ---------------------------------------------------------------------------
# NEW FUNCTION: compute_cx
# ---------------------------------------------------------------------------
def compute_cx(clay_pct, bd, depth_cm, fao_type):
    """
    Calculate the mineralogy-adjusted maximum protective carbon capacity (Cx)
    of the HUM pool, in Mg C ha⁻¹.

    WHY THIS MATTERS
    ----------------
    Cx is the ceiling for the HUM pool only — not for total SOC.
    Total SOC = DPM + RPM + BIO + HUM + IOM.  DPM, RPM, and BIO are
    biologically cycled fractions not constrained by mineral surfaces.
    IOM is inert recalcitrant carbon (Jenkinson 1977 equation: 0.049 × SOC^1.139).
    Only HUM is limited by the mineral protection capacity Cx.

    HOW IT IS CALCULATED
    --------------------
    Step 1 — Hassink (1997) formula in g C per kg soil:
        Cx_raw = 21.1 + 37.5 × clay_fraction

    Step 2 — Mineralogy adjustment:
        Cx_adj = Cx_raw × MINERALOGY_MULT[fao_type]
        (see MINERALOGY_MULT dictionary above for justification of each value)

    Step 3 — Convert from g C kg⁻¹ to Mg C ha⁻¹:
        Cx_mgha = Cx_adj × BD × depth_cm × 0.1
        (factor 0.1 converts: g/kg × g/cm³ × cm → Mg/ha)

    PARAMETERS
    ----------
    clay_pct  : float  — clay content in % (0–100), as used throughout RothC
    bd        : float  — bulk density in g/cm³ (measured, 0–30 cm composite)
    depth_cm  : float  — soil depth in cm (typically 30 for 0–30 cm composites)
    fao_type  : str    — FAO soil type code, e.g. "NTu", "ANm".  Must be a key
                         in MINERALOGY_MULT.  If not recognised, 1.0 is used
                         and a warning is printed.

    RETURNS
    -------
    cx_mgha     : float — HUM pool ceiling in Mg C ha⁻¹
    cx_gkg      : float — HUM pool ceiling in g C kg⁻¹ (useful for diagnostics)
    mult        : float — the mineralogy multiplier that was applied
    """

    clay_frac = clay_pct / 100.0

    # Step 1: Hassink raw formula
    cx_raw_gkg = 21.1 + 37.5 * clay_frac

    # Step 2: Mineralogy adjustment
    mult = MINERALOGY_MULT.get(fao_type, None)
    if mult is None:
        print(
            f"WARNING: FAO type '{fao_type}' not found in MINERALOGY_MULT. "
            f"Using 1.0 (no adjustment). Add this type to the dictionary "
            f"with an appropriate multiplier if it represents a known mineralogy."
        )
        mult = 1.0

    cx_adj_gkg = cx_raw_gkg * mult

    # Step 3: Convert to Mg C ha⁻¹
    # Unit derivation:
    #   g C / kg soil  ×  g soil / cm³  ×  cm depth  ×  10 000 m² / ha
    #   = g C / cm²  ×  10 000  = g C × 10 000 / 10 000 cm²
    #   = Mg C / ha  (since 1 Mg = 10⁶ g, 1 ha = 10⁸ cm²... simplifies to × 0.1)
    cx_mgha = cx_adj_gkg * bd * depth_cm * 0.1

    return cx_mgha, cx_adj_gkg, mult


# ---------------------------------------------------------------------------
# RATE MODIFYING FACTOR: Temperature  (unchanged)
# ---------------------------------------------------------------------------
def RMF_Tmp(TEMP):
    """
    Calculate the rate modifying factor for temperature.

    Uses the Ratkowsky equation from the original RothC model.
    At TEMP < –5 °C, decomposition is assumed to stop entirely (factor = 0).
    At higher temperatures, the factor rises non-linearly toward 1 as
    temperature increases.  The shape is controlled by the two constants
    (106.06 and 18.27) which were fitted to empirical decomposition data.

    UNCHANGED from original RothC_src.py.
    """
    if TEMP < -5.0:
        RM_TMP = 0.0
    else:
        RM_TMP = 47.91 / (np.exp(106.06 / (TEMP + 18.27)) + 1.0)

    return RM_TMP


# ---------------------------------------------------------------------------
# RATE MODIFYING FACTOR: Moisture  (unchanged)
# ---------------------------------------------------------------------------
def RMF_Moist(RAIN, PEVAP, clay, depth, PC, SWC):
    """
    Calculate the rate modifying factor for soil moisture.

    The factor ranges from RMFMin (0.2) when the soil is at maximum soil
    moisture deficit (SMDMax, completely dry) to RMFMax (1.0) when soil
    water content is above the –1 bar threshold (SMD1bar).

    SMDMax is the maximum soil moisture deficit (negative, so more negative
    = drier), derived from clay content and depth.  Clay holds more water,
    so more clayey soils have a larger SMDMax (more capacity before drying).

    The soil water content (SWC[0]) is updated each timestep based on the
    rainfall–evapotranspiration balance (DF = RAIN – 0.75 × PET).  The 0.75
    factor accounts for incomplete evaporation of potential evapotranspiration.

    PC (plant cover) affects whether the soil can dry further than the
    bare-soil limit (SMDBare), which is set at 55.6% of SMDMaxAdj.

    UNCHANGED from original RothC_src.py.
    """
    RMFMax = 1.0
    RMFMin = 0.2

    # Soil water properties from clay content and depth
    SMDMax = -(20 + 1.3 * clay - 0.01 * (clay * clay))
    SMDMaxAdj = SMDMax * depth / 23.0       # scaled to actual depth (23 cm is RothC default)
    SMD1bar = 0.444 * SMDMaxAdj             # soil water content at –1 bar tension
    SMDBare = 0.556 * SMDMaxAdj             # limiting deficit for bare soil

    # Moisture balance this timestep
    DF = RAIN - 0.75 * PEVAP

    minSWCDF = np.min(np.array([0.0, SWC[0] + DF]))
    minSMDBareSWC = np.min(np.array([SMDBare, SWC[0]]))

    if PC == 1:
        # Under plant cover: soil can dry all the way to SMDMaxAdj
        SWC[0] = np.max(np.array([SMDMaxAdj, minSWCDF]))
    else:
        # Bare soil: limited to SMDBare (less drying)
        SWC[0] = np.max(np.array([minSMDBareSWC, minSWCDF]))

    if SWC[0] > SMD1bar:
        RM_Moist = 1.0
    else:
        RM_Moist = (RMFMin + (RMFMax - RMFMin) * (SMDMaxAdj - SWC[0]) / (SMDMaxAdj - SMD1bar))

    return RM_Moist


# ---------------------------------------------------------------------------
# RATE MODIFYING FACTOR: Plant cover  (unchanged)
# ---------------------------------------------------------------------------
def RMF_PC(PC):
    """
    Calculate the plant cover rate modifying factor.

    When soil is bare (PC = 0), decomposition is slightly enhanced
    relative to vegetated soil (PC = 1), hence the factor is 1.0 for
    bare and 0.6 under plant cover.  This reflects the insulating and
    shading effect of plant cover on soil temperature and moisture.

    UNCHANGED from original RothC_src.py.
    """
    if PC == 0:
        RM_PC = 1.0
    else:
        RM_PC = 0.6

    return RM_PC


# ---------------------------------------------------------------------------
# DECOMPOSITION FUNCTION  —  CORE MODIFICATION IS HERE
# ---------------------------------------------------------------------------
def decomp(timeFact, DPM, RPM, BIO, HUM, IOM, SOC,
           DPM_Rage, RPM_Rage, BIO_Rage, HUM_Rage, Total_Rage,
           modernC, RateM, clay, C_Inp, FYM_Inp, DPM_RPM,
           Cx_mgha):
    """
    Perform one decomposition timestep for all RothC carbon pools.

    This function is called once per monthly timestep.  It:
      1. Decays each pool exponentially using its rate constant and the
         combined rate modifier (RateM).
      2. Partitions the decayed carbon between CO₂, BIO, and HUM.
         *** THIS STEP IS MODIFIED — see 'SATURATION MODIFICATION' below ***
      3. Adds new plant carbon inputs (C_Inp) to DPM and RPM.
      4. Adds FYM inputs to DPM, RPM, and HUM.
      5. Updates radiocarbon ages of each pool.

    PARAMETERS  (new parameter vs original is marked with ***)
    ----------------------------------------------------------
    timeFact  : int    — timesteps per year (12 for monthly)
    DPM       : list   — Decomposable Plant Material pool [Mg C/ha]
    RPM       : list   — Resistant Plant Material pool    [Mg C/ha]
    BIO       : list   — Microbial Biomass pool            [Mg C/ha]
    HUM       : list   — Humified Organic Matter pool      [Mg C/ha]
    IOM       : list   — Inert Organic Matter pool         [Mg C/ha]
    SOC       : list   — Total Soil Organic Carbon         [Mg C/ha]
    *_Rage    : lists  — Radiocarbon ages of each pool
    modernC   : float  — Modern radiocarbon activity (1.0 for present-day)
    RateM     : float  — Combined rate modifier (Tmp × Moist × PC × trm)
    clay      : float  — Clay content in % (0–100)
    C_Inp     : float  — Monthly plant carbon input [Mg C/ha/month]
    FYM_Inp   : float  — Monthly FYM carbon input   [Mg C/ha/month]
    DPM_RPM   : float  — DPM:RPM ratio (determines how plant C is split)
    Cx_mgha   : float  — *** NEW *** Mineralogy-adjusted HUM pool ceiling
                          [Mg C/ha], calculated by compute_cx().
                          This is the only new parameter relative to the
                          original decomp() function.

    WHAT IS NOT CHANGED
    -------------------
    All rate constants (DPM_k, RPM_k, BIO_k, HUM_k), the radiocarbon
    decay constant (conr), the BIO transfer fraction (0.46), the DPM:RPM
    split logic, the FYM split (49/49/2%), and all radiocarbon age
    calculations are identical to the original code.

    SATURATION MODIFICATION
    -----------------------
    In standard RothC, the partition between CO₂, BIO and HUM is:

        CO₂ fraction  =  x / (x + 1)
        BIO fraction  =  0.46 / (x + 1)
        HUM fraction  =  0.54 / (x + 1)          ← fixed ε = 0.54

    where x = 1.67 × (1.85 + 1.60 × exp(–0.0786 × clay)).  Note that
    x + 0.46 + 0.54 = x + 1, so the three fractions sum to 1.0.

    The modification replaces the fixed ε = 0.54 with an effective value
    that decreases as HUM approaches its mineral protection ceiling Cx:

        sat_factor  =  max(0,  1 – HUM / Cx)
        ε_eff       =  0.54 × sat_factor

    As HUM → Cx, sat_factor → 0 and ε_eff → 0:  no more C flows into HUM.
    C that would have gone to HUM is instead respired as CO₂.

    The updated fractions become:
        HUM fraction  =  ε_eff / (x + 1)
        BIO fraction  =  0.46  / (x + 1)          ← unchanged
        CO₂ fraction  =  (x + 0.54 – ε_eff) / (x + 1)   ← absorbs the difference

    Mass balance check:
        CO₂ + BIO + HUM = (x + 0.54 – ε_eff + 0.46 + ε_eff) / (x+1)
                        = (x + 1) / (x + 1) = 1.0  ✓

    WHY ε-REGULATION RATHER THAN k-REGULATION?
    -------------------------------------------
    An alternative approach modifies the HUM decomposition rate constant (k)
    rather than ε.  White et al. (2014) show that ε-regulation is preferred
    because it also correctly modifies the critical C:N ratio for net nitrogen
    mineralisation (r_cr = r_rec / ε_eff).  As soils approach saturation,
    r_cr increases, meaning decomposing residues are more likely to mineralise
    N rather than immobilise it — an empirically supported outcome.
    k-regulation does not reproduce this behaviour.

    RETURNS
    -------
    sat_ratio : float — HUM[0] / Cx_mgha at the START of this timestep
                        (before new C is added).  Range [0, 1].  Used for
                        diagnostics and output tracking.
    """

    zero = 0e-8

    # RothC rate constants (per year) — these are fixed model parameters
    # calibrated from long-term field experiments worldwide.  Do not change.
    #   DPM: 10.0/yr — rapidly decomposing plant material (e.g. leaves, roots)
    #   RPM:  0.3/yr — slowly decomposing plant material (e.g. lignified tissue)
    #   BIO:  0.66/yr — microbial biomass
    #   HUM:  0.02/yr — stable humic organic matter (50-year mean residence time)
    DPM_k = 10.0
    RPM_k = 0.3
    BIO_k = 0.66
    HUM_k = 0.02

    # Radiocarbon decay constant: half-life = 5568 years (Libby half-life)
    conr = np.log(2.0) / 5568.0

    # Timestep in years (1/12 for monthly)
    tstep = 1.0 / timeFact

    # Radiocarbon decay factor per timestep (used for age tracking)
    exc = np.exp(-conr * tstep)

    # -----------------------------------------------------------------------
    # STEP 1: Exponential decay of each pool over this timestep
    # -----------------------------------------------------------------------
    # Each pool decays as: pool_remaining = pool × exp(–RateM × k × tstep)
    # RateM is the combined rate modifier (temperature × moisture × plant cover × trm).
    # A higher RateM means faster decomposition.
    DPM1 = DPM[0] * np.exp(-RateM * DPM_k * tstep)
    RPM1 = RPM[0] * np.exp(-RateM * RPM_k * tstep)
    BIO1 = BIO[0] * np.exp(-RateM * BIO_k * tstep)
    HUM1 = HUM[0] * np.exp(-RateM * HUM_k * tstep)

    # Amount of carbon that decomposed from each pool this timestep
    DPM_d = DPM[0] - DPM1
    RPM_d = RPM[0] - RPM1
    BIO_d = BIO[0] - BIO1
    HUM_d = HUM[0] - HUM1

    # -----------------------------------------------------------------------
    # STEP 2: Clay-dependent CO₂:BIO+HUM partitioning coefficient
    # -----------------------------------------------------------------------
    # x represents the ratio of CO₂ production to total microbial product
    # formation.  Higher clay → lower x → more of the decomposed C ends up
    # in BIO+HUM rather than being respired as CO₂.  This reflects the
    # physical protection provided by clay surfaces.
    x = 1.67 * (1.85 + 1.60 * np.exp(-0.0786 * clay))

    # -----------------------------------------------------------------------
    # SATURATION MODIFICATION: Compute effective HUM transfer efficiency
    # -----------------------------------------------------------------------
    # Calculate current saturation ratio of the HUM pool.
    # We use HUM[0] (the value at the START of this timestep, before decay)
    # because that represents the existing mineral protection already in use.
    #
    # sat_ratio: what fraction of mineral surface capacity is already occupied.
    #   0.0 → HUM is empty;  soils at these cooperatives are at 0.04–0.13.
    #   1.0 → HUM is at its Cx ceiling; all incoming C would be respired.
    #
    # We clamp to [0, 1] to handle any floating-point overshoot and to ensure
    # the model doesn't apply a negative correction if HUM drifts fractionally
    # above Cx (which can happen in a single timestep of high input).
    sat_ratio = float(np.clip(HUM[0] / Cx_mgha, 0.0, 1.0))

    # Saturation factor: 1 when far from ceiling, 0 when at ceiling
    sat_factor = 1.0 - sat_ratio

    # *** MODIFIED ε ***
    # Standard RothC uses a fixed ε = 0.54.
    # This line is the core change: ε_eff shrinks as HUM fills up.
    eps_eff = 0.54 * sat_factor

    # -----------------------------------------------------------------------
    # STEP 3: Partition decomposed carbon into CO₂, BIO, and HUM
    # -----------------------------------------------------------------------
    # ORIGINAL code (for reference — these lines are REPLACED below):
    #   DPM_co2 = DPM_d * (x / (x + 1))
    #   DPM_BIO = DPM_d * (0.46 / (x + 1))
    #   DPM_HUM = DPM_d * (0.54 / (x + 1))   ← fixed 0.54 replaced by eps_eff
    #
    # MODIFIED code:
    #   CO₂ gets the extra C that can no longer go to HUM (mass balance preserved)
    #   BIO is unchanged — microbial biomass is not mineral-protected

    DPM_co2 = DPM_d * ((x + 0.54 - eps_eff) / (x + 1))   # ← modified CO₂ fraction
    DPM_BIO = DPM_d * (0.46 / (x + 1))                    # ← unchanged
    DPM_HUM = DPM_d * (eps_eff / (x + 1))                 # ← modified HUM fraction

    RPM_co2 = RPM_d * ((x + 0.54 - eps_eff) / (x + 1))
    RPM_BIO = RPM_d * (0.46 / (x + 1))
    RPM_HUM = RPM_d * (eps_eff / (x + 1))

    BIO_co2 = BIO_d * ((x + 0.54 - eps_eff) / (x + 1))
    BIO_BIO = BIO_d * (0.46 / (x + 1))
    BIO_HUM = BIO_d * (eps_eff / (x + 1))

    HUM_co2 = HUM_d * ((x + 0.54 - eps_eff) / (x + 1))
    HUM_BIO = HUM_d * (0.46 / (x + 1))
    HUM_HUM = HUM_d * (eps_eff / (x + 1))

    # -----------------------------------------------------------------------
    # STEP 4: Update carbon pools
    # -----------------------------------------------------------------------
    # Pool after decay + inflow from all decomposing pools
    DPM[0] = DPM1
    RPM[0] = RPM1
    BIO[0] = BIO1 + DPM_BIO + RPM_BIO + BIO_BIO + HUM_BIO
    HUM[0] = HUM1 + DPM_HUM + RPM_HUM + BIO_HUM + HUM_HUM

    # -----------------------------------------------------------------------
    # STEP 5: Add plant carbon inputs (split by DPM:RPM ratio)
    # -----------------------------------------------------------------------
    # DPM_RPM is the DPM-to-RPM ratio.  For most grassland/mixed systems ~1.44;
    # for forests ~0.25.  It is set per cooperative in the run configuration.
    PI_C_DPM = DPM_RPM / (DPM_RPM + 1.0) * C_Inp
    PI_C_RPM = 1.0 / (DPM_RPM + 1.0) * C_Inp

    # -----------------------------------------------------------------------
    # STEP 6: Add FYM (farmyard manure) inputs
    # -----------------------------------------------------------------------
    # FYM is split 49% DPM / 49% RPM / 2% HUM (Coleman & Jenkinson 1996)
    # The HUM fraction of FYM goes directly into HUM regardless of saturation.
    # This is intentional — freshly added stable organic matter (compost fraction)
    # is assumed to physically occupy mineral surfaces immediately.  If you want
    # FYM_HUM to also be subject to the saturation cap, multiply FYM_C_HUM by
    # sat_factor as well.  We leave it unmodified to stay close to the original
    # RothC FYM formulation.
    FYM_C_DPM = 0.49 * FYM_Inp
    FYM_C_RPM = 0.49 * FYM_Inp
    FYM_C_HUM = 0.02 * FYM_Inp

    # Add plant and FYM carbon to pools
    DPM[0] = DPM[0] + PI_C_DPM + FYM_C_DPM
    RPM[0] = RPM[0] + PI_C_RPM + FYM_C_RPM
    HUM[0] = HUM[0] + FYM_C_HUM

    # -----------------------------------------------------------------------
    # STEP 7: Radiocarbon age tracking  (unchanged logic from original)
    # -----------------------------------------------------------------------
    # Each pool's radiocarbon activity (Ract) is tracked to allow Δ¹⁴C
    # calculations.  The age is derived from: Ract = pool × exp(–conr × age)

    DPM_Ract = DPM1 * np.exp(-conr * DPM_Rage[0])
    RPM_Ract = RPM1 * np.exp(-conr * RPM_Rage[0])

    BIO_Ract = BIO1 * np.exp(-conr * BIO_Rage[0])
    DPM_BIO_Ract = DPM_BIO * np.exp(-conr * DPM_Rage[0])
    RPM_BIO_Ract = RPM_BIO * np.exp(-conr * RPM_Rage[0])
    BIO_BIO_Ract = BIO_BIO * np.exp(-conr * BIO_Rage[0])
    HUM_BIO_Ract = HUM_BIO * np.exp(-conr * HUM_Rage[0])

    HUM_Ract = HUM1 * np.exp(-conr * HUM_Rage[0])
    DPM_HUM_Ract = DPM_HUM * np.exp(-conr * DPM_Rage[0])
    RPM_HUM_Ract = RPM_HUM * np.exp(-conr * RPM_Rage[0])
    BIO_HUM_Ract = BIO_HUM * np.exp(-conr * BIO_Rage[0])
    HUM_HUM_Ract = HUM_HUM * np.exp(-conr * HUM_Rage[0])

    IOM_Ract = IOM[0] * np.exp(-conr * IOM_Rage[0])

    PI_DPM_Ract = modernC * PI_C_DPM
    PI_RPM_Ract = modernC * PI_C_RPM

    FYM_DPM_Ract = modernC * FYM_C_DPM
    FYM_RPM_Ract = modernC * FYM_C_RPM
    FYM_HUM_Ract = modernC * FYM_C_HUM

    DPM_Ract_new = FYM_DPM_Ract + PI_DPM_Ract + DPM_Ract * exc
    RPM_Ract_new = FYM_RPM_Ract + PI_RPM_Ract + RPM_Ract * exc

    BIO_Ract_new = (BIO_Ract + DPM_BIO_Ract + RPM_BIO_Ract +
                    BIO_BIO_Ract + HUM_BIO_Ract) * exc

    HUM_Ract_new = FYM_HUM_Ract + (HUM_Ract + DPM_HUM_Ract +
                                    RPM_HUM_Ract + BIO_HUM_Ract + HUM_HUM_Ract) * exc

    # Total SOC = sum of all pools
    SOC[0] = DPM[0] + RPM[0] + BIO[0] + HUM[0] + IOM[0]

    Total_Ract = DPM_Ract_new + RPM_Ract_new + BIO_Ract_new + HUM_Ract_new + IOM_Ract

    # -----------------------------------------------------------------------
    # STEP 8: Update radiocarbon ages of each pool
    # -----------------------------------------------------------------------
    if DPM[0] <= zero:
        DPM_Rage[0] = zero
    else:
        DPM_Rage[0] = (np.log(DPM[0] / DPM_Ract_new)) / conr

    if RPM[0] <= zero:
        RPM_Rage[0] = zero
    else:
        RPM_Rage[0] = (np.log(RPM[0] / RPM_Ract_new)) / conr

    if BIO[0] <= zero:
        BIO_Rage[0] = zero
    else:
        BIO_Rage[0] = (np.log(BIO[0] / BIO_Ract_new)) / conr

    if HUM[0] <= zero:
        HUM_Rage[0] = zero
    else:
        HUM_Rage[0] = (np.log(HUM[0] / HUM_Ract_new)) / conr

    if SOC[0] <= zero:
        Total_Rage[0] = zero
    else:
        Total_Rage[0] = (np.log(SOC[0] / Total_Ract)) / conr

    # Return the saturation ratio for diagnostic tracking in the run loop.
    # This lets you monitor how close HUM is to its ceiling over time.
    return sat_ratio


# ---------------------------------------------------------------------------
# TOP-LEVEL ROTHC FUNCTION  —  one monthly timestep
# ---------------------------------------------------------------------------
def RothC(timeFact, DPM, RPM, BIO, HUM, IOM, SOC,
          DPM_Rage, RPM_Rage, BIO_Rage, HUM_Rage, Total_Rage,
          modernC, clay, depth, TEMP, RAIN, PEVAP, PC, DPM_RPM,
          C_Inp, FYM_Inp, SWC, trm, Cx_mgha):
    """
    Run one monthly RothC timestep.

    Calculates the three rate modifying factors, combines them, then calls
    decomp() to update all carbon pools.

    PARAMETERS  (new parameter vs original is marked with ***)
    ----------------------------------------------------------
    timeFact  : int    — timesteps per year (12 for monthly)
    DPM–IOM   : lists  — carbon pools in Mg C ha⁻¹
    SOC       : list   — total soil organic carbon in Mg C ha⁻¹
    *_Rage    : lists  — radiocarbon ages
    modernC   : float  — modern ¹⁴C activity
    clay      : float  — clay content in % (0–100)
    depth     : float  — soil depth in cm
    TEMP      : float  — mean monthly temperature (°C)
    RAIN      : float  — monthly rainfall (mm)
    PEVAP     : float  — monthly potential evapotranspiration (mm) already
                         divided by 0.75 in the calling code
    PC        : int    — plant cover flag (0 = bare, 1 = covered)
    DPM_RPM   : float  — DPM:RPM ratio for incoming plant C
    C_Inp     : float  — monthly plant C input [Mg C/ha/month]
    FYM_Inp   : float  — monthly FYM C input   [Mg C/ha/month]
    SWC       : list   — soil water content deficit (updated in place)
    trm       : float  — additional rate modifier (e.g. tillage; 1.0 = no effect)
    Cx_mgha   : float  — *** NEW *** HUM pool ceiling [Mg C/ha] from compute_cx()

    RETURNS
    -------
    sat_ratio : float — HUM saturation ratio from decomp() (0–1), for tracking
    """

    # Calculate the three rate modifying factors
    RM_TMP   = RMF_Tmp(TEMP)
    RM_Moist = RMF_Moist(RAIN, PEVAP, clay, depth, PC, SWC)
    RM_PC    = RMF_PC(PC)

    # Combined rate modifier: product of all three factors plus any user-defined
    # modifier (trm).  This single value scales all pool decomposition rates.
    RateM = RM_TMP * RM_Moist * RM_PC * trm

    # Run the decomposition step; returns sat_ratio for diagnostic use
    sat_ratio = decomp(
        timeFact, DPM, RPM, BIO, HUM, IOM, SOC,
        DPM_Rage, RPM_Rage, BIO_Rage, HUM_Rage, Total_Rage,
        modernC, RateM, clay, C_Inp, FYM_Inp, DPM_RPM,
        Cx_mgha
    )

    return sat_ratio
