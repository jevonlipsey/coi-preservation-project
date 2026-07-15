from common import plotting
import pandas as pd


chain1 = pd.read_csv('co\\data\\colorado_neutral_test_weights_300k.csv')
chain2 = pd.read_csv('co\\data\\colorado_neutral_test_weights_300k_v1.csv')

chain3 = pd.read_csv('mo\\data\\missouri_neutral_test_weights_150k.csv')
chain4 = pd.read_csv('mo\\data\\missouri_optimized_test_weights_150k.csv')

plotting.plot_mix(
    chain1,
    chain2,
    label_a="neutral 300k", 
    label_b="neutral 300k v1", 
    title="Colorado Neutral Acceptance Strategy Comparison"
    )