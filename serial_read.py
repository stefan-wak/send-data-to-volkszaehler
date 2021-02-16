#!/usr/bin/env python3
import time
# from time import gmtime, strftime
import serial
import sqlite3
import requests
# from rrdtool import update as rrd_update

MAX_RMS = 100
I_SCALE = 12.5

ser = serial.Serial(
    port='/dev/ttyACM0',
    baudrate=57600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)
ser.flushInput()    # clear all input from input-buffer

# Open database connection
db = sqlite3.connect('/home/pi/readSerial/power.db')
# prepare a cursor object using cursor() method
cursor = db.cursor()
# Prepare SQL query to INSERT a record into the database.
sql = "INSERT INTO current VALUES (?, ?, ?, ?, ?)"

cnt = 0        # counter for 60 current values
sum_i1 = 0; sum_i2 = 0; sum_i3 = 0; sum_i4 = 0;

ser.flushInput()    # clear all input from input-buffer
while 1:
    cur = [0, 0, 0, 0]
    x = ser.readline()
    current = x.split()
    # print(current)    #debug
    if (len(current) == 4):
        for i in range(0, 4):        # Achtung: Index muss bis 4 laufen !?!?
            cur[i] = float(current[i])/float(I_SCALE)
        if ((cur[0] >= 0) and (cur[0] < MAX_RMS) and
            (cur[1] >= 0) and (cur[1] < MAX_RMS) and
            (cur[2] >= 0) and (cur[2] < MAX_RMS) and
            (cur[3] >= 0) and (cur[3] < MAX_RMS)):
            # print(cur[0], cur[1], cur[2], cur[3])
            sum_i1 += cur[0]; sum_i2 += cur[1]; sum_i3 += cur[2]; sum_i4 += cur[3];
            cnt = cnt + 1
            if (cnt == 60):
                # ret = rrd_update('/home/pi/readSerial/power.rrd', 'N:%s:%s:%s:%s' %(sum_i1/cnt, sum_i2/cnt, sum_i3/cnt, sum_i4/cnt));
                # print("Values: ", (sum_i1/cnt, sum_i2/cnt, sum_i3/cnt, sum_i4/cnt))
                # http://localhost/middleware.php/data/21249ac0-70cd-11ea-b021-350e8bab7e6b.json?operation=add&value=5.5
                # i1:
                add_i1 = "http://localhost/middleware.php/data/{0:s}.json?operation=add&value={1:3.1f}".format('f6ad5580-70cc-11ea-8e96-cf91bda3060c', sum_i1/cnt)
                requests.get(add_i1)

                # i2:
                add_i2 = "http://localhost/middleware.php/data/{0:s}.json?operation=add&value={1:3.1f}".format('0fc21880-70cd-11ea-80ce-03885332c379', sum_i2/cnt)
                requests.get(add_i2)

                # i3:
                add_i3 = "http://localhost/middleware.php/data/{0:s}.json?operation=add&value={1:3.1f}".format('172fd700-70cd-11ea-8a69-93cdace01130', sum_i3/cnt)
                requests.get(add_i3)

                # i4:
                add_i4 = "http://localhost/middleware.php/data/{0:s}.json?operation=add&value={1:3.1f}".format('21249ac0-70cd-11ea-b021-350e8bab7e6b', sum_i4/cnt)
                requests.get(add_i4)
                # print(add_i4)

                date_time = time.strftime("%Y-%m-%d %H:%M:%S")
                try:
                   cursor.execute(sql, (date_time, sum_i1/cnt, sum_i2/cnt, sum_i3/cnt, sum_i4/cnt))
                   db.commit()        # Commit your changes in the database
                except:
                   db.rollback()    # Rollback in case there is any error
                   print("Error during adding values to database!")
                sum_i1 = 0; sum_i2 = 0; sum_i3 = 0; sum_i4 = 0;
                cnt = 0

    #del x, current, cur

# disconnect from server
db.close()
