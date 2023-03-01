"""
The main script...
used to build and run the model.
"""

from CatchmentModel import ModelSchema
from EventHandler import EventDatabase

# -------------------------------------------------------------------
# Set up the model structure
model = ModelSchema(name='Burdekin', routing_method='rorb')

model.import_subarea_gis(subnodes='gis/Burdekin_v2_SubNodes.shp',
                         subareas='gis/Burdekin_v2_upperlower_Subarea_Centroid.shp',
                         join_header='SubA_Num')

# Junctions might be obsolete - check class objects for obsolete code
# model.import_junction_gis(gis_file='gis/Burdekin_v2_junctions.shp',
#                           header='Node_Num')

model.import_streams(gis_file='gis/Burdekin_v2_upperlower_Reach.shp',
                     header='Reach_Num')

# lastly, connect and order the components

# -------------------------------------------------------------------
# Set up the rainfall
event = EventDatabase('dummy', routing_method='rorb')
event.import_depth_database(filename='bc_dbase/depth_dbase_01.csv',
                            header='SubA_Num')
event.set_depths('dummy')
event.import_pattern_database(filename='bc_dbase/pattern_dbase_01.csv',
                              header='SubA_Num')

# -------------------------------------------------------------------
# Perform the simulation
model.add_rainfall(event.rainfall)
# do the local catchment routing
# do the total catchment routing

# -------------------------------------------------------------------
# Store results

