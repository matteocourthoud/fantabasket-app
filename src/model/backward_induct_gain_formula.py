"""
Backward induct player value
Author: Matteo Courthoud
Date: 22/10/2022
"""

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

# Read data
df = pd.read_csv('data/gain_formula_data.csv')

# Regress
print(smf.ols('gain ~ points + value - 1', data=df).fit().summary())

# Predict
df['gain_hat'] = np.round(smf.ols('gain ~ points + value - 1', data=df).fit().predict(), 1)
