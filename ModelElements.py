"""
Contains the storage nodes (subareas and streams) used to build a model
"""

import pandas as pd
import numpy as np
from scipy import optimize
from scipy import interpolate
import json
from shapely.geometry import Point, LineString, Polygon
from Rainfall import Hyetograph


class FloodEvent:
    def __init__(self, name=''):
        self.name = name
        self.event_parameters = {}
        self.simulations = {}
        self.streams = {}
        self.timestep = 0

    def set_event_parameters(self, json_file):
        print('Importing the event parameters:', end='\n\t')
        print(json_file)
        f = open(json_file)
        self.event_parameters = json.load(f)
        f.close()
        self.simulations = self.event_parameters['simulations']

    def inflow_csv(self, inflow_file, flow_col_name=''):
        # import the inflows
        print('Importing inflow file using column {}:'.format(flow_col_name), end='\n\t')
        print(inflow_file)
        inflows = pd.read_csv(inflow_file, index_col=0)

        # set up the inflows based on the event paramaters
        start = self.event_parameters['start_time']
        stop = self.event_parameters['end_time']
        self.timestep = self.event_parameters['timestep']  # hours
        step = self.timestep / 3600  # convert from seconds to hours
        period = stop - start
        number = int(period / step)
        stop = start + number * step
        times = np.linspace(start, stop, number)
        inflow_df = pd.DataFrame({'Time': times})
        inflow_df = inflow_df.set_index('Time')

        # interpolate the inflows
        x = inflows.index.to_numpy()
        y = inflows[flow_col_name].to_numpy()
        f = interpolate.interp1d(x, y)
        xnew = times
        ynew = f(xnew)
        inflow_df['Inflow'] = ynew
        return inflow_df

    def import_streams(self, json_file=''):
        if json_file == '':
            json_file = self.event_parameters['stream_file']
        print('Importing the event file:', end='\n\t')
        print(json_file)
        f = open(json_file)
        all_data = json.load(f)
        f.close()
        self.streams = all_data['streams']


class StorageNode:
    def __init__(self, name=''):
        self.name = name
        self.inflows = pd.DataFrame()
        self.exponent = 0.0
        self.stream_length = 0.0  # km
        self.computation_df = pd.DataFrame
        self.musk_K = 0.0  # coefficient from the Muskingum method
        self.musk_X = 0.0  # coefficient from the Muskingum method
        self.position = Point()
        self.coefficient = 0.0
        self.type = 'junction'

    def scale_inflow(self, scaling_factor):
        self.inflows = self.inflows * scaling_factor

    def set_routing_parameters(self, routing_method, parameters, stream_length=0.0):
        if routing_method == 'urbs':
            self.musk_K = 3600 * parameters['alpha'] * stream_length
            self.exponent = parameters['exponent']
            self.stream_length = stream_length
            if 'X' in parameters.keys():
                self.musk_X = parameters['X']
        if routing_method == 'rorb':
            self.musk_K = 3600 * parameters['k_c'] / parameters['d_ave'] * stream_length
            self.exponent = parameters['exponent']
            self.stream_length = stream_length

    def compute_outflow(self):
        # Get initial values
        initial_time = self.inflows.index[0]
        initial_inflow = self.inflows.iloc[0].values[0]
        initial_storage = 0.0
        initial_outflow = 0.0

        # print header
        print('Time | Inflow')
        print('{:.2f} hours | {} m³/s'.format(np.around(initial_time, decimals=2),
                                              np.around(initial_inflow, decimals=0)))

        # create container for the computation
        computation = {'Time': [initial_time],
                       'Inflow': [initial_inflow],
                       'Outflow': [initial_outflow],
                       'Storage_1': [initial_storage],
                       'Storage_2': [initial_storage]}

        # loop through the times from the second timestep
        counter = 0
        for time, inflow in self.inflows.iloc[1:].iterrows():
            counter += 1
            inflow = inflow.values[0]
            computation['Time'].append(time)
            computation['Inflow'].append(inflow)
            delta_time = (time - initial_time) * 3600  # in seconds
            average_inflow = 0.5 * (initial_inflow + inflow)
            outflow = self.route_flow(delta_time, average_inflow, initial_outflow, initial_storage)
            computation['Outflow'].append(outflow)
            computation['Storage_1'].append(self.storage_from_flows(outflow, initial_outflow, average_inflow,
                                                                    delta_time, initial_storage))
            computation['Storage_2'].append(self.storage_from_routing(outflow, average_inflow))
            print('{:.2f} hours | {} m³/s | {} m³/s'.format(np.around(time, decimals=2),
                                                            np.around(inflow, decimals=0),
                                                            np.around(outflow, decimals=0)))
            initial_time = time
            initial_inflow = inflow
            initial_storage = self.storage_from_routing(outflow, average_inflow)
            initial_outflow = outflow

        # Store the results
        self.computation_df = pd.DataFrame(computation).set_index('Time')

    def route_flow(self, delta_time, average_inflow, initial_outflow, initial_storage):
        delta_storage = delta_time * (average_inflow - initial_outflow)
        storage = delta_storage + initial_storage
        outflow = (storage/self.musk_K)**(1/self.exponent)
        # outflow = 2 * (average_inflow - delta_storage / delta_time) - initial_outflow
        # print('Change in storage estimate: {}'.format(delta_storage))
        if delta_storage ** 2 > 0.001:
            try:
                root = optimize.root_scalar(self.storage_optimisation, x0=outflow/2, x1=2*outflow,
                                            args=(initial_outflow, average_inflow, delta_time, initial_storage))
                print('Solution: {} | Iterations: {} | Calls: {}'
                      .format(root.root, root.iterations, root.function_calls))
                outflow = root.root
            except ValueError:
                print('Convergence issues!')
                outflow = outflow
        return outflow

    def storage_from_flows(self, outflow, initial_outflow, average_inflow, delta_time, initial_storage):
        delta_storage = delta_time * (average_inflow - 0.5 * (outflow + initial_outflow))
        return initial_storage + delta_storage

    def storage_from_routing(self, outflow, inflow):
        return self.musk_K * ((self.musk_X * inflow) + ((1-self.musk_X) * outflow))**self.exponent

    def storage_optimisation(self, outflow, initial_outflow, average_inflow, delta_time, initial_storage):
        storage_1 = self.storage_from_flows(outflow, initial_outflow, average_inflow, delta_time, initial_storage)
        storage_2 = self.storage_from_routing(outflow, average_inflow)
        return (storage_2 - storage_1) / storage_2 * 100

    def write_to_csv(self, filepath):
        print('\nWriting results to file:', end='\n\t')
        print(filepath)
        self.computation_df.to_csv(filepath)


class AreaNode(StorageNode):
    def __init__(self, name=''):
        super(AreaNode, self).__init__(name)
        self.area_km2 = 0.0
        self.type = 'subarea'
        self.rainfall = Hyetograph(name=name)
        self.initial_loss = 0.0  # mm
        self.continuing_loss = 0.0  # mm/hr

    def compute_runoff(self):
        self.rainfall.apply_il_cl_loss_model(self.initial_loss, self.continuing_loss)
        self.rainfall.compute_runoff(self.area_km2)
        # should do the local catchment routing here if urbs/wbnm


class Stream(StorageNode):
    def __init__(self, name=''):
        super(Stream, self).__init__(name)
        self.type = 'stream'
        self.position = LineString()
