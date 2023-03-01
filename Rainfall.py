"""
Used to handle the reading and processing of rainfall information

Hyetograph - an object used to build the excess runoff from the rainfall input. This object is a parameter
             in the storage node objects.
"""

import pandas as pd
from scipy.interpolate import CubicSpline
import numpy as np


class Hyetograph:
    def __init__(self, name='blank', total_depth=0.0):
        self.name = name
        self.total_depth = total_depth
        self.temporal_pattern = pd.DataFrame()
        self.depths = pd.DataFrame()  # mm
        self.excess_depths = pd.DataFrame()  # mm
        self.runoff = pd.DataFrame()  # m3/s

    def set_temporal_pattern(self, filename, header):
        temporal_pattern = pd.read_csv(filename, index_col=0)
        self.depths = temporal_pattern[header] * self.total_depth
        self.depths = self.depths.rename(self.name)

    def apply_il_cl_loss_model(self, initial_loss, continuing_loss):
        # drop parts of the hyetograph where there is no rain -- needed for interpolation
        cumulative_depths = self.depths.cumsum()
        cumulative_depths_increasing = cumulative_depths.drop_duplicates()

        # find the time where the initial losses are exhausted
        x = cumulative_depths_increasing.tolist()  # need to check if strictly increasing
        y = pd.DataFrame(cumulative_depths_increasing).index.tolist()
        cs = CubicSpline(x, y)
        excess_start = np.around(cs(initial_loss), 4)
        # print('Excess rain starts at {} hours'.format(excess_start))

        # apply the initial loss
        excess_depths = pd.DataFrame(self.depths)
        excess_depths.loc[excess_start] = 0.0
        excess_depths = excess_depths.sort_index()
        excess_depths.loc[excess_depths.index < excess_start] = 0.0

        # apply the continuing loss
        excess_depths['delta_time'] = excess_depths.index.to_series().diff()
        excess_depths['CL'] = continuing_loss * excess_depths['delta_time']
        excess_depths = excess_depths[self.name] - excess_depths['CL']
        excess_depths = excess_depths.fillna(0)
        excess_depths[excess_depths < 0.0] = 0.0
        self.excess_depths = excess_depths
        # print(excess_depths)

    def compute_runoff(self, catchment_area):
        runoff = pd.DataFrame(self.excess_depths)
        runoff = runoff.rename(columns={runoff.columns[0]: 'excess_rainfall'})
        runoff['runoff'] = runoff['excess_rainfall'] * catchment_area * 1000000 / 1000 / 3600
        # print(runoff)
        self.runoff = runoff['runoff']



