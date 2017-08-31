#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Aug  8 09:37:01 2017

@author: sajjan
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def sync_data(meas_date, AMR_data_dir="./local_log/raw_data/",
              LGR_data_dir="./local_log/raw_data/", lgr_lag=0):
    """this function syncronizses the 1 second data files from the LGR-AMR.py
       script. It requires the measurement date to be syncronized 
       and opitonally the
       directories where the LGR and AMR data are located and the 
       response delay of the LGR in seconds, with a lag being positive
     """
    """first read amr data into a pd dataframe with computer time as index"""
    print(meas_date)
    print("AMR")
    AMR_data = pd.read_csv(AMR_data_dir + "AMR_log_" + meas_date,
                           sep=",", index_col=-1,
                           error_bad_lines=False, warn_bad_lines=True,
                           parse_dates=[0, -1], na_values=" nan"
                           ).dropna()
    AMR_data = AMR_data[~AMR_data.index.duplicated(keep="first")]
    """convert gps time to epoch time"""
    AMR_data.gps_time = AMR_data.gps_time.astype(np.int64) / 10**9
    """next read lgr data""" 
    print("LGR")
    LGR_data = pd.read_csv(LGR_data_dir + "LGR_log_" + meas_date,
                           sep=",", index_col=-1,
                           error_bad_lines=False, warn_bad_lines=True,
                           parse_dates=[-1]
                           ).dropna()
    LGR_data = LGR_data[~LGR_data.index.duplicated(keep="first")]
    """shift LGR index backwards by the lgr_lag. This accounts for
       the measuremnt lag in the instument. Note that the lag must be 
       enterred as a positve value
    """"
    LGR_data.index = LGR_data.index - pd.Timedelta(seconds=lgr_lag)
    
    """join datasets, this creates a new dataset with columns from
       both the LGR and AMR and with all their indices
    """
    survey_data = pd.concat([AMR_data, LGR_data]).sort_index()
    survey_data = survey_data.loc[pd.notnull(survey_data.index)]

    """interpolate LGR data to the AMR computer times and hence to the gps
       times, two steps first interpolate all data to all times in index
       then only keep the AMR times in index
    """
    survey_data = survey_data.interpolate(method="time")
    survey_data = survey_data[~survey_data.index.duplicated(keep="first")]
    survey_data = survey_data.reindex(AMR_data.index)
    """repalce computer time with gps time in index and conver gps from
       from epoch time back to a datetime
    """
    survey_data.index = pd.to_datetime(survey_data["gps_time"], unit="s")
    """drop se columns, all 0 as only 1 data point in 
       each 1 second averaging period
    """
    survey_data = survey_data.drop(["ambse", "ch4dse", "ch4se", "co2dse",
                                    "co2se", "codse", "cose", "gaspse",
                                    "gps_time",
                                    "h2ose", "lgr_time", "rd1se", "rd2se",
                                    "tse"
                                    ], axis=1
                                   )
    """save as csv"""
    survey_data.to_csv("./sync_data_" + meas_date + ".txt")
    """print dataset head and plot the orignal data
       with the sync data so we can sanity check the data
    """
    survey_data.ch4d.plot()
    LGR_data.ch4d.plot()
    plt.show()
    print(survey_data.head())
    return survey_data