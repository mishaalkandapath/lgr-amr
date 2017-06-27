import threading
import numpy as np
import serial
import datetime as dt
import pytz
import paramiko
import getpass
np.set_printoptions(suppress=True)



def attach_date(sat_time):
    """" this function attaches a date to utc times from the gps
         and returns YYYY-MM-DD HHMMSS.ffff
    """
    date_str = dt.datetime.now(utc).date().isoformat()
    return date_str + " " + sat_time


class AMR_Daemon(object):
    """this object holds the AMR function"""
    def __init__(self):
        self.stuff = "Hi, this is AMR_Daemon"

    def data_read(self):
        """define empty lists, accuarccy and open local log file and write
           header
        """
        temp = []
        AMR_avg_list = []
        global AMR_data  # data from AMR written to AMR_data
        global AMR_t
        accuracy = 1  # instrument accuarcy

        AMR_local_log_file = open(AMR_local_log, mode="a")
        AMR_local_log_file.write("time, lat, lon, temp, wd, ws, pressure," +
                                 " hdop")
        AMR_local_log_file.flush()
        """if the LGR is disconected we write only AMR data
           and we need the user to specify an averaging time for the AMR
        """
        if LGR_ser == np.nan:
            avg_time = input("Please enter an averaging time in seconds for" +
                             " the AMR measurements"
                             )
            LGR_data = ""

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
                    except ValueError:
                        print("Not connected to satalite")
                        continue
                    lon = str(gps[4])
                    lon = -float(lon[0:3]) - float(lon[3:])/60.
                    AMR_t = attach_date(gps[1])
                    vars_str = [AMR_t, str(lat), str(lon), met[5],
                                met[13], met[-2],
                                str(float(pre[-3])*1000.),
                                str(float(gps[8]*accuracy))
                                ]
                    temp = []
                    var_num = []
                    for var in vars_str:
                        try:
                            var = float(var)
                        except ValueError:
                            var = np.nan
                        var_num.append(var)
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
                    if LGR_ser != np.nan:
                        global LGR_step
                        local_step = LGR_step
                        print(LGR_step)
                    else:

                        if len(AMR_avg_list) == avg_time:
                            local_step = "y"
                    """once trigger occurrs we average the AMR data and use
                       the write server function to send data to server
                    """
                    if local_step == "y":
                        LGR_step = "n"
                        data_list = np.array(AMR_avg_list)[:, 1:]
                        ts = np.array(AMR_avg_list)[:, 0
                                                    ][len(AMR_avg_list)/2 - 1]
                        data_avg = np.average(data_list,  axis=0)
                        data_avg = np.insert(data_avg, 0, ts)
                        AMR_avg_list = []
                        AMR_data = ""
                        for var in data_avg:
                            AMR_data = AMR_data + str(var) + ","
                        AMR_data = AMR_data[:-1] + "," + len(AMR_avg_list)
                        print(AMR_data)
                        write_to_server(AMR_data, LGR_data, mode)
                else:
                    print("Sentences are missing")
                    temp = []
                    continue


class LGR_Daemon(object):
    def __init__(self):
        self.stuff = "hi this is LGRDaemon"

    def data_read(self):
        LGR_local_log_file = open(LGR_local_log, mode="a")
        LGR_local_log_file.write()
        LGR_avg_list = []
        global LGR_step
        global LGR_data

        # put a header here and decide how to handle
        # times when AMR not present or satalite time string is absent,
        # think we should
        # just use LGR data's time need to double check when exactly
        while True:
            LGR_str = str(LGR_ser.readline())[2:-1].split(",")[0:-7]
            comp_time = dt.datetime.now(utc).isoformat()
            x = LGR_str[1:-7]
            x = np.array([float(y) for y in x])
            err = instrument_chk(x[21], x[23],  x[15])
            if err != "":
                break
            LGR_data = ""
            for var in x:
                LGR_data = LGR_data + str(var) + ","
            LGR_data = LGR_data[:-1]
            """local log write with instrument time and comp time
               at measurement
            """
            LGR_t = LGR_str[0]
            LGR_data = LGR_data.insert(0, LGR_t)
            LGR_data = LGR_data.insert(1, comp_time)
            LGR_local_log_file.write(LGR_data + "\r\n")
            LGR_local_log_file.flush()
            print(LGR_data)
            if AMR_ser == np.nan:
                continue  # stop iteration here if no AMR and just write local
            LGR_avg_list.appeend(x)
            if len(LGR_avg_list) == LGR_avg_time:
                LGR_step = "y"
                data_list = np.array(LGR_avg_list)[:, 1:]
                ts = np.array(LGR_avg_list)[:, 0
                                            ][int(len(LGR_avg_list)/2) - 1]
                data_avg = np.average(data_list, axis=0)
                data_avg = np.insert(data_avg, 0, ts)
                LGR_avg_list = []
                LGR_data = ""
                for var in data_avg:
                    LGR_data = LGR_data + str(var) + ","
                LGR_data = LGR_data[:-1] + "," + len(LGR_avg_list)
                print(LGR_data)


def instrument_chk(rd1i, rd2i, presi):
    rd10 = 7.21
    rd20 = 7.65
    pres0 = 140.5
    err = ""
    if (abs(rd1i - rd10)/rd10) >= 0.20:
        err = (err + "Time- " + str(dt.datitme.now()) +
               "Laser 1 ringdown time is too low." +
               "Please clean mirrors soon\r\n"
               )
    elif (abs(rd2i - rd20)/rd20) >= 0.20:
        err = (err + "Time- " + str(dt.datitme.now()) +
               "Laser 1 ringdown time is too low." +
               "Please clean mirrors soon\r\n"
               )
    elif (abs(pres0 - presi)) >= 20:
        err = (err + "Time- " + str(dt.datitme.now()) +
               "Pressure within the caivity is too high or low, please check" +
               "intake and waste tubes for bloackages and leaks"
               )
    if err != "":
        print(err)
        return err


def write_to_server():
    data_str = AMR_data + "," + LGR_data + ";\n"
    if mode != "local":
        """code to open ssh port to server with user provided input"""
        transport = paramiko.Transport(hostname, port)
        transport.connect(username=username, password=password)
        sftp = paramiko.SFTPClient.from_transport(transport)
        sftp.chdir(path=filePath)
        fileObject = sftp.file(fileName, mode="a", bufsize=-1)
        fileObject.write(data_str)
        fileObject.close()
        sftp.close()
        transport.close()
    else:
        return
    print(data_str)

"""maybe setup an infile for these parameters?"""


def logging_setup():
    global hostname, port, username, password, filePath, fileName
    global LGR_local_log, mode, AMR_local_log
    mode = input("Are we writing locally or remotely? ")
    if mode != "locally":
        yn = input("Use default remote server and local settings " +
                   "(write to gta-emissions@haboob and ./LGR_log)? (y/n) ")
        if yn is "y":
            hostname = "haboob.atmosp.physics.utoronto.ca"
            port = 2222
            username = "gta-emissions"
            password = "m3thane"
            filePath = ("/home/atmosp.physics.utoronto.ca/public_html/" +
                        "GTA-Emissions/FirstExample")
            fileName = "datasource.txt"
            LGR_local_log = "./LGR_log"
        else:
            hostname = input("hostname- ")
            port = input("port- ")
            username = input("username- ")
            password = getpass.getpass("password- ")
            filePath = input("remote file location- ")
            fileName = input("remote file name- ")
            LGR_local_log = input("local LGR log file- ")
    else:
        yn = input("Writing only to local machine. Use default log files" +
                   " (./LGR_log and ./AMR_log)? (y/n) "
                   )
        if yn == "y":
            LGR_local_log = "./LGR_log" + dt.datetime.now(utc).date.isoformat()
            AMR_local_log = "./AMR_log" + dt.datetime.now(utc).date.isoformat()

        else:
            LGR_local_log = input("LGR local log file- ")
            AMR_local_log = input("AMR local log file- ")


def instrument_setup():
    global AMR_ser, LGR_ser, LGR_avg_time
    """get location of instruments"""
    while True:
        AMR_loc = input("Please enter the AMR's COM port. If not using AMR" +
                        " press Enter"
                        )
        if AMR_loc != "":
            print("Trying to connect to AMR at " + AMR_loc)
            try:
                AMR_ser = serial.Serial(AMR_loc, baudrate=4800)
                print("AMR found at " + AMR_loc)
                break
            except:
                print("AMR not found at " + AMR_loc)
                continue
        else:
            print("Not using AMR")
            AMR_ser = np.nan
            break
    while True:
        LGR_loc = input("Please enter the LGR's COM port. If not using LGR" +
                        " press Enter "
                        )
        if LGR_loc != "":
            print("Trying to connect to LGR at " + LGR_loc)
            try:
                LGR_ser = serial.Serial(LGR_loc, baudrate=9600)
                print("LGR found at " + LGR_loc)
                LGR_avg_time = int(input("Please enter an averaging time " +
                                         "for the LGR data in seconds "))

            except:
                print("LGR not found at " + LGR_loc)
                LGR_ser = np.nan
        else:
            print("Not using LGR")
            LGR_ser = np.nan
            break


def main():
    logging_setup()
    instrument_setup()
    l = LGR_Daemon()
    a = AMR_Daemon()
    t1 = threading.Thread(target=l.data_read)
    t2 = threading.Thread(target=a.data_read)
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()


if __name__ == "__main__":
    utc = pytz.timezone("UTC")
    main()
