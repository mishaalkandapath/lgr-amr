#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 18:55:48 2017

@author: sajjan, colin
"""
import os
import datetime as dt
import numpy as np
import socket
from threading import Thread
from getpass import getpass
from serial import Serial
from pytz import timezone
from paramiko import SSHClient, AutoAddPolicy
from time import sleep
import subprocess
"""import necessary modules"""

#import slack api mods:
import logging
logging.basicConfig(level=logging.DEBUG)

import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

"""set numpy print options so flaots printed in regular notation not scientific
"""
np.set_printoptions(suppress=True)
"""create a pytz timezone for adjusting datetimes"""
utc = timezone("UTC")

"""Get a slack token from the environment variable"""
slack_token = os.environ["SLACK_BOT_TOKEN"]

"""
Section 1- Setup of Instrument and logging using in_file
"""


def logging_setup(in_file):
    """define global varibles for logging setup from lgr_amr.infile"""
    global hostname, port, username, password, file_path, remote_plot_file
    """varibles for opening ssh port with remote machine"""
    global remote_write_period, mode
    """how often attempt to write to server, important as we don't want to
       ping server too freqeuntly and if we're writing locally or remotely
    """
    global LGR_local_log, AMR_local_log, local_plot_file
    global local_cache_file, err_log
    """define local log files
       also define the local copy of the remote plotting file and the cache
       file for stroing data before writing
    """
    """ log problems with LGR"""
    err_log = open("./errors/error_log", mode="a")
    """ name of plotting file on server"""
    remote_plot_file = in_file[5]
    """open file for appending and reading local copy of web data"""
    local_plot_file = open(("./local_log/web_data/" + remote_plot_file + "_" +
                            dt.date.today().isoformat()
                            ), mode="a+"
                           )
    """remote+ local or local only write mode"""
    mode = in_file[0]
    """minimamlly processed data files for each instrument"""
    LGR_local_log = in_file[6] + "_" + dt.date.today().isoformat()
    AMR_local_log = in_file[7] + "_" + dt.date.today().isoformat()
    if mode == "remotely":
        """in remote mode, we define server varibles and open an ssh port
            using the varibales defined in infile. we also open a cacheing
            file that stores data before it's written to server
        """
        local_cache_file = open(("./local-cache"
                                 ), mode="a+"
                                )
        hostname = in_file[1]
        port = int(in_file[2])
        username = in_file[3]
        password = getpass(prompt="Please type password to remote machine " +
                           "for user " + username + "@" + hostname
                           )
        file_path = in_file[4]
        open_remote()
    """in local mode we only write to the local log files, defined above
       if statement
    """
    return


def instrument_setup(in_file):
    """function defines instrument settings based on infile"""
    """define global serial connections and averaging period"""
    global AMR_ser, LGR_ser, avg_time
    avg_time = int(in_file[10])
    """try to connect to AMR if set as being used in infile and
       handle errors in connceting. If not using or can't find switch to an LGR
       only mode
    """
    AMR_loc = in_file[8]
    """if AMR loc defined in settings try to connect to it and handle error if
       not connected
    """
    if AMR_loc != "":
        print("Trying to connect to AMR at " + AMR_loc)
        try:
            AMR_ser = Serial(AMR_loc, baudrate=4800, timeout=1)
            print("AMR found at " + AMR_loc)
        except KeyboardInterrupt:
            raise
        except:
            """switch to LGR only """
            print("AMR not found at " + AMR_loc)
            print("Not using AMR")
            AMR_ser = ""
    else:
        """switch to LGR only """
        print("Not using AMR")
        AMR_ser = ""

    """same for LGR as with AMR"""
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
in mapping files see readmes
"""


def is_connected():
    """this fucntion is can check connection quickly before
       writing to remote as time for the script to realise the channel dead
       is approximately 30 seconds. Not currently used but may be easily
       integrated into code by adding to top of remote write daemon
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
       copy of the mapping data and to the cache
    """
    global AMR_data, LGR_data, avg_time, data_str
    global local_plot_file, local_cache_file

    data_str = ((AMR_data + "," + LGR_data + "," + str(avg_time) + "," +
                 str(dt.datetime.now()) + ";\n"
                 )
                )
    """print data string so user can know if code is working"""
    print(data_str)

    """ check for nans to see if lgr and amr are working, if not write to slack"""
    if "nan" in AMR_data and "nan" in LGR_data:
        # subprocess.run("sendmessage.sh 1 " + slack_token)
        send_slack_message("LGR & AMR disconnected")
    elif "nan" in AMR_data:
        # subprocess.run("sendmessage.sh 2 " + slack_token)
        send_slack_message("AMR disconnected")
    elif "nan" in LGR_data:
        # subprocess.run("sendmessage.sh 3 " + slack_token)
        send_slack_message("LGR disconnected")

    """this blocks handles trying to write to the datafile if it's closed.
       We just reopen the file for appending if it's closed
       this can happen sometimes due to remote daemon clearing file and closing
       it
    """
    try:
        local_cache_file.write(data_str)
        local_cache_file.flush()
    except AttributeError:
        local_cache_file = open("./local-cache", mode="a+")
        local_cache_file.write(data_str)
        local_cache_file.flush()
    """write to local plotting file"""
    local_plot_file.write(data_str)
    local_plot_file.flush()


def open_remote():
    """function returns a secrue file transfer prtocool channel as a globa
       variable using
       the variables from logging setup. this sftp
       is used to write to the remote machine
    """
    global sftp, file_object, network_status
    global hostname, port, username, password, file_path, remote_plot_file
    """try except clasuse attempts to write to open port and handles what
       happens if we're offline
    """
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
        """set network status switch to online, needed to tell code if to
           try to write or try to reconnect
        """
        network_status = "online"
        print("Connected to " + hostname)
    except KeyboardInterrupt:
        raise
    except:
        """bare except is bad we should have here except gaierror. Need
        to add from import gaierror to top and change statement. No time to
        test change yet
        """
        print("Could not connect to " + hostname + " cacheing data")
        """set network status switch to offline, needed to tell code if to
           try to write or try to reconnect
        """
        network_status = "offline"
    return


class write_to_remote_Daemon(object):
    """this class defines a remote writing thread that attempts to write to
       the remote machine every remote write period and if this fails, it
       attempts to reconnect. it also sets the global network status after
       every write attempt
    """
    def __init__(self):
        """intialises the daemon and sets the line we read from in the loca
           copy of the remote machine data to 0
        """
        """"these lines definetly aren't needed(from old version of code)
            but would want to test if remove
            is okay
        """
        global local_file_step
        local_file_step = 0
        self.stuff = "Hi, this is Remote Daemon"

    def write_to_remote(self):
        """define function that sends data in cache through sftp port in
           open_remote().
        """
        global sftp, file_object
        global network_status
        global local_file_step, remote_data_str, local_cache_file

        no_fails = 5 # number of times we try to write before we ping the slack

        while True:
                sleep(int(in_file[11]))
                """sleep so we aren't pinging remote machine too freqeunctly"""
                """based on network ssatus we either try to write to remote or
                   we try to reconnect
                """
                if network_status == "online":
                    try:
                        """move to read line 0 in cache"""
                        local_cache_file.seek(0)
                        """loop over lines and write each via sftp port"""
                        for i, l in enumerate(local_cache_file):
                            #  if i >= local_file_step:
                                """quality check line """
                                if len(l.split(",")) != 16:
                                    continue
                                else:
                                    file_object.write(l)
                                    """print so user knows if port is
                                       working
                                    """
                                    print("Successfully wrote new lines to " +
                                          "remote " +
                                          "machine")
#                                local_file_step = local_file_step + 1
#                            else:
#                                continue
                        """clear local cache after we write all lines from
                           it
                        """
                        local_cache_file = open("./local-cache",
                                                mode="w"
                                                ).close()
                        """reopen file for more data"""
                        local_cache_file = open("./local-cache", mode="a+")
                    except KeyboardInterrupt:
                        raise
                    except:
                        """this except should really be except giaerror: so
                           only netowrk errors caught
                        """
                        network_status = "offline"
                        """if sftp fails print something so user can see"""
                        print("Failure")
                        continue
                elif network_status == "offline":
                    """if network switch is offline then try to reconnect using
                       open remote function
                    """
                    try:
                        open_remote()
                        print(network_status)
                    except KeyboardInterrupt:
                        raise
                    except:
                        network_status = "offline"
                        no_fails -= 1
                        print(network_status)
                        continue


"""
Section 3- Define Instrument Reading and Processing Daeemons
"""


def attach_date(satalite_time):
    """" this function attaches a date to utc times from the gps
         and returns YYYY-MM-DD HHMMSS.ffff This should ideally use the date
         provided by the gps in other sentence but this would requier more
         data being sent through amr com port
    """
    date_str = dt.datetime.now(utc).date().isoformat()
    return (date_str + " " + str(satalite_time)).strip("'")


def find_average_time(time_array, format_str):
    """find the time at the middle of a list of times to get time at middle of
       averaging period function can accept a
       format string defiinng time foramt
    """
    time_list = [dt.datetime.strptime(x, format_str
                                      )
                 for x in time_array
                 ]
    t0 = time_list[0]
    tf = time_list[-1]
    time_delta = tf - t0
    t_middle = t0 + time_delta/2.
    return t_middle


def wind_average(wind_array):
    """this function splits an array of measured wind vectors into components
       and outputs their average. The intial wind vectors are relative to
       north as is the functions output. Need this to properly average amr
       winds
    """
    """ variables"""
    thetas = np.radians(wind_array[:, 0])
    vs = wind_array[:, 1]
    """split into components"""
    vxs = vs * np.sin(thetas)
    vys = vs * np.cos(thetas)
    """average componets"""
    vxs_avg = np.average(vxs)
    vys_avg = np.average(vys)
    """recombine into a theta, second line takes care of negative angles and
       angels greater than 360 and rotates into angel from North
    """
    thetas_avg = np.degrees(np.arctan2(vys_avg, vxs_avg))
    thetas_avg = (450 - thetas_avg) % 360
    """get average speed"""
    vs_avg = np.average(vs)
    """return tuple of data"""
    return (thetas_avg, vs_avg)


class AMR_Daemon(object):
    """this object holds the AMR logging function"""
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

        accuracy = 1  # instrument accuarcy would need to measure this
        temp = []
        AMR_avg_list = []
        """try except loop to write header only at top of file. checks if file
           exists and if not opens and writes a header"""
        try:
            AMR_local_log_file = open(AMR_local_log, mode="r")
            AMR_local_log_file.close()
            AMR_local_log_file = open(AMR_local_log, mode="a")
        except FileNotFoundError:
            AMR_local_log_file = open(AMR_local_log, mode="a")
            AMR_local_log_file.write("gps_time,lat,lon,alt,temp,wd_corr," +
                                     "ws_corr,pressure," +
                                     "hdop,wd_uncorr,ws_uncorr,heading," +
                                     "cog,sog, computer_utc_time\r\n"
                                     )
        AMR_local_log_file.flush()
        """if the lgr isn't connected, we set its data as a list of nans for
           remote write and
            set amr averaging step to 0
        """
        if LGR_ser == "":
            LGR_data = str([np.nan]*5)[1:-1]
            local_step = "n"
        """this while True is bad as it means there's no eay to cleanly end
           logging thread. better would be something like
           def stop():
               global stop_event
               stop_event = threading.Event()
               return
           while not stop_event:
            then logger thread stopped with typing stop()
        """
        while True:
            """read line from com port and remove b''"""
            try: #fails when port is removed sometimes
                amr_str = str(AMR_ser.readline())[2:-5]
            except:
                send_slack_message("AMR disconnected")
                continue
            """append data to the temp list"""
            temp.append(amr_str)
            """this if else block waits for temp to have right number of
               elements to possibley have all the AMR data
            """
            if len(temp) == 6:
                """once right number elements in temp, we split the
                   data in temp by  type
                   data from each sensor, pressure, gps and meterological,
                   velocity, uncorrected wind and heading
                """
                gps = [lin for lin in temp if lin[0:6] == "$GPGGA"]
                met = [lin for lin in temp if lin[0:6] == "$WIMDA"]
                pre = [lin for lin in temp if lin[0:6] == "$YXXDR"]
                win = [lin for lin in temp if lin[0:6] == "$WIMWV"]
                vtg = [lin for lin in temp if lin[0:6] == "$GPVTG"]
                hdg = [lin for lin in temp if lin[0:6] == "$HCHDT"]
                if (bool(gps) and bool(met) and bool(pre) and bool(win) and
                   bool(vtg) and bool(hdg)):
                    """if we have one of each of the amr strings in the
                       temp
                       we proecess them, else they are thrown out. This is bad
                       since it would be better to keep strings if only a few
                       are out. But it doesn't seem like we lose much if any
                       at all data
                       with this
                    """
                    """print output so user knows we got amr data"""
                    print("AMR data recieved")
                    """get comptuer time at which all data recived, this may be
                       a little off as we take it at the end of reciveving all
                       the data not at the middle
                    """
                    comp_time = str(dt.datetime.now(utc))
                    """split sentces by commas for format of data strings
                       see amr technical manual
                       ran out of time/patience to list all
                    """
                    met = [x.strip() for x in met[0].split(",")]
                    gps = [x.strip() for x in gps[0].split(",")]
                    pre = [x.strip() for x in pre[0].split(",")]
                    win = [x.strip() for x in win[0].split(",")]
                    vtg = [x.strip() for x in vtg[0].split(",")]
                    hdg = [x.strip() for x in hdg[0].split(",")]
                    """try except clause to handle lost satelite conncetion"""
                    try:
                        """try to define variables from gps needed here so
                           we can covnert lat and lon to decimal degrees
                        """
                        lat = str(gps[2])
                        lat = float(lat[0:2]) + float(lat[2:])/60.
                        lon = str(gps[4])
                        lon = -float(lon[0:3]) - float(lon[3:])/60.
                        alt = float(gps[9])
                        hdop = float(gps[8])
                        """create amr datetime"""
                        AMR_t = attach_date(gps[1])
                    except ValueError:
                        lat, lon, alt, AMR_t, hdop = (np.nan, np.nan,
                                                      np.nan, np.nan,
                                                      np.nan
                                                      )
                    try:
                        """convert pressure to hPa for further plotting and
                           handle error if its missing
                        """
                        pres = float(pre[-3])*1000.
                    except ValueError:
                        pres = np.nan
                    vars_str = [AMR_t, str(lat), str(lon), str(alt),
                                met[5],
                                met[13], met[-2],
                                str(pres),
                                str(hdop*accuracy), win[1], win[3], hdg[1],
                                vtg[1], vtg[7]
                                ]
                    """time, lat, lon, alt, temp, wd_corr, ws_corr, press,
                        accuraccy, wd_uncorr, ws_uncorr, true heading, ground
                        speed ground direction
                    """
                    """here we cleared temp list and defined the list that
                       will
                       hold the data in numeric format needed for averaging
                    """
                    temp = []
                    var_num = []
                    """loop over var_str and convert to floats"""
                    for var in vars_str:
                        try:
                            var = float(var)
                        except ValueError:
                            """fill missing data with nans"""
                            var = np.nan
                        var_num.append(var)
                    """put time back into data"""
                    var_num[0] = AMR_t
                    AMR_raw_data = var_num
                    AMR_raw_data = tuple(var_num)

                    AMR_avg_list.append(AMR_raw_data[0:-5])
                    """append the data tuple to an averaging list
                       and remove several varibles not needed for web plotting
                    """
                    AMR_raw_data = str(AMR_raw_data)[1:-1]
                    """write full data string to local logging file"""
                    AMR_local_log_file.write(AMR_raw_data + "," +
                                             comp_time.strip("'") + "\r\n"
                                             )
                    AMR_local_log_file.flush()
                    """determine when averaging of back data occurrs,
                       either
                       triggered by LGR or by length of AMR list
                       depending
                       on which instruments are connected
                    """
                    """if lgr connected it ddetermines averaging write its
                       data step to local step
                    """
                    if LGR_ser != "":
                        global data_step
                        local_step = data_step
                    else:
                        """else set local step
                           when avg_time numeber of elements in amr
                           list. asssumes this means we have avg_time
                           seconds of
                           data
                        """
                        if len(AMR_avg_list) == avg_time:
                            local_step = "y"
                        else:
                            local_step = "n"
                    """once local step trigger occurrs we average the AMR
                       data
                       and use prep data string to prepare a string for writing
                       to server
                    """
                    if local_step == "y":
                        """reset averaging triggers"""
                        data_step = "n"
                        local_step = "n"
                        """take out non datetime data for averaging and change
                            back to floats (creating an array with non-numeric
                            makes all data strings
                        """
                        data_list = np.array(AMR_avg_list)[:, 1:
                                                           ].astype("f8")
                        """take out winds for their averaging (arthimatic
                           average won't
                           work on winds)
                        """
                        winds = data_list[:, 4:6]
                        try:
                            wind_avg = wind_average(winds)
                        except KeyboardInterrupt:
                            raise
                        except:
                            """except alone is bad and should handle errors in
                               the wind average function
                            """
                            wind_avg = (np.nan, np.nan)
                        """average other data normally"""
                        data_avg = np.average(data_list, axis=0)
                        """repalce wind data with properply averaged ones"""
                        data_avg[4] = wind_avg[0]
                        data_avg[5] = wind_avg[1]
                        """remove lat and lon so not rounded down. important
                           for accurtae postions on map
                        """
                        lat, lon = data_avg[0], data_avg[1]
                        data_avg = np.round(data_avg, 3)
                        """average data in avg list and round all values"""
                        data_avg[0] = lat
                        data_avg[1] = lon
                        """replace lat and lon fields with unrounded values
                           for plotting
                        """
                        """convert data back into strings so we could add time
                           back in and write to txt files
                        """
                        data_avg = data_avg.astype("str")
                        """select times from original aveage list"""
                        time_array = np.array(AMR_avg_list)[:, 0]
                        """find middle time. as with winds error handling
                           should ideally occurr in function and be specific
                        """
                        try:
                            t_middle = find_average_time(time_array,
                                                         "%Y-%m-%d" +
                                                         " %H%M%S.%f"
                                                         )
                        except KeyboardInterrupt:
                            raise
                        except:
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
                           file and cache
                        """
                        """reset averaging list"""
                        AMR_avg_list = []
                else:
                    """if any amr expectd data is missing from amr print
                       something and reset temp list for next set of data
                    """
                    print("Sentences are missing")
                    temp = []


class LGR_Daemon(object):
    def __init__(self):
        self.stuff = "Hi this is LGRDaemon"

    def data_read(self):
        """explictly get the gloabl varibales we need, local logs, amr serial
           port, lgr serial port and averaging time
        """
        global LGR_local_log, mode, AMR_local_log
        global AMR_ser, LGR_ser, avg_time, err_log
        """write header if needed"""
        try:
            LGR_local_log_file = open(LGR_local_log, mode="r")
            LGR_local_log_file.close()
            LGR_local_log_file = open(LGR_local_log, mode="a")
        except FileNotFoundError:
            LGR_local_log_file = open(LGR_local_log, mode="a")
            LGR_local_log_file.write("lgr_time,ch4,ch4se,h2o," +
                                     "h2ose,co2,co2se,co,cose,ch4d," +
                                     "ch4dse,co2d,co2dse,cod,codse,gasp," +
                                     "gaspse,t,tse,amb,ambse,rd1,rd1se," +
                                     "rd2,rd2se,computer_utc_time" + "\r\n"
                                     )
        """define daa step varible used to trigger averaging in this and the
           amr deamon
        """
        global data_step
        global LGR_data, LGR_avg_list, AMR_data
        LGR_avg_list = []
        LGR_local_step = "n"
        """if amr serila closed then define its data as nans to be written to
           server
        """
        if AMR_ser == "":
            AMR_datat = [np.nan]*9
            AMR_data = ""
            for a in AMR_datat:
                AMR_data = AMR_data + str(a) + ","
            AMR_data = AMR_data[:-1]
        """same problem as amr while loop, this way doesn't allow clean exit of
           code. Not really a problem but nice to be able to close threads in
           console
        """
        while True:
            """read lgr string from serial port and split into a list"""
            LGR_str = str(LGR_ser.readline())[2:-1].split(",")[0:-7]
            lgr_str = LGR_str[1:]
            """get computer timestamp for when string recived"""
            comp_time = str(dt.datetime.now(utc))
            lgr_lst = []
            """above block converts string to floats and handles
               missing data fields. Except statement
               should be excpet ValueError: to handle missing data not except
               alone
            """
            for y in lgr_str:
                try:
                    lgr_lst.append(float(y))
                except KeyboardInterrupt:
                    raise
                except:
                    lgr_lst.append(np.nan)
            """do a check of laser ringdown times and cavity pressure,
               important for qualit control of LGR data and for knowing when
               we need to clean it. Also doubles as a check for bad strings in
               LGR output
            """
            try:
                err = instrument_chk(lgr_lst[20], lgr_lst[22], lgr_lst[14])
            except IndexError:
                print("Missing Data String from LGR")
                send_slack_message("LGR Disconnected")
                continue
            """if we have an error write it to a log"""
            if err != "":
                err_log.write(err)
                err_log.flush()
            """local log write with instrument time and comp time
               at measurement
            """
            """create lgr data string"""
            LGR_t = LGR_str[0][2:]
            """insett back lgr time which is now a nan due to flaot conversion
            """
            lgr_lst.insert(0, LGR_t)
            LGR_raw_data = ""
            for var in lgr_lst:
                LGR_raw_data = LGR_raw_data + str(var) + ","
            """not sure why I do this line...think there are useless varaibles
               at end of string
            """
            LGR_raw_data = LGR_raw_data[1:-2]
            LGR_local_log_file.write(LGR_raw_data + "," +
                                     comp_time.strip(",") + "\r\n"
                                     )
            LGR_local_log_file.flush()
            "above writes data to local log file for LGR"""

            """output so user knows data recived from LGR"""
            print("LGR data recieved")
            LGR_avg_list.append(lgr_lst)
            """once average list include right number of measuremnts
               we set LGR step to y
            """
            if len(LGR_avg_list) == avg_time:
                LGR_local_step = "y"
            if LGR_local_step == "y":
                data_step = "y"
                """above sets global data step to y and triggers amr daemon
                   averaging if both instruments are working
                """
                try:
                    """try to average data in lgr string very similar to amr
                       averaging and creates a array of useful varibles
                       that is sent to prep data string
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
                except IndexError:
                    """this handles a weird error where the lgr sometimes
                       outputs which causes an index error. This bug is
                       very uncommon so we haven't seen what the bad string
                       looks like but we know an index error is triggerd in
                       above block during the bug so we catch it here and
                       define the lgr data as nan's
                    """
                    data_avg = np.array([np.nan]*5)
                """create lgr data string"""
                LGR_data = ""
                for var in data_avg:
                    LGR_data = LGR_data + str(var) + ","
                LGR_data = LGR_data[:-1]
                LGR_avg_list = []
                """if lgr not being used do prep data here, if it is prep data
                   occurrs in amr daemon
                """
                if AMR_ser == "":
                    prep_data_string()
                LGR_local_step = "n"
                """reset LGR averaging stepp"""


def instrument_chk(rd1i, rd2i, presi):
    """this function checks that the LGR is functioning properply"""
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

#slack function stuff:
def send_slack_message(text):
    client = WebClient(token="")
    try:
        response = client.chat_postMessage(
            channel="D03EGDT9WAF",
            text=text
        )
        print("Sent slack message: ", response)
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["error"]    # str like 'invalid_auth', 'channel_not_found'

"""
Main Function Call, starts all daemons and does setup
"""


def main():
    global data_step, data_str
    global AMR_ser, LGR_ser, in_file
    """red infile"""
    in_file = [x.rstrip() for x in
               open("./lgr_amr.infile", mode="r").readlines() if x[0] != "#"
               ]
    """do logging set up"""
    logging_setup(in_file)
    """do instrument setup"""
    instrument_setup(in_file)
    """set intial data step and data string"""
    data_step = "n"
    data_str = ""
    """if using amr start amr daemon"""
    if AMR_ser != "":
        a = AMR_Daemon()
        t1 = Thread(target=a.data_read)
        t1.setDaemon(True)
        t1.start()
        print("AMR is connected")
    """if using lgr start lgr daemon"""
    if LGR_ser != "":
        l = LGR_Daemon()
        t2 = Thread(target=l.data_read)
        t2.setDaemon(True)
        t2.start()
        print("LGR is connected")
    """if using remote writing start lgr daemon"""
    if mode == "remotely":
        w = write_to_remote_Daemon()
        t3 = Thread(target=w.write_to_remote)
        t3.setDaemon(True)
        t3.start()
        print("Remote writing is on")

"""start function if this script is called"""
if __name__ == "__main__":
    main()
