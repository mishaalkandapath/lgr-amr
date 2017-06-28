#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 18:55:48 2017

@author: sajjan
"""
import datetime as dt
import numpy as np
import socket
from threading import Thread
from getpass import getpass
from serial import Serial
from pytz import timezone
from paramiko import SSHClient, AutoAddPolicy
from time import sleep

np.set_printoptions(suppress=True)
utc = timezone("UTC")


"""
Section 1- Setup of Instrument and logging using in_file
"""


def logging_setup(in_file):
    """define global varibles for logging setup"""
    global hostname, port, username, password, file_path, remote_plot_file
    """varibles for opening ssh port with remote machine"""
    global remote_write_period, err_log
    """how often attempt to write to server, important as we don't want to
       ping server too freqeuntly"""
    global LGR_local_log, mode, AMR_local_log, local_plot_file
    """define local log files and if we're writing locally or remotely
       also define the local copy of the remote plotting file
    """
    err_log = open("./errors/error_log", mode="a")
    remote_plot_file = in_file[5]
    local_plot_file = open(("./local_log/web_data/" + remote_plot_file + "_" +
                            dt.date.today().isoformat()
                            ), mode="a+"
                           )
    mode = in_file[0]
    LGR_local_log = in_file[6] + "_" + dt.date.today().isoformat()
    AMR_local_log = in_file[7] + "_" + dt.date.today().isoformat()
    if mode == "remotely":
        """in remote mode, we define server varibles and open an ssh port
            using the varibales defined here
        """
        hostname = in_file[1]
        port = int(in_file[2])
        username = in_file[3]
        password = getpass(prompt="Please type password to remote machine " +
                           "for user " + username + "@" + hostname
                           )
        file_path = in_file[4]
        open_remote()
    """in local mode we only write to the local log files, defined above
    """
    return


def instrument_setup(in_file):
    global AMR_ser, LGR_ser, avg_time
    """define global serial connections and averaging times"""
    avg_time = int(in_file[10])
    AMR_loc = in_file[8]
    if AMR_loc != "":
        print("Trying to connect to AMR at " + AMR_loc)
        try:
            AMR_ser = Serial(AMR_loc, baudrate=4800, timeout=1)
            print("AMR found at " + AMR_loc)
        except KeyboardInterrupt:
            raise
        except:
            print("AMR not found at " + AMR_loc)
            print("Not using AMR")
            AMR_ser = ""
    else:
        print("Not using AMR")
        AMR_ser = ""
    """this try except and if statemetn block looks for AMR at postion
        given in infile
       and if we can't find it or if the infile has no locations
       we define the AMR port as ""
    """
    LGR_loc = in_file[9]
    if LGR_loc != "":
        print("Trying to connect to LGR at " + LGR_loc)
        try:
            LGR_ser = Serial(LGR_loc, baudrate=9600, timeout=1)
            print("LGR found at " + LGR_loc)
        except KeyboardInterrupt:
            raise
        except:
            print("LGR not found at " + LGR_loc)
            print("Not using LGR")
            LGR_ser = ""
    else:
        print("Not using LGR")
        LGR_ser = ""
    """identical functionality as above"""
    return

"""
Section 2- Definition of Netowrk Fucntions and create Network logging Daemon
"""

"""
data header
 time,lat,lon,alt,temp,wd,ws,pressure,hdop,lgr_time, ch4d, co2d,
 cod, water, averaging time, computer time
;
"""


def is_connected():
    """this fucntion is useful for cehccking connection quickly before
       writing to remote as time for the script to realise the channel is
       is approximately 30 seconds
    """
    global network_status
    """asks for host name as IPV4 address if returned, we're online"""
    try:
        socket.gethostbyname("www.google.ca")
        network_status = "online"
    except socket.gaierror:
        network_status = "offline"
    finally:
        print(network_status)
        return


def prep_data_string():
    """this function concatantes amr and lgr data strings
       It also writes the prepared string to the local
       copy of the file uploaded to the server
    """
    global AMR_data, LGR_data, avg_time, data_str
    global local_plot_file

    data_str = ((AMR_data + "," + LGR_data + "," + str(avg_time) + "," +
                 str(dt.datetime.now()) + ";\n"
                 )
                )
    print(data_str)
    local_plot_file.write(data_str)
    local_plot_file.flush()


def open_remote():
    """function returns a global secrue file transfer prtocool channel using
       the variables from logging setup. this sftp
       is used to write to the remote machine
    """
    global sftp, file_object, network_status
    global hostname, port, username, password, file_path, remote_plot_file
    try:
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password, port=port
                    )
        sftp = ssh.open_sftp()
        sftp.chdir(path=file_path)
        file_object = sftp.file(remote_plot_file + ".txt", mode="a",
                                bufsize=-1
                                )
        network_status = "online"
        print("Connected to " + hostname)
    except KeyboardInterrupt:
        raise
    except:
        print("Could not connect to " + hostname + " cacheing data")
        network_status = "offline"
    return


class write_to_remote_Daemon(object):
    """this class defines a remoe writing thread that attempts to write to
       the remote machine every remote write period and if this fails, it
       attempts to reconnect it also sets the global network status
    """
    def __init__(self):
        """intialises the daemon and sets the line we read from in the loca
           copy of the remote machine data to 0
        """
        global local_file_step
        self.stuff = "Hi, this is Remote Daemon"
        local_file_step = 0

    def write_to_remote(self):
        global sftp, file_object
        global network_status
        global local_file_step, remote_data_str

        while True:
                sleep(int(in_file[11]))
                """sleep so we aren't pinging remote machine too freqeunctly"""
                if network_status == "online":
                    try:
                        local_plot_file.seek(0)
                        for i, l in enumerate(local_plot_file):
                            if i >= local_file_step:
                                if len(l.split(",")) != 16:
                                    continue
                                else:
                                    file_object.write(l)
                                    print("Successfully wrote new lines to " +
                                          "remote " +
                                          "machine")
                                local_file_step = local_file_step + 1
                            else:
                                continue

                    except KeyboardInterrupt:
                        raise
                    except:
                        network_status = "offline"
                        print("Failure")
                        continue
                    """first if statement checks if network status is
                       set to online
                       and if it is, it tries to write through the sftp
                       channel, it
                       writes all unwritten lines in the local_plot_file
                       by moving
                       to the line immediately after last written line
                   """
                elif network_status == "offline":
                    try:
                        open_remote()
                        print(network_status)
                    except KeyboardInterrupt:
                        raise
                    except:
                        network_status = "offline"
                        print(network_status)
                        continue
                """if network status was offfline then we attmept to reconnect
                    with open remote function
                """
#            except KeyboardInterrupt:
#                raise
#            except:
#                continue


"""
Section 3- Define Instrument Reading and Processing Daeemons
"""


def attach_date(satalite_time):
    """" this function attaches a date to utc times from the gps
         and returns YYYY-MM-DD HHMMSS.ffff
    """
    date_str = dt.datetime.now(utc).date().isoformat()
    return date_str + " " + str(satalite_time)


def find_average_time(time_array, format_str):
    time_list = [dt.datetime.strptime(x, format_str
                                      )
                 for x in time_array
                 ]
    t0 = time_list[0]
    tf = time_list[-1]
    time_delta = tf - t0
    t_middle = t0 + time_delta/2.
    return t_middle


class AMR_Daemon(object):
    """this object holds the AMR function"""
    def __init__(self):
        self.stuff = "Hi, this is AMR_Daemon"

    def data_read(self):
        """define empty lists, accuarccy and open local log file and write
           header to it
        """
        global LGR_local_log, mode, AMR_local_log
        global AMR_ser, LGR_ser, avg_time
        global AMR_avg_list
        global AMR_data, LGR_data, AMR_t

        accuracy = 1  # instrument accuarcy
        temp = []
        AMR_avg_list = []
        AMR_local_log_file = open(AMR_local_log, mode="a")
        AMR_local_log_file.write("time, lat, lon, alt,  temp, wd," +
                                 "ws, pressure," +
                                 " hdop\r\n")
        AMR_local_log_file.flush()

        if LGR_ser == "":
            LGR_data = str([np.nan]*5)[1:-1]
            local_step = "n"
        """if thelgr isn't connected, we set its data as a list of nans"""
        while True:
                x = str(AMR_ser.readline())[2:-5]
                print("\\")
                """read lines from com port"""
                temp.append(x)
                """append data to the temp file"""
                """this if else block waits for temp to have 4 elements"""
                if len(temp) == 4:
                    """once 3 elements in temp, we split the
                       data in temp by instrument type
                       data from each sensor, pressure, gps and meterological
                    """
                    gps = [lin for lin in temp if lin[0:6] == "$GPGGA"]
                    met = [lin for lin in temp if lin[0:6] == "$WIMDA"]
                    pre = [lin for lin in temp if lin[0:6] == "$YXXDR"]
                    win = [lin for lin in temp if lin[0:6] == "$WIMWD"]
                    if (bool(gps) and bool(met) and bool(pre) and bool(win)):
                        """if we have one of each of the amr strings in the
                           triplet
                           we proecess them, else they are thrown out
                        """
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
                        win = [x.strip() for x in win[0].split(",")]
                        try:
                            lat = str(gps[2])
                            lat = float(lat[0:2]) + float(lat[2:])/60.
                            lon = str(gps[4])
                            lon = -float(lon[0:3]) - float(lon[3:])/60.
                            alt = float(gps[9])
                            hdop = float(gps[8])
                            AMR_t = attach_date(gps[1])
                        except ValueError:
                            lat, lon, alt, AMR_t, hdop = (np.nan, np.nan,
                                                          np.nan, np.nan,
                                                          np.nan
                                                          )
                        """this try except block handles if the AMR isn't
                           conneceted to gps, we write nans if not connected
                        """
                        # TODO: to do, ask Colin to put calibrations on his end
                        try:
                            pres = float(pre[-3])*1000.
                        except ValueError:
                            pres = np.nan
                        """ditto as last try except"""
                        vars_str = [AMR_t, str(lat), str(lon), str(alt),
                                    met[5],
                                    win[1], win[7],
                                    str(pres),
                                    str(hdop*accuracy)
                                    ]
                        temp = []
                        var_num = []
                        """here we cleared temp list and defined the lsit that
                           will
                           hold the data in a numeric format
                        """
                        for var in vars_str:
                            try:
                                var = float(var)
                            except ValueError:
                                var = np.nan
                            var_num.append(var)
                        """here we filled the numeric list and filled the
                            missing
                            data with nans
                         """
                        var_num[0] = AMR_t
                        AMR_raw_data = tuple(var_num)
                        AMR_avg_list.append(AMR_raw_data)
                        """append the data tuple to an averaging list"""
                        AMR_raw_data = str(AMR_raw_data)[1:-1]
                        AMR_local_log_file.write(AMR_raw_data + "\r\n")
                        AMR_local_log_file.flush()
                        """write to raw data to local log file"""

                        """determine when averaging of back data occurrs,
                           either
                           triggered by LGR or by length of AMR list
                           depending
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
                        """once local step triger occurrs we average the AMR
                           data
                           and use
                           the write to the local copy of the file sent to the
                           remote machine
                        """
                        if local_step == "y":
                            data_step = "n"
                            local_step = "n"
                            """reset averaging triggers"""
                            data_list = np.array(AMR_avg_list)[:, 1:
                                                               ].astype("f8")
                            data_avg = np.average(data_list,  axis=0)
                            lat, lon = data_avg[0], data_avg[1]
                            data_avg = np.round(data_avg, 3)
                            """average data in avg list and round all values"""
                            data_avg[0] = lat
                            data_avg[1] = lon
                            """replace lat and lon fields with unrounded values
                               for plotting
                            """

                            data_avg = data_avg.astype("str")
                            time_array = np.array(AMR_avg_list)[:, 0]
                            try:
                                t_middle = find_average_time(time_array,
                                                             "%Y-%m-%d" +
                                                             " %H%M%S.%f"
                                                             )
                            except TypeError:
                                t_middle = np.nan
                            data_avg = np.insert(data_avg, 0, t_middle)
                            """add the average time in the measurement period
                                to
                                the start of the array
                            """

                            AMR_data = ""
                            """reset data string"""
                            for var in data_avg:
                                AMR_data = AMR_data + str(var) + ","
                            AMR_data = AMR_data[:-1]
                            prep_data_string()
                            """write data in averaging array to a string and
                               use
                               prep data to concatentate with the LGR data
                               and
                               write to the local copy of the remote plotting
                               file
                            """
                            AMR_avg_list = []
                            """reset aveeragign list"""
                    else:
                        print("Sentences are missing")
                        temp = []


class LGR_Daemon(object):
    def __init__(self):
        self.stuff = "Hi this is LGRDaemon"

    def data_read(self):
        global LGR_local_log, mode, AMR_local_log
        global AMR_ser, LGR_ser, avg_time, err_log
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
                xlist = []
                for y in x:
                    try:
                        xlist.append(float(y))
                    except KeyboardInterrupt:
                        raise
                    except:
                        xlist.append(np.nan)
                """above block converts string to floats and handles
                   missing data fields
                """
                x = xlist
                try:
                    err = instrument_chk(x[20], x[22],  x[14])
                except IndexError:
                    print("Missing Data String from LGR")
                    continue
                """Do an instument check and ensure string output from LGR
                   includes all variables
                """
                if err != "":
                    err_log.write(err)
                    err_log.flush()
                """local log write with instrument time and comp time
                   at measurement
                """
                LGR_t = LGR_str[0][2:]
                x.insert(0, LGR_t)
                LGR_raw_data = ""
                for var in x:
                    LGR_raw_data = LGR_raw_data + str(var) + ", "
                LGR_raw_data = LGR_raw_data[1:-2]
                LGR_local_log_file.write(LGR_raw_data + "\r\n")
                LGR_local_log_file.flush()
                "above writes data to local log file for LGR"""
                """once average list incluodes rigth number of measuremnts
                   we set LGR step to y and do an average
                """
                print("/")
                LGR_avg_list.append(x)
                if len(LGR_avg_list) == avg_time:
                    LGR_local_step = "y"

                if LGR_local_step == "y":
                    data_step = "y"
                    """above sets global data step to y and triggers amr daemon
                       averaging
                    """
                    data_list = np.array(LGR_avg_list)[:, 1:].astype("f8")
                    time_array = np.array(LGR_avg_list)[:, 0]
                    t_middle = find_average_time(time_array,
                                                 "%m/%d/%Y %H:%M:%S.%f"
                                                 )
                    data_avg = np.average(data_list, axis=0)
                    data_avg = np.round(data_avg, 3)
                    data_avg = data_avg.astype("str")
                    data_avg = np.insert(data_avg, 0, t_middle)

                    data_avg = np.array([data_avg[0], data_avg[9],
                                         data_avg[11],
                                         data_avg[13], data_avg[3],
                                         ]
                                        )
                    LGR_data = ""
                    for var in data_avg:
                        LGR_data = LGR_data + str(var) + ","
                    LGR_data = LGR_data[:-1]
                    LGR_avg_list = []
                    """similar processing AMR daemon"""
                    if AMR_ser == "":
                        prep_data_string()
                    """if AMR not attached then data prep done here, else it's
                       by AMR Daemon"""
                    LGR_local_step = "n"
                    """reset LGR averaging stepp"""



def instrument_chk(rd1i, rd2i, presi):
    """this function ensures the LGR is functioning properply"""
    rd10 = 7.21
    rd20 = 7.65
    pres0 = 140.5
    """laser ringdown times and cavity gas pressure when we initally got it"""
    err = ""
    if (abs(rd1i - rd10)/rd10) >= 0.20:
        err = (err + "Time- " + str(dt.datetime.now(utc)) +
               "Laser 1 ringdown time is too low." +
               "Please clean mirrors soon\r\n"
               )
        print(rd1i)
    elif (abs(rd2i - rd20)/rd20) >= 0.20:
        err = (err + "Time- " + str(dt.datetime.now(utc)) +
               "Laser 1 ringdown time is too low." +
               "Please clean mirrors soon\r\n"
               )
        print(rd2i)
    elif (abs(pres0 - presi)) >= 20:
        err = (err + "Time- " + str(dt.datetime.now(utc)) +
               "Pressure within the caivity is too high or low, please check" +
               "intake and waste tubes for bloackages and leaks"
               )
        print(presi)
    if err != "":
        print(err)
    return err

"""
Main Function Call, starts all daemons and does setup
"""


def main():
    global data_step, data_str
    global AMR_ser, LGR_ser, in_file

    in_file = [x.rstrip() for x in
               open("./lgr_amr.infile", mode="r").readlines() if x[0] != "#"
               ]

    logging_setup(in_file)
    instrument_setup(in_file)

    data_step = "n"
    data_str = ""

    if AMR_ser != "":
        a = AMR_Daemon()
        t1 = Thread(target=a.data_read)
        t1.setDaemon(True)
        t1.start()
        print("AMR is on")

    if LGR_ser != "":
        l = LGR_Daemon()
        t2 = Thread(target=l.data_read)
        t2.setDaemon(True)
        t2.start()
        print("LGR is on")

    w = write_to_remote_Daemon()
    t3 = Thread(target=w.write_to_remote)
    t3.setDaemon(True)
    t3.start()
    print("Remote writing is on")


if __name__ == "__main__":
    main()
