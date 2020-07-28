print('imports...', end='', flush=True)
from tqdm import tqdm
import time
import sys
import pandas as pd
import re
from pprint import pprint
import numpy as np
import signal
from matplotlib import pyplot as plt
import seaborn as sns

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 500)
pd.set_option('display.width', 1000)

PICKLE_PATH = 'generated_files/main.pkl'
PICKLES = [
    'generated_files/autotrader_wc.pkl',
    'generated_files/cars_wc.pkl',
    'generated_files/gumtree_wc.pkl',
    'generated_files/surf4cars_wc.pkl',
]
print('done')


def main():
    df = calc_derivatives(join_together(PICKLES))
    low_zar, high_zar = df['price'].quantile([0.05, 0.95]).to_list()
    low_kms, high_kms = df['kms'].quantile([0.05, 0.95]).to_list()
    top_makes = df['make'].value_counts()[:30].index.to_list()
    df = df[
        (df.price <= high_zar) &
        (df.price >= low_zar) &
        (df.kms <= high_kms) &
        (df.kms >= low_kms) &
        (df.year >= 2000) &
        (df['make'].isin(top_makes))
        ]
    df['year'] = df['year'].astype('category')
    x = 'price'
    y = 'kms'
    hue = 'year'
    facet = 'make'
    df[facet] = df[facet].cat.remove_unused_categories()
    g = sns.FacetGrid(df, col=facet, col_wrap=5, palette='cubehelix', hue=hue)
    g.map(plt.scatter, x, y, alpha=0.6)
    g.add_legend()
    plt.subplots_adjust(top=0.9)
    g.fig.suptitle(f'{x}-{y}({hue}-{facet})')
    plt.savefig(f'{x}-{y}({hue}-{facet})')

    # df = df[df['price'] >= 1_000_000]

    # df.sort_values('price')[useful]

    df['year'] = df['year'].astype('category')
    sns.scatterplot(x='price', y='kms', hue='website', data=df, palette='hls')
    plt.show()
    useful = [
        'title',
        'price',
        'year',
        'kms',
        'kms_per_year',
        'website',
        'uid'
    ]
    print('done')


def plot_each_make():
    df = calc_derivatives(join_together(PICKLES))
    x = 'price'
    y = 'kms'
    hue = 'year'
    facet = 'model'
    makes = df.groupby('make')['model'].nunique().sort_values()[-15:].index.to_list()
    for i, make in enumerate(makes):
        print(f'Plotting {make} ({i}/{len(makes)})')
        df = calc_derivatives(join_together(PICKLES))
        low_zar, high_zar = df['price'].quantile([0.05, 0.95]).to_list()
        low_kms, high_kms = df['kms'].quantile([0.05, 0.95]).to_list()
        df = df[
            (df.price <= high_zar) &
            (df.price >= low_zar) &
            (df.kms <= high_kms) &
            (df.kms >= low_kms) &
            (df.year >= 2000) &
            (df['make'] == make)
            ]
        df['year'] = df['year'].astype('category')

        df[facet] = df[facet].cat.remove_unused_categories()
        if len(df) > 0:
            g = sns.FacetGrid(df, col=facet, col_wrap=5, palette='cubehelix', hue=hue)
            g.map(plt.scatter, x, y, alpha=0.6)
            g.add_legend()
            plt.subplots_adjust(top=0.9)
            g.fig.suptitle(f'{make.title()})')
            plt.savefig(f'per_make/{make}-{x}-{y}({hue}-{facet})')

def plot_expensive():
    expensives = [
        'jaguar',
        'porsche',
        'mercedes-amg',
        'bmw',
        'ferrari',
        'mercedes-benz',
    ]
    df = calc_derivatives(join_together(PICKLES))
    df = df[(df['make'].isin(expensives)) &
            (df['kms'] <= 500_000)]
    df['year'] = df['year'].astype('category')
    x = 'price'
    y = 'kms'
    hue = 'year'
    facet = 'make'
    df[facet] = df[facet].cat.remove_unused_categories()
    g = sns.FacetGrid(df, col=facet, col_wrap=2, palette='cubehelix', hue=hue)
    g.map(plt.scatter, x, y, alpha=0.6)
    g.add_legend()
    plt.subplots_adjust(top=0.9)
    g.fig.suptitle(f'{x}-{y}({hue}-{facet}) ZAR >= 1000000')
    plt.savefig(f'{x}-{y}({hue}-{facet}) ZAR >= 1000000')

def plot_heavy_duty():
    makes = [
        'isuzu',
        'land-rover',
        'land rover',
        'jeep',
    ]
    df = calc_derivatives(join_together(PICKLES))
    df = df[(df['make'].isin(makes)) &
            (df['price'] <= 1_500_000 ) &
            (df['kms'] <= 400_000 )
            ]
    df['year'] = df['year'].astype('category')
    x = 'price'
    y = 'kms'
    hue = 'year'
    facet = 'make'
    df[facet] = df[facet].cat.remove_unused_categories()
    g = sns.FacetGrid(df, col=facet, col_wrap=2, palette='cubehelix', hue=hue)
    g.map(plt.scatter, x, y, alpha=0.6)
    g.add_legend()
    plt.subplots_adjust(top=0.9)
    g.fig.suptitle(f'{x}-{y}({hue}-{facet}) heavy duty')
    plt.savefig(f'price-kms(year-make)heavy_duty.png')

def join_together(paths):
    dfs = []
    for p in paths:
        try:
            dfs.append(pd.read_pickle(p))
        except (FileNotFoundError, KeyError):
            dfs.append(pd.DataFrame())
            dfs[-1].to_pickle(p)

    df = pd.concat(dfs, ignore_index=True, sort=False)
    df['province'] = 'western_cape'
    numerics = [
        'year',
        'price',
        'kms'
    ]
    df[numerics] = df[numerics].astype('float64')

    categoricals = [
        'make', 'model', 'fuel_type', 'transmission',
        'color', 'variant', 'website', 'province'
    ]
    df[categoricals] = df[categoricals].astype('category')
    return df

def calc_derivatives(df):
    df['kms_per_year'] = df['kms'] / (2021 - df['year'])
    df['zar_100km'] = df['price'] * df['kms'] / 100.0
    return df



if __name__ == '__main__':
    main()
