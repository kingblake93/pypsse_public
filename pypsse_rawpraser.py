"""
Created by Blake King & Jesse Boyd. Feel free to submit PRs or collaborate through github.
"""


import re
import networkx as nx
from networkx.readwrite import json_graph
from matplotlib import pylab as pl

import json
import pandas as pd


def capture_rows(rows, element_type):
    if element_type == 'TRANSFORMER':
        xfmr_header = []
    if element_type == 'BUS':
        key = ('I',)
    elif element_type == 'BRANCH':
        key = ('I', 'J', "'CKT'",)
    elif element_type == 'TRANSFORMER':
        key = ('I', 'J', 'K', "'CKT'",)
    elif element_type == 'SYSTEM SWITCHING DEVICE':
        key = ('I', 'J', "'CKT'",)
    elif element_type == 'LOAD':
        key = ('I', "'ID'")
    elif element_type == 'GENERATOR':
        key = ('I', "'ID'")
    elif element_type == 'SWITCHED SHUNT':
        key = ('I', "'ID'")
    elif element_type == 'FIXED SHUNT':
        key = ('I', "'ID'")
    else:
        key = ('I',)

    start_string = f'BEGIN {element_type} DATA'
    end_string = f'END OF {element_type} DATA'
    items = {}
    flag = False
    for line in rows:
        try:
            if start_string in line:
                flag = True
            elif end_string in line:
                flag = False
                break
            else:
                if element_type != 'TRANSFORMER':
                    if flag is True and '@!' in line:
                        header = line.replace('@!', '').replace('\n', '').replace(' ', '').split(',')
                    if flag is True and '@!' not in line:
                        row = line.replace(' ', '').replace('\n', '').split(',')
                        row_id = [row[header.index(k)] for k in key]
                        row_id = '.'.join(row_id) if len(row_id) > 1 else row_id[0]
                        temp_dict = dict(zip(header, row))
                        items[row_id] = temp_dict
                else:
                    if flag is True and '@!' in line:
                        xfmr_header.append(line.replace('@!', '').replace('\n', '').replace(' ', '').split(','))
                    if flag is True and '@!' not in line:
                        if len(xfmr_header) < 10:
                            xfmr_header = [item for sublist in xfmr_header for item in sublist]
                            row = []
                        if "'" in line:
                            if len(row) > 1:
                                row = ','.join(row)
                                row = row.replace(' ', '').replace('\n', '').split(',')
                                row_id = [row[xfmr_header.index(k)] for k in key]
                                row_id = '.'.join(row_id) if len(row_id) > 1 else row_id[0]
                                temp_dict = dict(zip(xfmr_header, row))
                                items[row_id] = temp_dict
                                row = []
                            row.append(line)
                        else:
                            row.append(line)

                pass
        except:
            pass
    return items


def capture_headers(rows):
    elements = []
    for line in rows:
        if 'END OF' in line:
            try:
                element = re.search(r'END OF (.*?) DATA, BEGIN', line).group(1)
            except:
                element = 'SUBSTATION'
            elements.append(element)
    elements.remove('SYSTEM-WIDE')

    return elements


def build_graph(raw_elem_dict, substation_buses_map=None, bus_station_map=None, outfile_name=''):
    if substation_buses_map is None:
        substation_buses_map = {}
    if bus_station_map is None:
        bus_station_map = {}

    G = nx.MultiGraph()

    for branch_element in ('BRANCH', 'SYSTEM SWITCHING DEVICE'):
        for key, value in raw_elem_dict[branch_element].items():
            G.add_edge(u_for_edge=int(value['I']), v_for_edge=int(value['J']), key=key.replace("'", ""), vals=value,
                       type=branch_element)
            for bus in (int(value['I']), int(value['J'])):
                if f'COUNT_{branch_element}' not in G.nodes[bus].keys():
                    G.nodes[bus].update({f'COUNT_{branch_element}': 1})
                else:
                    G.nodes[bus][f'COUNT_{branch_element}'] = G.nodes[bus][f'COUNT_{branch_element}'] + 1

                if f'{branch_element}' not in G.nodes[bus].keys():
                    G.nodes[bus].update({f'{branch_element}': {key: value}})
                else:
                    G.nodes[bus][f'{branch_element}'].update({key: value})

    for transformer in [xfmr for xfmr in raw_elem_dict['TRANSFORMER'].values() if xfmr['K'] == '0']:
        ckt = transformer["'CKT'"].replace("'", "")
        key = f'{int(transformer["I"])}.{int(transformer["J"])}.{int(transformer["K"])}.{ckt}'
        G.add_edge(u_for_edge=int(transformer['I']), v_for_edge=int(transformer['J']), key=key, vals=value,
                   type='2WXFMR')
        for bus in (int(transformer['I']), int(transformer['J'])):
            if 'COUNT_2WXFMR' not in G.nodes[bus].keys():
                G.nodes[bus].update({'COUNT_2WXFMR': 1})
            else:
                G.nodes[bus]['COUNT_2WXFMR'] = G.nodes[bus]['COUNT_2WXFMR'] + 1

            if '2WXFMRS' not in G.nodes[bus].keys():
                G.nodes[bus].update({'2WXFMRS': {key: value}})
            else:
                G.nodes[bus]['2WXFMRS'].update({key: value})

    for transformer in [xfmr for xfmr in raw_elem_dict['TRANSFORMER'].values() if xfmr['K'] != '0']:
        i_bus, j_bus, k_bus = int(transformer['I']), int(transformer['J']), int(transformer['K'])
        ckt = transformer["'CKT'"].replace("'", "")
        key = f'{int(transformer["I"])}.{int(transformer["J"])}.{int(transformer["K"])}.{ckt}'
        star_bus = f'star_{i_bus}-{j_bus}-{k_bus}'
        for bus in i_bus, j_bus, k_bus:
            G.add_edge(u_for_edge=int(bus), v_for_edge=star_bus, key=key, vals=value, type='3WXFMR')
            if 'COUNT_3WXFMR' not in G.nodes[bus].keys():
                G.nodes[bus].update({'COUNT_3WXFMR': 1})
            else:
                G.nodes[bus]['COUNT_3WXFMR'] = G.nodes[bus]['COUNT_3WXFMR'] + 1

            if '3WXFMRS' not in G.nodes[bus].keys():
                G.nodes[bus].update({'3WXFMRS': {key: value}})
            else:
                G.nodes[bus]['3WXFMRS'].update({key: value})

    for bus_modifier in ('LOAD', 'GENERATOR', 'SWITCHED SHUNT', 'FIXED SHUNT'):
        for __, value in raw_elem_dict[bus_modifier].items():
            _id = value["'ID'"].replace("'", "")
            modifier_type = bus_modifier[0] if len(bus_modifier.split(' ')) == 1 else f'{bus_modifier.split(" ")[0][0]}{bus_modifier.split(" ")[1][0]}'
            G.add_edge(u_for_edge=int(value['I']), v_for_edge=f"{int(value['I'])}.{modifier_type}{_id}", key=key.replace("'", ""), vals=value,
                       type=branch_element)
            try:
                if f'{bus_modifier}S' not in G.nodes[int(value['I'])].keys():
                    G.nodes[int(value['I'])].update({f'{bus_modifier}S': {_id: value}})
                else:
                    G.nodes[int(value['I'])][f'{bus_modifier}S'].update({_id: value})
            except:
                pass

    for psse_bus in list(G.nodes):
        if type(psse_bus) == int:
            G.nodes[psse_bus].update({'PSSE DATA': raw_elem_dict['BUS'][f'{psse_bus}']})

    if outfile_name != '':
        with open(outfile_name, 'w') as out_file:
            json_out = {}
            for node in G.nodes:
                json_out[node] = G.degree[node]

            json.dump(json_out, out_file, indent=4)

    nodes = [node for node in G.nodes if type(node) == int]
    nodes.sort()
    buses = list([int(bus) for bus in raw_elem_dict['BUS'].keys()])
    buses.sort()
    delta = [bus for bus in buses if bus not in nodes]
    errors = []
    if len(substation_buses_map) > 0 and len(bus_station_map) > 0:

        for node in nodes:
            try:
                SUBSTATION_DATA = {'STATION NAME': bus_station_map[node],
                                   'BUS COUNT': len(substation_buses_map[bus_station_map[node]]) if bus_station_map[
                                                                                                        node] != '' else '',
                                   'BUS DATA': substation_buses_map[bus_station_map[node]] if bus_station_map[
                                                                                                  node] != '' else ''}
                G.nodes[node].update({'SUBSTATION DATA': SUBSTATION_DATA})
            except Exception as r:
                errors.append(f'Exception occurred during DD to node mapping: {r}')

    return {'Graph': G, 'Missing Buses': delta, 'Map File': outfile_name, 'Errors': errors}


def parse_raw(v35_raw_file,
              create_json=False,
              outfile_name=''):
    with open(v35_raw_file, 'r') as file:
        lines = file.readlines()

        elements = capture_headers(rows=lines)

        all_items = {}
        for element in elements:
            all_items[element] = capture_rows(rows=lines, element_type=element)

    if create_json is True:
        outfile_name = v35_raw_file.replace('.raw', '.json') if outfile_name == '' else outfile_name
        with open(outfile_name, 'w') as out_file:
            json.dump(all_items, out_file, indent=4)

    return all_items


def get_bus_data(graph, bus):
    return graph.nodes[bus]


def import_ercot_dd(path):
    xls = pd.ExcelFile(path)
    dd = pd.read_excel(xls, 'Data Dictionary')

    bus_station_map = {}
    temp_dict = {}
    for index, row in dd.iterrows():
        bus_station_map[row['SSWG BUS NUMBER']] = row['NMMS STATION NAME'] if type(
            row['NMMS STATION NAME']) == str else ''
        if type(row['NMMS STATION NAME']) == str:
            if row['NMMS STATION NAME'] not in temp_dict.keys():
                temp_dict[row['NMMS STATION NAME']] = {}
            temp_dict[row['NMMS STATION NAME']][row['PLANNING BUS LONGNAME']] = row.to_dict()

    return dd, bus_station_map, temp_dict


def send_graph_json(graph, json_name='graph.json'):
    json_out_graph = json_graph.node_link_data(graph)
    with open(json_name, 'w') as out_graph:
        json.dump(json_out_graph, out_graph, indent=4)


def get_ercot_bus_data(data_dictionary_path, raw_file_path, bus_num=None):
    df, bus_map, dd_dict = import_ercot_dd(data_dictionary_path)
    raw_data = parse_raw(v35_raw_file=raw_file_path, create_json=True)
    d = build_graph(raw_elem_dict=raw_data, substation_buses_map=dd_dict, bus_station_map=bus_map)
    G = d['Graph']

    payload = {'raw_data': raw_data, 'graph': d}

    if bus_num is not None:
        bus_data = get_bus_data(G, bus_num)
        payload['bus_data'] = bus_data

    return payload


def bus_cut_size(graph, bus_id):
    return nx.cut_size(graph, {bus_id, })


def node_minimum_cut(graph, source_node, sink_node):
    return nx.algorithms.connectivity.cuts.minimum_node_cut(graph, source_node, sink_node)


def edge_minimum_cut(graph, source_node, sink_node):
    # TODO: Return exhaustive cut-set rather than only a single option of edge cut.
    return nx.algorithms.connectivity.cuts.minimum_edge_cut(graph, source_node, sink_node)


def get_subgraph(graph, source_node, radius=3):
    return nx.generators.ego.ego_graph(graph, n=source_node, radius=radius)


def draw_subgraph(source_node, graph, label_dict=None):
    pos = nx.spring_layout(graph)
    if label_dict is None:
        label_dict = {}
        for node in subgraph.nodes():
            if type(node) != str:
                label_dict[node] = f"{node}"
            else:
                if 'star' in node:
                    label_dict[node] = 'star'
                else:
                    label_dict[node] = node.split('.')[-1]

    node_size = []
    for node in subgraph.nodes():
        if 'PSSE DATA' in subgraph.nodes[node].keys():
            node_size.append(int(float(subgraph.nodes[node]['PSSE DATA']['BASKV']))*5)
        else:
            node_size.append(10)

    color_map = []

    for node in subgraph.nodes():
        if node == source_node:
            color_map.append('yellow')
        elif 'LOADS' in subgraph.nodes[node]:
            color_map.append('green')
        elif 'GENERATORS' in subgraph.nodes[node]:
            color_map.append('red')
        else:
            color_map.append('blue')

    pl.figure()
    nx.draw(subgraph, pos=pos, node_color=color_map, node_size=node_size, labels=label_dict, with_labels=True)
    pl.show()


if __name__ == '__main__':

    ercot_data_dict_full_path = r'C:\Users\bking\...\Planning_Data_Dictionary_11162021_FINAL.xlsx'
    raw_file_full_path = r'C:\Users\bking\...\21SSWG_2028_SUM1_U1_FINAL_10222021.raw'

    data = get_ercot_bus_data(
        data_dictionary_path=ercot_data_dict_full_path,
        raw_file_path=raw_file_full_path)

    subgraph = get_subgraph(data['graph']['Graph'], source_node=1, radius=3)

    subgraph_minimum_cut = edge_minimum_cut(subgraph, source_node=1, sink_node=4)
    graph_minimum_cut = edge_minimum_cut(graph=data['graph']['Graph'], source_node=1, sink_node=4)

    draw_subgraph(source_node=1, graph=subgraph)


