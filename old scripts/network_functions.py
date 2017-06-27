# -*- coding: utf-8 -*-
"""
Created on Wed Jun 21 19:25:34 2017

@author: wunch_group
"""
import paramiko
import datetime as dt
import socket
from time import sleep
"""
data header
 time,lat,lon,alt,temp,wd,ws,pressure,hdop,lgr_time, ch4d, co2d,
 cod, water, average, computer time
;
"""


def is_connected():
    try:
        socket.gethostbyname('www.google.com')
        network_status = "online"
    except socket.gaierror:
        network_status = "offline"
    finally:
        print(network_status)
        return network_status


class write_to_remote_Daemon(object):

    def __init__(self):
        self.stuff = "Hi, this is Remote Daemon"

    def prep_data_string(self):
        global AMR_data, LGR_data, avg_time, data_str
        global local_web_copy

        data_str = (data_str +
                    (AMR_data + "," + LGR_data + "," + str(avg_time) + "," +
                     str(dt.datetime.now()) + ";\n"
                     )
                    )
        local_web_copy.write(data_str)
        local_web_copy.flush()

    def write_to_remote(self):
        global AMR_data, LGR_data, avg_time, data_str
        global transport, sftp, file_object, file_name, ssh
        global network_status, remote_wrtie_step
        while True:
            sleep(30)
            is_connected()
            if network_status == "online":
                try:
                    file_object.write(data_str)
                    print(data_str)
                    data_str = ""
                except KeyboardInterrupt:
                    raise
                except:
                    network_status = "offline"
                    return
            if network_status == "offline":
                try:
                    open_remote()
                    print(network_status)
                    return
                except KeyboardInterrupt:
                    raise
                except:
                    network_status = "offline"
                    print(network_status)
                    return


def open_remote():
    global sftp, file_object, network_status, local_web_copy
    global hostname, port, username, password, file_path, file_name
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(hostname, username=username, password=password, port=port
                    )
        sftp = ssh.open_sftp()
        sftp.chdir(path=file_path)
        file_object = sftp.file(file_name, mode="a", bufsize=-1)
        network_status = "online"
        print("Connected to " + hostname)
        local_web_copy = open("./local_log/web_data/" + file_name, mode="a")
    except KeyboardInterrupt:
        raise
    except:
        raise
        print("Could not connect to " + hostname + " cacheing data")
        network_status = "offline"

if __name__ == "__main__":
    AMR_data, LGR_data, avg_time, data_str = ("a", "l", "at", "")
    hostname = "haboob.atmosp.physics.utoronto.ca"
    port = 2222
    username = "gta-emissions"
    password = "m3thane"
    file_path = ("/home/atmosp.physics.utoronto.ca/public_html/" +
                 "GTA-Emissions/FirstExample"
                 )
    file_name = "test.txt"
