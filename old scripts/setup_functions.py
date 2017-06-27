# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 18:55:48 2017

@author: wunch_group
"""
import datetime as dt

import getpass
import serial
import pytz
from network_functions import open_remote
utc = pytz.timezone("UTC")

in_file = [x.rstrip() for x in open("./lgr_amr.infile", mode="r").readlines()]


def logging_setup():
    global hostname, port, username, password, file_path, remote_plot_file
    global LGR_local_log, mode, AMR_local_log, remote_write_period
    mode = in_file[0]
    if mode == "remotely":
        hostname = in_file[1]
        port = int(in_file[2])
        username = in_file[3]
        password = getpass.getpass()
        file_path = in_file[4]
        remote_plot_file = in_file[5]
        LGR_local_log = in_file[6] + "_" + dt.date.today().isoformat()
        AMR_local_log = in_file[7] + "_" + dt.date.today().isoformat()
        open_remote()
    if mode == "locally":
        LGR_local_log = in_file[8] + "_" + dt.date.today().isoformat()
        AMR_local_log = in_file[9] + "_" + dt.date.today().isoformat()


def instrument_setup():
    global AMR_ser, LGR_ser, avg_time
    """get location of instruments"""
    while True:
        AMR_loc = in_file[10]
        if AMR_loc != "":
            print("Trying to connect to AMR at " + AMR_loc)
            try:
                AMR_ser = serial.Serial(AMR_loc, baudrate=4800, timeout=2)
                print("AMR found at " + AMR_loc)
                break
            except:
                print("AMR not found at " + AMR_loc)
                continue
        else:
            print("Not using AMR")
            AMR_ser = ""
            break
    while True:
        LGR_loc = in_file[11]
        if LGR_loc != "":
            print("Trying to connect to LGR at " + LGR_loc)
            try:
                LGR_ser = serial.Serial(LGR_loc, baudrate=9600, timeout=2)
                print("LGR found at " + LGR_loc)
                break
            except:
                print("LGR not found at " + LGR_loc)
                continue
        else:
            print("Not using LGR")
            LGR_ser = ""
            break
    avg_time = int(in_file[12])
