# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 19:25:34 2017

@author: wunch_group
"""
import numpy as np
import datetime as dt
import pytz
from network_functions import write_to_remote_Daemon
utc = pytz.timezone("UTC")
np.set_printoptions(suppress=True)


def attach_date(sat_time):
    """" this function attaches a date to utc times from the gps
         and returns YYYY-MM-DD HHMMSS.ffff
    """
    date_str = dt.datetime.now(utc).date().isoformat()
    return date_str + " " + str(sat_time)


class AMR_Daemon(object):
    """this object holds the AMR function"""
    def __init__(self):
        self.stuff = "Hi, this is AMR_Daemon"

    def data_read(self):
        """define empty lists, accuarccy and open local log file and write
           header
        """
        global LGR_local_log, mode, AMR_local_log
        global AMR_ser, LGR_ser, avg_time
        global AMR_avg_list
        temp = []
        AMR_avg_list = []
        global AMR_data
        global AMR_t
        global LGR_data
        accuracy = 1  # instrument accuarcy

        AMR_local_log_file = open(AMR_local_log, mode="a")
        AMR_local_log_file.write("time, lat, lon, alt,  temp, wd," +
                                 "ws, pressure," +
                                 " hdop\r\n")
        AMR_local_log_file.flush()

        if LGR_ser == "":
            LGR_data = str([np.nan]*5)[1:-1]
            local_step = "n"

        while True:
            x = str(AMR_ser.readline())[2:-1]  # read data from AMR COM Port
            temp.append(x)  # append to a temporary list
            """this if else block waits for temp to have 3 elements"""
            if len(temp) == 3:
                """once 3 elements in temp, we split the
                   data in temp by instrument type
                   data from each sensor, pressure, gps and meterological
                """
                gps = [lin for lin in temp if lin[0:6] == "$GPGGA"]
                met = [lin for lin in temp if lin[0:6] == "$WIMDA"]
                pre = [lin for lin in temp if lin[0:6] == "$YXXDR"]
                if ((bool(gps)) and (bool(met)) and (bool(pre))):
                    met = [x.strip() for x in met[0].split(",")]
                    """format: pressure in bars, B, temp in celsius,
                       C, ,,,,,,true wind dir, T,
                       magnetic wind dir, M, true ws in knots, N,
                       true ws in ms , M
                    """
                    gps = [x.strip() for x in gps[0].split(",")]
                    """format: utc time, lat,N/s, lon,W/E, fix quality,
                               number of satalites, hdop, altiude, M,
                               mean sea level , M,, checksum
                    """
                    pre = [x.strip() for x in pre[0].split(",")]
                    """format: """
                    try:
                        lat = str(gps[2])
                        lat = float(lat[0:2]) + float(lat[2:])/60.
                        lon = str(gps[4])
                        lon = -float(lon[0:3]) - float(lon[3:])/60.
                        alt = float(gps[9])
                        hdop = float(gps[8])
                        AMR_t = attach_date(gps[1])
                    except ValueError:
                        print("Not connected to satalite")
                        lat, lon, alt, AMR_t, hdop = (np.nan, np.nan,
                                                      np.nan, np.nan,
                                                      np.nan
                                                      )
                    """to do, look at wind spped and pressuer for ful time
                        comparison time series and make temperature plots to
                        show Debra abouut lag
                    """
                    vars_str = [AMR_t, str(lat), str(lon), str(alt), met[5],
                                met[13], met[-2]*0.615 + 0.378,
                                str(float(pre[-3])*1000.*1.003 - 2.751),
                                str(hdop*accuracy)
                                ]
                    temp = []
                    var_num = []
                    for var in vars_str:
                        try:
                            var = float(var)
                        except ValueError:
                            var = np.nan
                        var_num.append(var)
                    var_num[0] = AMR_t
                    AMR_raw_data = tuple(var_num)
                    AMR_avg_list.append(AMR_raw_data)
                    AMR_raw_data = str(AMR_raw_data)[1:-1]
                    """write to raw data to local log file"""
                    AMR_local_log_file.write(AMR_raw_data + "\r\n")
                    AMR_local_log_file.flush()

                    """determine when averaging of back data occurrs, either
                       triggered by LGR or by length of list depending
                       on which instruments are connected
                    """
                    if LGR_ser != "":
                        global data_step
                        local_step = data_step
                    else:
                        if len(AMR_avg_list) == avg_time:
                            local_step = "y"
                        else:
                            local_step = "n"
                    """once trigger occurrs we average the AMR data and use
                       the write server function to send data to server
                    """
                    if local_step == "y":
                        data_step = "n"
                        local_step = "n"
                        data_list = np.array(AMR_avg_list)[:, 1:].astype("f8")
                        a = int(round(len(AMR_avg_list)/2 - 1))
                        ts = np.array(AMR_avg_list)[:, 0][a]
                        data_avg = np.average(data_list,  axis=0).astype("str")
                        data_avg = np.insert(data_avg, 0, ts)
                        AMR_data = ""
                        for var in data_avg:
                            AMR_data = AMR_data + str(var) + ","
                        AMR_data = AMR_data[:-1]
                        if mode != "locally":
                            write_to_remote_Daemon.prep_data_string()
                        AMR_avg_list = []
                else:
                    print("Sentences are missing")
                    temp = []


class LGR_Daemon(object):
    def __init__(self):
        self.stuff = "hi this is LGRDaemon"

    def data_read(self):
        global LGR_local_log, mode, AMR_local_log
        global AMR_ser, LGR_ser, avg_time
        LGR_local_log_file = open(LGR_local_log, mode="a")
        LGR_local_log_file.write("lgr_time, ch4, ch4se, h2o, " +
                                 "h2ose, co2, co2se, co, cose, ch4d, " +
                                 "ch4dse, co2d, co2dse, cod, codse, gasp, " +
                                 "gaspse, t, tse, amb, ambse, rd1, rd1se, " +
                                 "rd2, rd2se" + "\r\n"
                                 )
        global data_step
        global LGR_data, LGR_avg_list, AMR_data
        LGR_avg_list = []
        LGR_local_step = "n"
        if AMR_ser == "":
            AMR_datat = [np.nan]*9
            AMR_data = ""
            for a in AMR_datat:
                AMR_data = AMR_data + str(a) + ","
            AMR_data = AMR_data[:-1]
        while True:
            LGR_str = str(LGR_ser.readline())[2:-1].split(",")[0:-7]
            x = LGR_str[1:]
            x = [float(y) for y in x]
            try:
                err = instrument_chk(x[20], x[22],  x[14])
            except IndexError:
                print("Missing Data String from LGR")
                continue
            if err != "":
                print(err)
                break
            """local log write with instrument time and comp time
               at measurement
            """
            LGR_t = LGR_str[0][1:]
            x.insert(0, LGR_t)
            LGR_raw_data = ""
            for var in x:
                LGR_raw_data = LGR_raw_data + str(var) + ", "
            LGR_raw_data = LGR_raw_data[1:-2]
            LGR_local_log_file.write(LGR_raw_data + "\r\n")
            LGR_local_log_file.flush()
            if len(LGR_avg_list) == avg_time:
                LGR_local_step = "y"
            print("/")
            LGR_avg_list.append(x)
            if LGR_local_step == "y":
                data_step = "y"
                data_list = np.array(LGR_avg_list)[:, 1:].astype("f8")
                data_list = np.round(data_list, 3)
                ts = np.array(LGR_avg_list)[:, 0
                                            ][int(len(LGR_avg_list)/2) - 1]
                data_avg = np.average(data_list, axis=0)
                data_avg = data_avg.astype("str")
                data_avg = np.insert(data_avg, 0, ts[1:])

                data_avg = np.array([data_avg[0], data_avg[9], data_avg[11],
                                     data_avg[13], data_avg[3],
                                     data_avg[-1]
                                     ]
                                    )
                LGR_data = ""
                for var in data_avg:
                    LGR_data = LGR_data + str(var) + ","
                LGR_avg_list = []
                if mode != "locally" and AMR_ser == "":
                    write_to_remote_Daemon.prep_data_string()
                LGR_local_step = "n"


def instrument_chk(rd1i, rd2i, presi):
    rd10 = 7.21
    rd20 = 7.65
    pres0 = 140.5
    err = ""
    if (abs(rd1i - rd10)/rd10) >= 0.20:
        err = (err + "Time- " + str(dt.datetime.now(utc)) +
               "Laser 1 ringdown time is too low." +
               "Please clean mirrors soon\r\n"
               )
    elif (abs(rd2i - rd20)/rd20) >= 0.20:
        err = (err + "Time- " + str(dt.datitme.now(utc)) +
               "Laser 1 ringdown time is too low." +
               "Please clean mirrors soon\r\n"
               )
    elif (abs(pres0 - presi)) >= 20:
        err = (err + "Time- " + str(dt.datitme.now(utc)) +
               "Pressure within the caivity is too high or low, please check" +
               "intake and waste tubes for bloackages and leaks"
               )
    if err != "":
        print(err)
    return err
