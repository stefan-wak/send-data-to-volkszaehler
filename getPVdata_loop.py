#!/usr/bin/env python

import os
import sys
import time
import json
import urllib
import sqlite3
import requests
import time
# from rrdtool import update as rrd_update

while True:
    try:
        startTime = time.time()
        date_time = time.strftime("%Y-%m-%d %H:%M:%S")
        # Open database connection
        db = sqlite3.connect('/home/pi/readSerial/PVdata.db')
        # prepare a cursor object using cursor() method
        cursor = db.cursor()
        # Prepare SQL query to INSERT a record into the database.
        sql_piko = "INSERT INTO piko VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        sql_fronius = "INSERT INTO fronius VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"


        # PIKO 5.5
        input = os.popen("/usr/bin/python /home/pi/readSerial/Piko.py --host=192.168.0.50 -q -i -d -p -t").readlines()
        #print(input)

        totalEnergy = int(input[0])    # total Energy for DB
        todayEnergy = int(input[1])    # today Energy for DB
        power = input[2].split()    # [acPower dcPower efficiency]
        acPower = int(power[1])        # ac Power for DB

        phase1 = input[6].split()
        u1 = float(phase1[0])
        i1 = float(phase1[1])
        phase2 = input[7].split()
        u2 = float(phase2[0])
        i2 = float(phase2[1])
        phase3 = input[8].split()
        u3 = float(phase3[0])
        i3 = float(phase3[1])

        p_acPower = acPower
        p_totalEnergy = totalEnergy
        p_todayEnergy = todayEnergy
        p_i1 = i1
        p_i2 = i2
        p_i3 = i3

        try:
           cursor.execute(sql_piko, (date_time, acPower, totalEnergy, todayEnergy, u1, i1, u2, i2, u3, i3))
           db.commit()          # Commit your changes in the database
        except:
           db.rollback()        # Rollback in case there is any error
           print("Error during adding PIKO-values to PVdata-database!")

        # Daten an Volkszaehler uebertragen
        piko_i1_uuid = '87cd0520-71a5-11ea-b7a5-3bfe16baea4c'
        piko_i2_uuid = 'a5fca700-71a5-11ea-985b-4d9835128a28'
        piko_i3_uuid = 'b2a33b10-71a5-11ea-80db-0d5bbec70e1b'
        piko_leistung_uuid = '18298100-71a6-11ea-9556-3fcc3b9ffb0b'
        piko_tagesenergie_uuid = '60629f60-71a6-11ea-94d0-2549ce7ceb7b'
        piko_gesamtenergie_uuid = '85b7b980-71a6-11ea-82d0-158a7c0dcbc5'
        vz_add_data_string = "http://localhost/middleware.php/data/{0:s}.json?operation=add&value={1:3.1f}"
        # add_i1 = vz_add_data_string.format(piko_i1_uuid, i1)
        requests.get(vz_add_data_string.format(piko_i1_uuid, i1))
        requests.get(vz_add_data_string.format(piko_i2_uuid, i2))
        requests.get(vz_add_data_string.format(piko_i3_uuid, i3))
        requests.get(vz_add_data_string.format(piko_leistung_uuid, acPower))
        requests.get(vz_add_data_string.format(piko_tagesenergie_uuid, todayEnergy))
        requests.get(vz_add_data_string.format(piko_gesamtenergie_uuid, totalEnergy))

        # FRONIUS SYMO 17.5-3-M
        try:
            link = "http://192.168.0.51/solar_api/v1/GetInverterRealtimeData.cgi?Scope=System"
            f = urllib.urlopen(link)
            pvData = f.read()
            pv_json = json.loads(pvData)
            f_acPower = pv_json["Body"]["Data"]["PAC"]["Values"]["1"]
            f_todayEnergy = pv_json["Body"]["Data"]["DAY_ENERGY"]["Values"]["1"]
            f_totalEnergy = pv_json["Body"]["Data"]["TOTAL_ENERGY"]["Values"]["1"]
            # print(f_acPower, f_totalEnergy, f_dayEnergy)
            link = "http://192.168.0.51/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DeviceId=1&DataCollection=3PInverterData"
            f = urllib.urlopen(link)
            pvData = f.read()
            pv_json = json.loads(pvData)
            f_i1 = pv_json["Body"]["Data"]["IAC_L1"]["Value"]
            f_i2 = pv_json["Body"]["Data"]["IAC_L2"]["Value"]
            f_i3 = pv_json["Body"]["Data"]["IAC_L3"]["Value"]
            f_u1 = pv_json["Body"]["Data"]["UAC_L1"]["Value"]
            f_u2 = pv_json["Body"]["Data"]["UAC_L2"]["Value"]
            f_u3 = pv_json["Body"]["Data"]["UAC_L3"]["Value"]
            # print(f_i1, f_i1, f_i3, f_u1, f_u2, f_u3)

            # Daten an Volkszauhler uebertragen
            f_i1_uuid = '20452a20-71a7-11ea-b08e-ad2a748b42de'
            f_i2_uuid = '3043cf30-71a7-11ea-a034-4ba0c5368e30'
            f_i3_uuid = '39bed370-71a7-11ea-b365-893590bcaca6'
            f_leistung_uuid = '56b8f440-71a7-11ea-9640-434cf41d3844'
            f_tagesenergie_uuid = '6ff508b0-71a7-11ea-9e15-6bae44c3c06d'
            f_gesamtenergie_uuid = '7e22feb0-71a7-11ea-b7f9-97a5f82c442a'
            vz_add_data_string = "http://localhost/middleware.php/data/{0:s}.json?operation=add&value={1:3.1f}"
            # add_i1 = vz_add_data_string.format(piko_i1_uuid, i1)
            requests.get(vz_add_data_string.format(f_i1_uuid, f_i1))
            requests.get(vz_add_data_string.format(f_i2_uuid, f_i2))
            requests.get(vz_add_data_string.format(f_i3_uuid, f_i3))
            requests.get(vz_add_data_string.format(f_leistung_uuid, f_acPower))
            requests.get(vz_add_data_string.format(f_tagesenergie_uuid, f_todayEnergy))
            requests.get(vz_add_data_string.format(f_gesamtenergie_uuid, f_totalEnergy))

            try:
               cursor.execute(sql_fronius, (date_time, f_acPower, f_totalEnergy, f_todayEnergy, f_u1, f_i1, f_u2, f_i2, f_u3, f_i3))
               db.commit()          # Commit your changes in the database
            except:
               db.rollback()        # Rollback in case there is any error
               print("Error during adding FRONIUS-values to PVdata-database!")

            # ret = rrd_update('/home/pi/readSerial/PVdata.rrd', 'N:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s' %(p_acPower, p_totalEnergy, p_todayEnergy, p_i1, p_i2, p_i3, f_acPower, f_totalEnergy, f_todayEnergy, f_i1, f_i2, f_i3));
            # print(ret)
            # print(p_acPower, p_totalEnergy, p_todayEnergy, p_i1, p_i2, p_i3, f_acPower, f_totalEnergy, f_todayEnergy, f_i1, f_i2, f_i3)

        except:
            # print("Unexpected error:", sys.exc_info()[0])
            # ret = rrd_update('/home/pi/readSerial/PVdata.rrd', 'N:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s:%s' %(p_acPower, p_totalEnergy, p_todayEnergy, p_i1, p_i2, p_i3, 'U', 'U', 'U', 'U', 'U', 'U'));
            # print(ret)
            # print(p_acPower, p_totalEnergy, p_todayEnergy, p_i1, p_i2, p_i3, 0, 0, 0, 0, 0, 0)

        # disconnect from server
        db.close()

    finally:
        endTime = time.time()
        time.sleep(60 + startTime - endTime)

