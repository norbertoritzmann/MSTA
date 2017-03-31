## This file will be the main py file
## It will include all necessary dependencies and libraries, it will run all steps of the algo
## In order to compile this file into an executable file we might need an additional program, also check the pyc extension

import data
import numpy as np
from historical_mean import HM
from linear_regression import LR
from core_base_algos import CMW, BIS
from tree import DT

## Global Hyperparameters
# The window size of the rolling window used to define each training set size
# The models will never see more than this number of points at once
rolling_window_size=500
    
# Output type : C for Classification, R for Regression
output_type='C'
# Note that for a Classification, 1 means positive return, -1 means negative, and 0 means bellow threshold
# In case of 3 class Classification, please provide an absolute level for the zero return threshold
# Fix it to 0 for a binary classification
# The optimal value can also be globally optimized as a result of the PnL optimisation and will be function of the volatility of the asset
threshold=0.001

# This dictionary of global hyperparameters will be passed an an argument of all built algorithms
global_hyperparams={'rolling_window_size':rolling_window_size,
                    'output_type':output_type,
                    'threshold':threshold}    

## Building the dataset
dataset=data.dataset_building(n_max=2000)
    
# We select an asset returns time series to predict from the dataset
asset_label='EURUSD Curncy'
Y=dataset[[asset_label]]
Y.dropna(inplace=True)
 
# With lags, used as X
lags=range(1,rolling_window_size+1)
X=data.lagged(Y,lags=lags) # In X please always include all the lags of Y that you want to use for the HM as first colunms
max_lags=max(lags)
# We could also turn X into classes data, is that meaningful?
# X=to_class(X,threshold)    

# In case of classification, we transform Y and put the classes labels into global_hyperparams 
if output_type=='C':
    Y=data.to_class(Y, threshold) # Notice that now the values of Y is the index of the class in classes

## Creating & calibrating the different algorithms

# First define a dictionary of algorithm associated with their names
# As arguments please include the fixed hyperparams of the model as a named argument
# For the hyperparameters grid to use in cross validation please provide a dictionary using sklearn syntax 
algos={'HM AR Full window':HM(global_hyperparams),#,hp_grid={'window_size':[10,100,500]}),
       'HM GEO Full window':HM(global_hyperparams,mean_type='geometric',hp_grid={'window_size':[1,10,50,100]}),
       'HM AR Short Term':HM(global_hyperparams,window_size=10),
       'LR':LR(global_hyperparams),
       'Lasso':LR(global_hyperparams, regularization='Lasso',hp_grid={'alpha':np.logspace(-4,1,5)}),
       'ElasticNet':LR(global_hyperparams, regularization='ElasticNet',hp_grid={'alpha':np.logspace(-3,1,20),'l1_ratio':np.linspace(0,1,20)}),
       'Tree':DT(global_hyperparams,hp_grid={'max_features':['sqrt',None]})}
    
# Then we just allow ourselves to work/calib/fit/train only a subsets of these algos
algos_used=algos.keys()
#algos_used=['Lasso']
#algos_used=['HM AR Full window']
#algos_used=['HM AR Full window','LR','Lasso']
#algos_used=['Tree']
algos_used=['ElasticNet']

for key in algos_used:
    # We let each algo select the relevent data to work on
    algos[key].select_data(X)

    for i in range(rolling_window_size+max_lags,len(Y.index)): # Note that i in the numeric index in Y of the predicted value
        train=range(i-rolling_window_size,i) # should be equal to i-rolling_window_size:i-1
        test=[i] # I am not sure of the index, we can check, it is inside [] to make sure the slicing produces a dataframe
        pred_index=Y.index[test] # This is the timestamp of i

        # We train all the algos on the testing set, it includes the calibration of hyperparameters and the fitting
        algos[key].calib(X.iloc[train],
                         Y.iloc[train],
                         pred_index,
                         cross_val_type='ts_cv',
                         n_splits=5,
                         calib_type='GeneticAlgorithm',
                         scoring_type=None,
                         n_iter=25,
                         init_pop_size=10, select_rate=0.5, mixing_ratio=0.5, mutation_proba=0.1, variance_ratio=0.1)

        # We build the predictions
        algos[key].predict(X.iloc[test],pred_index)

        # for debug
        print('{} rolling window {}/{}'.format(algos[key].name,i-rolling_window_size-max_lags+1,len(Y.index)-rolling_window_size-max_lags+1), end='\r')

    # We compute the outputs
    algos[key].compute_outputs(Y)
            
    # for debug
    print(algos[key].best_hp)
    pass

## Core algorithm
# Definition of the core algo
core=HM(global_hyperparams) # Average of the predictions 
core=BIS(global_hyperparams, 'accuracy')

# We first built a new dataset with all the predictions for the algos, it will be our new X
X_core=data.core_dataset(algos, algos_used)
Y_core=Y.loc[X_core.index]

# Again we do the rolling window estimation process
for i in range(rolling_window_size+1,len(Y_core.index)): # Note that i in the numeric index in Y of the predicted value
    train=range(i-rolling_window_size,i) # should be equal to i-rolling_window_size:i-1
    test=[i] # I am not sure of the index, we can check, it is inside [] to make sure the slicing produces a dataframe
    pred_index=Y_core.index[test] # This is the timestamp of i

    # We train all the algos on the testing set, it includes the calibration of hyperparameters and the fitting
    core.calib(X_core.iloc[train],Y_core.iloc[train],pred_index)

    # We build the predictions
    core.predict(X_core.iloc[test],pred_index)

    # for debug
    print('Core Algo: {} rolling window {}/{}'.format(core.name,i-rolling_window_size+1,len(Y_core.index)-rolling_window_size+1), end='\r')

# We compute the outputs
core.compute_outputs(Y_core)
            
# We check that the core algo is better than all other algos:
scoring='accuracy'
for algo in algos_used:
    if getatr(algos[key],scoring)>getattr(core,scoring): print('Warning: {} got a better score than the core algo {}'.format(algos[key].name, core.name))

# for debug
print(core.best_hp)
pass

## Trading Strategy


## Backtest/Plots/Trading Execution

## Use zipline here

