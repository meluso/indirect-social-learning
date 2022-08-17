# -*- coding: utf-8 -*-
"""
Created on Fri Jan 14 11:05:44 2022

@author: John Meluso
"""

#%% Import libraries

# Import libraries
from itertools import product
import numpy as np
from patsy import dmatrices
import statsmodels.api as sm
import statsmodels.formula.api as smf
import statsmodels.iolib.summary2 as su2
import statsmodels.iolib.smpickle as pickle

# Import src files
from classes.Time import Time
import util.data as ud


#%% Regression Functions

def regress_points(model, slice_name, mode, out_var, out_log):
    '''Run regression on points.'''

    # Start timer
    time = Time()
    time.begin('Model', f'Regression for {slice_name}', model)

    # Load data
    filename = f'../data/sets/model{model}_{slice_name}.pickle'
    df = ud.load_pickle(filename)
    df = normalize_df(df, out_var, out_log)
    time.update('Data loaded')

    # Construct variable equations and results list
    equations = select_formula(mode, out_var, out_log)
    results = []
    time.update('Equations constructed')

    # Iterate through equations
    for ii, eq in enumerate(equations):

        # Run dataframe through patsy
        y, X = dmatrices(eq, data=df)
        res = sm.OLS(y, X).fit(cov_type='HC2',
            # cov_type='cluster',
            # cov_kwds=dict(groups=reg_df['team_fn']),
            parallel_method='joblib',
        )
        time.update('Model built & fit')

        # Add result to list
        results.append(res)
        time.update(f'Regression Model {ii+1} of {len(equations)} complete')

    time.end(f'Regressions for {slice_name}', model)
    return results

def select_formula(mode, out_var, out_log='linear'):
    '''Constructs a regression formula from the columns of the dataframe
    according to the specified mode.'''
    
    # Always include team size
    if out_var == 'team_productivity':
        include_always = ['np.log1p(run_step)']
    else:
        include_always = ['run_step','team_size']
    
    # Then select other include always variables based on mode
    if mode == 'fixed_by_fn_subtype':
        include_always.append('team_fn')
    elif mode == 'fixed_by_fn_type':
        include_always.append('team_fn_type') 
    elif mode == 'metrics':
        app = ['team_fn_alignment','team_fn_interdep','team_fn_difficulty']
        for aa in app: include_always.append(aa)
    
    # Add iterator variables
    include_iter = get_graph_vars()
    
    # Build equations
    return build_equation(include_always, include_iter, out_var, out_log)


def build_equation(include_always, include_iter, out_var, out_log='linear'):
    
    # Build array of equations
    eqs = []
    
    # Construct base equation
    if out_log != 'linear':
        eq_base = f'np.log{out_log}({out_var})' + ' ~ '
    else:
        eq_base = out_var + ' ~ '
    for ii, var in enumerate(include_always):
        if ii > 0:
            eq_base += ' + ' + var
        else:
            eq_base += var
    
    # # Iteratively build single-variable models from base equation
    # for var in include_iter:
    #     eqs.append(eq_base + ' + ' + var)
        
    # Build all-variable model from base equation
    all_vars = eq_base
    for var in include_iter:
        all_vars += ' + ' + var
    eqs.append(all_vars)
    
    return eqs


#%% Regression utilities

def normalize_df(df, out_var, out_log):
    
    norm_cols = get_graph_vars()
    if out_log != 'linear': norm_cols.append(out_var)
    
    for col in df.columns:
        if col in norm_cols:
            df[col] = normalize(df[col])
            
    return df


def normalize(df_col):
    return (df_col - df_col.mean()) / (df_col.max() - df_col.min())


def generate_table(model, slice_name, mode, results_list, out_var, out_log):
    
    # Get model names
    names = [f'{ii+1}' for ii, res in enumerate(results)]
    
    # Build variable order for table
    base_vars = ['Intercept','run_step','np.log10(run_step)','team_size']
    graph_vars = get_graph_vars()
    var_list = [base_vars, graph_vars]
    order = [var for sub_list in var_list for var in sub_list]

    # Construct table from results
    table = su2.summary_col(
        results_list,
        model_names=names,
        stars=True,
        regressor_order=order
        )
    
    # Set out_log variable
    if out_log != 'linear': out_log = f'log{out_log}'
    
    # Save Table to Pickle
    file = f'../data/regression/reg_{out_log}_{out_var}_{mode}_model{model}_{slice_name}.pickle'
    pickle.save_pickle(table, file)
    
    # Save Table to Text File
    file = f'../figures/regression/reg_{out_log}_{out_var}_{mode}_model{model}_{slice_name}.txt'
    with open(file, 'w') as output:
        output.write(table.as_text())
        
        
#%% Variable builders

def get_graph_vars():
    
    return [
        'team_graph_centrality_degree_mean',
        'team_graph_centrality_degree_stdev',
        'team_graph_centrality_eigenvector_mean',
        'team_graph_centrality_eigenvector_stdev',
        'team_graph_centrality_betweenness_mean',
        'team_graph_centrality_betweenness_stdev',
        'team_graph_nearest_neighbor_degree_mean',
        'team_graph_nearest_neighbor_degree_stdev',
        'team_graph_clustering',
        'team_graph_assortativity',
        'team_graph_pathlength',
        'team_graph_diameter'
        ]        


#%% Running code

def run_regression(model, slice_name, mode, out_var, out_log='linear'):
    results = regress_points(model, slice_name, mode, out_var, out_log)
    generate_table(model, slice_name, mode, results, out_var, out_log)
    return results

if __name__ == '__main__':
    
    # models = ['3xx','3xg']
    # reg_types = ['fixed_by_fn_subtype']
    # out_vars = ['team_performance','team_productivity']
    # out_logs = ['linear', 10]
    
    models = ['3xg']
    reg_types = ['fixed_by_fn_subtype']
    out_vars = ['team_productivity']
    out_logs = [10]
    
    results = {}
    iterator = product(models, reg_types, out_vars, out_logs)
    for model, reg, out_var, out_log in iterator:
        results[f'{model}_{reg}_{out_var}_{out_log}'] \
            = run_regression(model, 'team_is_nbhd', reg, out_var, out_log)
