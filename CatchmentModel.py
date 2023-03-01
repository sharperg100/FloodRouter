"""
Used to construct and simulate the overall model

ModelSchema - reads the GIS files to create the model structure.
ModelSimulation - handles the simulation (to be built, should move the add rainfall here).
"""

import geopandas as gpd
import pandas as pd
from ModelElements import StorageNode, AreaNode, Stream
import numpy as np
from Rainfall import Hyetograph


class ModelSchema:
    def __init__(self, name='', routing_method='urbs'):
        print('\n-------\nSetting up the model structure for catchment: {}\n-------'.format(name))
        print('\nThe routing method applied to this model is: {}'.format(routing_method))
        self.name = name
        self.nodes = {'junction': [], 'subarea': []}
        self.streams = []
        self.average_stream_length = 0.0
        self.routing_method = routing_method
        self.losses = {}

    def import_streams(self, gis_file, header='ID'):
        print('\nReading junction delineation file: {}'.format(gis_file))
        geo_df = gpd.read_file(gis_file)
        geo_df = geo_df.set_index(header)
        geo_df = geo_df.sort_index()
        # print(geo_df)
        self.add_streams(geo_df)

    def import_junction_gis(self, gis_file, header='ID'):
        print('\nReading junction delineation file: {}'.format(gis_file))
        geo_df = gpd.read_file(gis_file)
        geo_df = geo_df.set_index(header)
        geo_df = geo_df.sort_index()
        # print(geo_df)
        self.add_nodes(geo_df)

    def import_subarea_gis(self, subareas, subnodes, join_header='ID'):
        print('\nReading subarea delineation file: {}'.format(subareas))
        geo_df = gpd.read_file(subareas)
        geo_df = geo_df.set_index(join_header)
        geo_df = geo_df.sort_index()
        # print(geo_df)

        print('\nReading subarea nodes gis file: {}'.format(subnodes))
        node_df = gpd.read_file(subnodes)
        node_df = node_df.set_index(join_header)
        node_df = node_df.sort_index()
        node_df['Area'] = np.around(geo_df.area / 1000000, 3)
        # print(node_df)
        self.add_nodes(node_df)

    def add_streams(self, geo_df):
        total_length = 0.0
        num_streams = 0
        for stream_id, stream_data in geo_df.iterrows():
            num_streams += 1
            new_stream = Stream(name=stream_id)
            length = np.around(stream_data['geometry'].length / 1000, 3)
            new_stream.stream_length = length
            new_stream.position = stream_data['geometry']
            total_length += length
            new_stream.coefficient = stream_data['coeff']
            new_stream.exponent = stream_data['exponent']
            print('Found stream: {} | Length: {} km'.format(stream_id, length))
            self.streams.append(new_stream)
        self.average_stream_length = np.around(total_length / num_streams, 3)
        print('The average stream length is {} km'.format(self.average_stream_length))

    def add_nodes(self, geo_df):
        for node_id, node in geo_df.iterrows():
            if node['Type'] == 'subarea':
                new_node = AreaNode(name=node_id)
                new_node.area_km2 = node['Area']
                new_node.position = node['geometry']
                new_node.coefficient = node['coeff']
                new_node.exponent = node['exponent']
                new_node.initial_loss = node['IL']
                new_node.continuing_loss = node['CL']
                print('Found subarea: {} | Area: {} km²'.format(node_id, node['Area']))
                self.nodes['subarea'].append(new_node)

            elif node['Type'] == 'junction':
                new_node = StorageNode(name=[node_id])
                print('Found junction: {}'.format(node_id))
                self.nodes['junction'].append(new_node)

    def add_rainfall(self, rainfall_dict):
        print('Applying rainfall to subareas...')
        for subarea in self.nodes['subarea']:
            subarea.rainfall = rainfall_dict[subarea.name]
            subarea.compute_runoff()


class ModelSimulation:
    pass