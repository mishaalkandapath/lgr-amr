# -*- coding: utf-8 -*-
"""
Created on Fri May  5 11:00:45 2017

@author: Colin
"""
import time
import numpy as np
import datetime
import serial

import paramiko

np.set_printoptions(suppress=True)
now = datetime.datetime.now()
year = now.year
month = now.month
day = now.day

#specify if we're writing to atmosp or local host
mode = input("Please specify 'local' or 'server' mode: ")
if mode != "local":
    hostname = "haboob.atmosp.physics.utoronto.ca"
    port = 2222
    username = "gta-emissions"
    password = "m3thane"
    filePath = '/home/atmosp.physics.utoronto.ca/public_html/GTA-Emissions/FirstExample'
    fileName = 'datasource.txt'
    

for i in np.arange(1,6):
     print("Checking COM Port " + str(i))
     try:
         ser = serial.Serial("COM"+str(i), baudrate=4800)
         print("Airmar connected to COM Port" + str(i))
         break
     except:
         continue
data_rec = open('C:\wamp64\www\FirstExample\Data_Record_' +
                               str(year) + str(month) + str(day)  +
                                ".txt", 'w'
                                )


response = str(input("Please Enter Transport Type.\n" +
                "Options:\n" +
                "'Walking'\n" +
                "'Cycling'\n" +
                "'Driving'\n" +
                "'Streetcar'\n" +
                "Type Here: "
                ))

while True :
    if response == 'Walking' :
        average_time = 60
        break
    elif response == 'Cycling' :
        average_time = 10
        break
    elif response == 'Driving' :
        average_time = 5
        break
    elif response == 'Streetcar' :
        average_time = 7
        break
    else :
        print("Not a Valid Option")


print("Averaging Over" + str(average_time) + "seconds")
time.sleep(2)
i = 0
temp = []
avg_list = []
average_time = 5
accuracy = 1


while True:
    try:
        x = ser.readline()
        temp.append(x)
        if len(temp) == 3: 
            gps = [lin for lin in temp if lin[0:6] == "$GPGGA"]
            met = [lin for lin in temp if lin[0:6] == "$WIMDA"]
            pre = [lin for lin in temp if lin[0:6] == "$YXXDR"]
            if (bool(gps) == True) and  (bool(met) == True) and  (bool(pre) == True):
                t = gps[0][0:12]

                """mert data"""
                """split on commas"""
                met  =  [x.strip() for x in met[0].split(',')]

                """d: pressure in bars, B, temp in celsius, C, ,,,,,,true wind dir, T,
                magnetic wind dir, M, true ws in knots, N, true ws in ms , M"""
                gps = [x.strip() for x in gps[0].split(',')]
                pre = [x.strip() for x in pre[0].split(',')]

                try:
                    lat = str(gps[2])
                    lat = float(lat[0:2]) + float(lat[2:])/60.
                except ValueError:
                    print("Not connected to satalite")
                    continue
                t = gps[1]
                lon = str(gps[4])
                lon = -float(lon[0:3]) - float(lon[3:])/60.
                """need to deal with missing variables"""
                vars_str = [gps[1], str(lat), str(lon), met[5],
                            met[13], met[-2],  str(float(pre[-3] )*1000.), str(float(gps[8]*accuracy))  
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

                print(row)
                

                row =str(row)[1:-1]


           

                #Append to average list and check when it reaches desired length
                if len(avg_list) == average_time :
                    data_list = np.array(avg_list)[:, 1:]
                    ts = np.array(avg_list)[:,0][int(len(avg_list)/2) - 1]
                    data_avg = np.average(data_list,  axis=0)
                    data_avg = np.insert(data_avg, 0, ts)
                    avg_list = []
                    print(data_avg)
                    row2 = ""
                    for var in data_avg:
                        row2 = row2 + str(var) + ","
                    row2 = row2[:-1] + ';' + "\n"
                    if mode != "local":
                        # Open a transport
                        transport = paramiko.Transport((hostname, port))

                        # Authentication
                        transport.connect(username = username, password = password)

                        # Create SFTPClient object called "sftp"
                        sftp = paramiko.SFTPClient.from_transport(transport)

                        # Change the current directory of this SFTP session.
                        sftp.chdir(path= filePath)

                        # Create a python file object from the datasource.txt file
                        fileObject = sftp.file(fileName, mode='a', bufsize=-1)

                        # Write to this file object
                        fileObject.write(row2)

                        # Close the file
                        fileObject.close()

                        # Close the SFTP session and the transport
                        sftp.close()
                        transport.close()
                    else:    
                        file = open('C:\wamp64\www\FirstExample\datasource.txt', 'a')
                        file.write(row2)

                data_rec.write(row + "\n")
                data_rec.flush()
            else:
                print("sentences are missing")
                temp = []
    except KeyboardInterrupt:
        raise
    except:
        print("Something went wrong")
        continue            