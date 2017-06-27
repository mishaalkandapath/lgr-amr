import time
import threading
import numpy as np
import datetime
import serial
import datetime as dt
import paramiko

np.set_printoptions(suppress=True)
year = now.year
month = now.month
day = now.day
# mode = input("Please specify "local" or "server" mode: ")
mode = "server"
if mode != "local":
    hostname = "haboob.atmosp.physics.utoronto.ca"
    port = 2222
    username = "gta-emissions"
    password = "m3thane"
    filePath = ("/home/atmosp.physics.utoronto.ca/public_html/" +
                "GTA-Emissions/FirstExample")
    fileName = "datasource.txt"

AMR_ser = serial.Serial("COM4", baudrate=4800)
LGR_ser = serial.Serial("COM5", baudrate=9600)
step = ""


def attach_date(utc_time, utc_offset):
    """"please note the time offset is by default edt"""
    now = datetime.date.today()
    if 24 - utc_offset <= int(utc_time[0:2]) <= 24:
        utc_date = str(now + dt.timedelta(days=1))[0:10]
    else:
        utc_date = str(now)[0:10]
    return utc_date + " " + utc_time


def check_dst():
    import calendar
    start_day = [week[-1]
                 for week in calendar.monthcalendar(dt.date.today().year, 3)
                 ][1]
    start_date = dt.date(year=dt.date.today().year, month=3, day=start_day)
    end_day = [week[-1]
               for week in calendar.monthcalendar(dt.date.today().year, 11)
               ][0]
    end_date = dt.date(year=dt.date.today().year, month=11, day=end_day)
    return (start_date, end_date)


class AMR_Daemon(object):
    def __init__(self):
        self.stuff = "hi there this is AMR_Daemon"

    def data_read(self):
        temp = []
        avg_list = []
        global row2
        accuracy = 1
        start, end = check_dst()
        while True:
            # try:
                x = str(AMR_ser.readline())[2:-1]
                temp.append(x)
                if len(temp) == 3:
                    gps = [lin for lin in temp if lin[0:6] == "$GPGGA"]
                    met = [lin for lin in temp if lin[0:6] == "$WIMDA"]
                    pre = [lin for lin in temp if lin[0:6] == "$YXXDR"]
                    if ((bool(gps)) and (bool(met)) and (bool(pre))):
                        """met data"""
                        """split on commas"""
                        met = [x.strip() for x in met[0].split(",")]

                        """d: pressure in bars, B, temp in celsius,
                           C, ,,,,,,true wind dir, T,
                           magnetic wind dir, M, true ws in knots, N,
                           true ws in ms , M
                        """
                        gps = [x.strip() for x in gps[0].split(",")]
                        pre = [x.strip() for x in pre[0].split(",")]
                        try:
                            lat = str(gps[2])
                            lat = float(lat[0:2]) + float(lat[2:])/60.
                        except ValueError:
                            print("Not connected to satalite")
                            continue
                        lon = str(gps[4])
                        lon = -float(lon[0:3]) - float(lon[3:])/60.
                        if start <= dt.today <= end:
                            utc_offset = -4
                        else:
                            utc_offset = -5
                        t = attach_date(gps[1], utc_offset)
                        vars_str = [t, str(lat), str(lon), met[5],
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
                        """insert utc time into list"""
                        row = tuple(var_num)
                        avg_list.append(row)

                        # print(row)
                        row = str(row)[1:-1]
                        """Append to average list and check when
                           it reaches desired length
                        """
                        global step
                        print(step)
                        if step == "y":
                            step = "n"
                            data_list = np.array(avg_list)[:, 1:]
                            ts = np.array(avg_list)[:, 0
                                                    ][int(len(avg_list)/2) - 1]
                            data_avg = np.average(data_list,  axis=0)
                            data_avg = np.insert(data_avg, 0, ts)
                            avg_list = []
                            row2 = ""
                            for var in data_avg:
                                row2 = row2 + str(var) + ","
                            row2 = row2[:-1]
                            print(row2)
                            write_to_server(row2, row3, mode)

                        # data_rec.write(row + "\n")
                        # data_rec.flush()
                    else:
                        print("sentences are missing")
                        temp = []
            # except KeyboardInterrupt:
                # raise
            # except:
                # print("Something went wrong")
                # continue


class LGR_Daemon(object):
    def __init__(self):
        self.stuff = "hi this is LGRDaemon"

    def data_read(self):
        while True:
            global step
            global row3
            x = str(LGR_ser.readline())[2:-1].split(",")[1:-7]
            step = "y"
            """time, methane, methane_se, h20, h20_se, gasp_torr, gasp_torr_se,
                gast, gast_se, ambt, ambt_se, RD0, RD_se, fit_flag
            """
            x = np.array([float(y) for y in x])
            """please insert instument check variables here"""
            err = instrument_chk()
            if err != "":
                break
            row3 = ""
            for var in x:
                row3 = row3 + str(var) + ","
            row3 = row3[:-1]
            print(row3)


def instrument_chk(rd1i, rd2i, pi):
    rd10 = 7.21
    rd20 = 7.65
    p0 = 140.5
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
    elif (abs(p0 - pi)) >= 20:
        err = (err + "Time- " + str(dt.datitme.now()) +
               "Pressure within the caivity is too high or low, please check" +
               "intake and waste tubes for bloackages and leaks"
               )
    if err != "":
        print(err)
        return err


def write_to_server(row2, row3, mode, local_log="./lgr_log"):
    data_str = row2 + "," + row3 + ";\n"
    if mode != "local":
        # Open a transport
        transport = paramiko.Transport((hostname, port))

        # Authentication
        transport.connect(username=username, password=password)

        # Create SFTPClient object called "sftp"
        sftp = paramiko.SFTPClient.from_transport(transport)

        # Change the current directory of this SFTP session.
        sftp.chdir(path=filePath)

        # Create a python file object from the datasource.txt file
        fileObject = sftp.file(fileName, mode="a", bufsize=-1)

        # Write to this file object
        fileObject.write(data_str)

        # Close the file
        fileObject.close()

        # Close the SFTP session and the transport
        sftp.close()
        transport.close()
    file = open(local_log, "a")
    file.write(data_str)
    print(data_str)

def main():
    a = AMR_Daemon()
    r = LGR_Daemon()
    t1 = threading.Thread(target=r.data_read)
    t2 = threading.Thread(target=a.data_read)
    t1.setDaemon(True)
    t2.setDaemon(True)
    t1.start()
    t2.start()

if __name__ == "__main__":
    main()