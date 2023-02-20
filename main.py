from HydrologicModel import StorageNode
from HydrologicModel import FloodEvent
import pandas as pd


def main():
    # repeat the computations on this run?
    do_computation = True

    # set up the inflows to be modelled
    standard_flows = {"inflow_file": 'config/120122A_Feb_2009.csv',
                      "inflow_col_name": 'Flow',
                      "scaling_factors": [1.0, 1.5, 2.0, 3.0],
                      "result_file_prefix": 'Feb_2009'
                      }

    pmf_flows = {"inflow_file": 'config/PMF_flow.csv',
                 "inflow_col_name": 'Flow_PMF',
                 "scaling_factors": [1.0],
                 "result_file_prefix": 'PMF'
                 }

    flows = [standard_flows, pmf_flows]

    all_simulations = FloodEvent()
    all_simulations.set_event_parameters('config/event_parameters.json')
    all_simulations.import_streams()
    simulations = all_simulations.simulations
    streams = all_simulations.streams
    print(simulations)

    # create an empty list to store all results in
    frames = []

    # loop through the scaling factors, simulations and streams
    for flow in flows:
        scaling_factors = flow['scaling_factors']
        for scaling_factor in scaling_factors:
            scaling_factor_text = '{:.2f}'.format(scaling_factor)
            scaling_factor_text = scaling_factor_text.replace(".", "p")
            for simulation in simulations:
                for stream in streams:
                    # set up the filename to use to store results
                    result_file = 'results/{}_{}_{}_SF{}.csv'.format(flow['result_file_prefix'],
                                                                     stream['name'],
                                                                     simulation['name'],
                                                                     scaling_factor_text)

                    # do the actual stream routing
                    if do_computation:
                        inflow = all_simulations.inflow_csv(flow['inflow_file'], flow['inflow_col_name'])
                        compute_outflows(simulation, stream, scaling_factor, result_file, inflow)

                    # collate the individual results into a single file of all results
                    df = pd.read_csv(result_file)
                    df = pd.DataFrame(df['Outflow'])
                    new_col_name = result_file.replace('results/', '')
                    new_col_name = new_col_name.replace('.csv', '')
                    df = df.rename(columns={'Outflow': new_col_name})
                    frames.append(df.copy())

    # write the collated results of all simulations into a single csv file
    results = pd.concat(frames, axis=1)
    results.to_csv('results.csv')


def compute_outflows(simulation, stream_parameters, scaling_factor, result_file, inflow):
    stream = StorageNode(stream_parameters['name'])
    stream.inflows = inflow
    stream.scale_inflow(scaling_factor)
    stream.set_routing_parameters(routing_method=str(simulation['routing_method']),
                                  parameters=simulation['parameters'],
                                  stream_length=stream_parameters['length'])
    stream.compute_outflow()
    stream.write_to_csv(result_file)


if __name__ == '__main__':
    main()

