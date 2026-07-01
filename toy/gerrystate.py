import json
import pandas as pd
from gerrychain import (Partition, Graph, updaters, MarkovChain, constraints, accept)
from gerrychain.proposals import recom
from gerrychain.constraints import contiguous
from gerrychain.updaters import cut_edges
from functools import partial
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as mcm

graph = Graph.from_json('gerrystate.json')

def plot_partition(partition, show=True):
    node_positions = {}
    node_colors = []
    for node_id, node_attrs in partition.graph.nodes.items():
        node_positions[node_id] = (node_attrs['x'], node_attrs['y'])
        partition_id = partition.assignment[node_id]
        node_colors.append(mcm.tab20(int(partition_id)))
    nx.draw(partition.graph, with_labels=True, pos=node_positions, node_color=node_colors)
    if show:
        plt.show()

def multi_plot(partition, partition2, partition3, partition4, show=True):
    partition_colors = {
        1:'green',
        2:'orange',
        3:'yellow',
        4: 'red'
    }
    node_positions = {}
    node_colors = []
    x1 = 0
    x2 = 0
    x3 = 0
    y1 = 0
    y2 = 0
    y3 = 0
    i1 = 0
    i2 = 0
    i3 = 0
    for node_id, node_attrs in partition.graph.nodes.items():
        node_positions[node_id] = (node_attrs['x'], node_attrs['y'])
        partition_id = partition.assignment[node_id]
        #node_colors.append(mcm.tab20(int(partition_id)))
        node_colors.append(partition_colors[partition_id])
    #plt.scatter(0,0, s = 1000)
    nx.draw(partition.graph, with_labels=True, pos=node_positions, node_color=node_colors, edgecolors = 'black')
    
    node_colors2 = []
    for node_id, node_attrs in partition2.graph.nodes.items():
        x1 = node_attrs['x']
        y1 = node_attrs['y']
        partition_id = partition2.assignment[node_id]
        node_colors2.append(mcm.tab20(int(partition_id)))
        plt.scatter(x1,y1,color = node_colors2[i1], s = 1500, marker ='s')
        i1 += 1

    node_colors3 = []
    for node_id, node_attrs in partition3.graph.nodes.items():
        x2 = node_attrs['x']
        y2 = node_attrs['y']
        partition_id = partition3.assignment[node_id]
        node_colors3.append(mcm.tab20(int(partition_id)))
        plt.scatter(x2,y2,color = node_colors3[i2], s = 1200, marker = '^')
        i2 += 1

    node_colors4 = []
    for node_id, node_attrs in partition4.graph.nodes.items():
        x3 = node_attrs['x']
        y3 = node_attrs['y']
        partition_id = partition4.assignment[node_id]
        node_colors4.append(mcm.tab20(int(partition_id)))
        plt.scatter(x3,y3,color = node_colors4[i3], s = 1800, marker = 'P')
        i3 += 1

    if show:
        plt.scatter(-1, -1, s = 300, color = 'orange', label = 'economic', marker = 'P', alpha = 0.0)
        plt.scatter(-1, -1, s = 600, color = 'orange', edgecolors= 'black', label = 'power', alpha = 0.0)
        plt.scatter(-1, -1, s = 1000, color = 'orange', label = 'schools', marker = '^', alpha = 0.0)
        plt.scatter(-1, -1, s = 1000,color = 'orange', label = 'water', marker = 's', alpha = 0.0)
        leg = plt.legend(borderpad = 2, labelspacing = 3)
        for lm in leg.legend_handles:
            lm.set_alpha(1.0)
        plt.show()

def cleaner_multi_plot(partition_list, labels, markers, show=True):
    partition_colors = {
        1:'green',
        2:'orange',
        3:'yellow',
    }
   
    if len(partition_list) > 4:
        print("error: too many partitions")
        return
    
    j = 0
    size = 2000
    legend_size = 1800
    
    for partition in partition_list:
        node_colors = []
        i = 0
        for node_id, node_attrs in partition.graph.nodes.items():
            x = node_attrs['x']
            y = node_attrs['y']
            partition_id = partition.assignment[node_id]
            node_colors.append(partition_colors[partition_id])
            plt.scatter(x,y,color = node_colors[i], edgecolors= 'black', s = size, marker = markers[j])
            i+= 1
        size -= 450
        j += 1

    if show:
        j = 0
        for label in labels:
            plt.scatter(-1, -1, s = legend_size, color = 'orange', edgecolors= 'black', label = labels[j], marker = markers[j], alpha = 0.0)
            j += 1
            legend_size -= 300      
        leg = plt.legend(borderpad = 1.5, labelspacing = 3)
        for lm in leg.legend_handles:
            lm.set_alpha(1.0)
        plt.show()

#power assignments
for i in range(32):
    graph.nodes[i]['power'] = 1

for i in range(32,64):
    graph.nodes[i]['power'] = 2

#water assignments
i = 0
flipper_counter = 0
bool_array = [False, True]
while i < 64:
    flipper = bool_array[0]

    if flipper == False:
        graph.nodes[i]['water'] = 1
        flipper_counter += 1
    else:
        graph.nodes[i]['water'] = 2
        flipper_counter += 1
        flipper += 1

    if flipper_counter == 4:
        flipper_counter = 0
        bool_array.reverse()
    i += 1

#economic class assignments
green = [0, 1, 8, 9, 16]
orange = [27,28,29,35,36,44,45,52]

i = 0
while i < 64:
    if i in green:
        graph.nodes[i]['economic_class'] = 1
    elif i in orange:
        graph.nodes[i]['economic_class'] = 2
    else:
        graph.nodes[i]['economic_class'] = 3
    i += 1        

#school assignments
i = 0
green_t = [35,36,43,44,45,51,52,53,54,55,60,61,62,63]
orange_t = [0,1,2,8,9,10,16,17,18,24,25,26,27,32,33,34,40,41,42,48,49,50,56,57,58,59]
while i < 64:
    if i in green_t:
        graph.nodes[i]['schools'] = 1
    elif i in orange_t:
        graph.nodes[i]['schools'] = 2
    else:
        graph.nodes[i]['schools'] = 3
    i += 1      


#for node, data in graph.nodes(data=True):
   #print(f"Node {node} has attributes: {data}")

power_partition = Partition(graph, assignment="power")
water_partition = Partition(graph, assignment="water")
economic__partition = Partition(graph, assignment="economic_class")
school_partition = Partition(graph, assignment="schools")

partition_list = [power_partition, water_partition, economic__partition, school_partition]
labels = ['power', 'water', 'economic', 'school']
markers = ['s', '^', 'o', 'P']

cleaner_multi_plot(partition_list, labels, markers)

Graph.to_json(graph, "new_gerrystate.json")

