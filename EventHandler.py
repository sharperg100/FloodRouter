"""
Used to manage the events

EventDatabase - used to read the event data that is used to put together the rainfall for each event
"""

import pandas as pd
from Rainfall import Hyetograph


class EventDatabase:
    def __init__(self, name='', routing_method='urbs'):
        self.name = name
        self.depth_database = pd.DataFrame()
        self.pattern_database = pd.DataFrame()
        self.depths = pd.DataFrame()
        self.patterns = pd.DataFrame()
        self.routing_method = routing_method
        self.rainfall = {}
        self.loss_model = 'il_cl'

    def import_depth_database(self, filename, header='ID'):
        print('\nImporting rainfall depth database: {}'.format(filename))
        self.depth_database = pd.read_csv(filename)
        self.depth_database = self.depth_database.set_index(header)
        # print(self.depth_database)

    def set_depths(self, simulation):
        print('\nSetting rainfall depth: {}'.format(simulation))
        self.depths = pd.DataFrame(self.depth_database.loc[:, simulation])
        print(self.depths)

    def import_pattern_database(self, filename, header='ID'):
        print('\nImporting rainfall pattern database: {}'.format(filename))
        self.pattern_database = pd.read_csv(filename)
        self.pattern_database = self.pattern_database.set_index(header)
        # print(self.pattern_database)
        for subarea, depth in self.depths.iterrows():
            new_rainfall = Hyetograph(name=subarea, total_depth=depth[0])
            temporal_pattern_data = self.pattern_database.loc[subarea]
            new_rainfall.set_temporal_pattern(filename=temporal_pattern_data['filename'],
                                              header=temporal_pattern_data['header'])
            self.rainfall[subarea] = new_rainfall
