import pandas as pd
import numpy as np

def Bolinder_CI(C_P, S_P, C_S, S_S, C_R, S_R, C_E, S_E):
    C_I = C_P * S_P + C_S * S_S + C_R * S_R + C_E * S_E
    return C_I

carbon_content = 0.5
root_exudate_ratio = 0.05


# Maize
crop_type = "Maize"
crop_yield = 7.413 		# yields usually already reported as dry matter
moist_content = 0.13
harvest_index = 0.48	# ratio of dry-yield : total dry aboveground biomass
rs_ratio = 0.1

C_P = crop_yield * carbon_content
print(f"C_P: {C_P:.2f}")
S_P = 0

C_S = (C_P * 1/harvest_index - C_P)
print(f"C_S: {C_S:.2f}")
S_S = 1

C_R = (C_S + C_P)* rs_ratio
print(f"C_R: {C_R:.2f}")
S_R = 1

C_E = (C_P + C_S + C_R) * (root_exudate_ratio)
print(f"C_E: {C_E:.2f}")
S_E = 1

carbon_input = Bolinder_CI(C_P, S_P, C_S, S_S, C_R, S_R, C_E, S_E)

print(f"C-inp for {crop_type}: {carbon_input:.3f} t/ha")

