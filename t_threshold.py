import pandas as pd
from gerrychain import (Partition, Graph, updaters, MarkovChain, constraints, accept)
from gerrychain.proposals import recom
from gerrychain.constraints import contiguous
from gerrychain.updaters import cut_edges
from functools import partial
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.cm as mcm

'''
So this "metric" was motivated by some of the readings that clustered COI's and then the preservations
of these clusters in a given plan was determined by a "T threshold number"

I used the gerrymandria data which isn't clustered but future work could involve clustering the different
COI's based on how overlapped they are or some other metric
'''

#plotting functions
def plot_partition(partition, show=True, title = None):
    node_positions = {}
    node_colors = []
    for node_id, node_attrs in partition.graph.nodes.items():
        node_positions[node_id] = (node_attrs['x'], node_attrs['y'])
        partition_id = partition.assignment[node_id]
        node_colors.append(mcm.tab20(int(partition_id)))
    nx.draw(partition.graph, with_labels=True, pos=node_positions, node_color=node_colors)
    if show:
        plt.title(title)
        plt.show()

def multi_plot(partition, partition2, partition3, show=True):
    partition_colors = {
        '1':'blue',
        '2':'green',
        '3':'purple',
        '4':'hotpink'
    }
    node_positions = {}
    node_colors = []
    x1 = 0
    x2 = 0
    y1 = 0
    y2 = 0
    i1 = 0
    i2 = 0
    for node_id, node_attrs in partition.graph.nodes.items():
        node_positions[node_id] = (node_attrs['x'], node_attrs['y'])
        partition_id = partition.assignment[node_id]
        #node_colors.append(mcm.tab20(int(partition_id)))
        node_colors.append(partition_colors[partition_id])
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
    if show:
        plt.scatter(-1, -1, s = 600, color = 'orange', edgecolors= 'black', label = 'county', alpha = 0.0)
        plt.scatter(-1, -1, s = 1000, color = 'orange', label = 'muni', marker = '^', alpha = 0.0)
        plt.scatter(-1, -1, s = 1500,color = 'orange', label = 'water', marker = 's', alpha = 0.0)
        leg = plt.legend(borderpad = 2, labelspacing = 3)
        for lm in leg.legend_handles:
            lm.set_alpha(1.0)
        plt.title("Graph of different COI's")
        plt.show()

#data extraction functions (from Jevon's code)
def extract_data(partition):
    data_rows = []
    
    for node_id in partition.graph.nodes:
        node = partition.graph.nodes[node_id]
        assigned_dist = partition.assignment[node_id] 
        pop = node.get('TOTPOP', 1)
        
        if 'muni' in node:
            data_rows.append({'category': 'muni', 'community_id': f"muni_{node['muni']}", 'district': assigned_dist, 'pop': pop})
        if 'county' in node:
            data_rows.append({'category': 'county', 'community_id': f"county_{node['county']}", 'district': assigned_dist, 'pop': pop})
        if 'water_dist' in node:
            data_rows.append({'category': 'water', 'community_id': f"water_{node['water_dist']}", 'district': assigned_dist, 'pop': pop})
        
    return pd.DataFrame(data_rows)

def district_splits(raw_df):

    # get total pop per community (water1, water2..)
    total_pops = raw_df.groupby(['category', 'community_id'])['pop'].sum().reset_index()
    total_pops.rename(columns={'pop': 'total_pop'}, inplace=True)
    #print(total_pops)

    # get pop per community and district
    district_splits = raw_df.groupby(['category', 'community_id', 'district'])['pop'].sum().reset_index()

    # merge to get pop / total pop
    merged = pd.merge(district_splits, total_pops, on=['category', 'community_id'])
    return merged

#counting functions (using T threshold)
def count_preserved_counties(partition):
    raw_df = extract_data(partition)
    split_df = district_splits(raw_df)

    # The T values for county and water were if 6 or more of either community was maintained in a district
    # Couldn't really get a majority of these COIs with size 8 districts so 6 felt right, could always change
    # this allows for the c_pre variable to be more than the # of counties/water districts which isn't neccesarily bad I think
    T = 0.375
    c_pre = 0
    for row in split_df.itertuples():
        if row.category == 'county':
            if row.pop /row.total_pop >= T:
                c_pre += 1
    return c_pre

def count_preserved_water(partition):
    raw_df = extract_data(partition)
    split_df = district_splits(raw_df)

    T = 0.375
    w_pre = 0
   
    for row in split_df.itertuples():
        if row.category == 'water':
            if row.pop /row.total_pop >= T:
                w_pre += 1

    return w_pre

def count_preserved_muni(partition):
    
    raw_df = extract_data(partition)
    split_df = district_splits(raw_df)

    #since muni's are size 4 it was reasonable to say they were preserved if a district had 3 or 4 of a muni within it
    #hence the T threshold being 0.75 in this case

    T = 0.75
    m_pre = 0
   
    for row in split_df.itertuples():
        if row.category == 'muni':
            if row.pop /row.total_pop >= T:
                m_pre += 1

    return m_pre

def total_score(partition):
    county = count_preserved_counties(partition)
    water = count_preserved_water(partition)
    muni = count_preserved_muni(partition)

    #weights are arbitrary(ish)
    ts = county * 0.45 + water * 0.45 + muni *0.1
    return ts

#getting graph and intital partitions
graph = Graph.from_json('gerrymandria.json')
initial_partition = Partition(graph, assignment="district", updaters={
            'c_count' : count_preserved_counties,
            'w_count': count_preserved_water,
            'm_count': count_preserved_muni,
            'total_score': total_score
        }
)

water_partition = Partition(graph, assignment='water_dist')
muni_partition = Partition(graph, assignment='muni')
county_partition = Partition(graph, assignment='county')

#plotting different COIs and intitial partition
multi_plot(county_partition, water_partition, muni_partition, graph)
plot_partition(initial_partition, graph, "initial partition")

#markov chain stuff
total_population = sum(node.get('TOTPOP', 1) for node in graph.nodes.values())
target_pop = total_population / len(initial_partition.parts)

proposal = partial(recom, pop_col="TOTPOP", pop_target=target_pop, epsilon=0.05, node_repeats=2)
chain = MarkovChain(
        proposal=proposal,
        constraints=[contiguous],
        accept=accept.always_accept,
        initial_state=initial_partition,
        total_steps=1000
    )

#data for histograms
c_scores, w_scores, m_scores, total_scores = [], [], [], []
best_score = 0
best_map = None

for partition in chain:
    score = partition['total_score']

    c_scores.append(partition['c_count'])
    w_scores.append(partition['w_count'])
    m_scores.append(partition['m_count'])
    total_scores.append(partition['total_score'])

    if score > best_score:
        best_score = score
        best_map = partition
        



#histograms for different community scores
def hist(score):
    plt.hist(score, edgecolor='black')
    if score == c_scores:
        initial_score = initial_partition['c_count']
        label = "counties"
    elif score == w_scores:
        initial_score = initial_partition['w_count']
        label = "water"
    elif score == m_scores:
        initial_score = initial_partition['m_count']
        label = "munis"
    plt.axvline(initial_score, color='red', linestyle='dashed', linewidth=2, label=f'Initial Preserved: {initial_score:.3f}')
    plt.title('# of ' + label + ' preserved')
    plt.xlabel('# of ' + label + ' preserved in given partition')
    plt.ylabel('Frequency')
    plt.legend()
    plt.show()

hist(c_scores)
hist(w_scores)
hist(m_scores)

#histogram of total scores based on my specific metric
plt.hist(total_scores, bins = 25,  edgecolor='black')
initial_score = initial_partition['total_score']
plt.axvline(initial_score, color='red', linestyle='dashed', linewidth=2, label=f'Initial TCP: {initial_score:.3f}')
plt.title('total preservation score (bigger is better)')
plt.xlabel('different scores')
plt.ylabel('Frequency')
plt.legend()
plt.show()

plot_partition(best_map, graph, "most preserved map")
