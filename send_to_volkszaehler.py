#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
read Fronius data (SolarAPI v1 - CurrentData - Inverter)
and send it to volkszaehler via middelware API
"""

import json
import time
import requests
import os

# volkszaehler IP-adress
HOST = "192.168.0.215"
# location, of the json files
storage_path = 'D:\Fronius_Daten'

def main():

    # list all files in this directory
    f = []
    for (dirpath, dirnames, filenames) in os.walk(storage_path):
        break

    # collect all json files for data tranmission
    for fn in filenames:
        if fn[-5:] == '.json':
            f.append(fn)
    length = len(f)

    # loop over each json-file
    for idx in range(0, length):
        with open(f[idx]) as file:
            data = json.load(file)
            # remove the last characters (timzone shift) from data string
            date_time_string = data['Head']['Timestamp'][0:-6]
            date_time_format = "%Y-%m-%dT%H:%M:%S"
            time_object = time.strptime(date_time_string, date_time_format)
            # timestamp in ms
            ts = round(time.mktime(time_object)) * 1000
            # extract the data
            power_ac = data['Body']['PAC']['Values']['1']
            day_energy = data['Body']['DAY_ENERGY']['Values']['1']
            total_energy = data['Body']['TOTAL_ENERGY']['Values']['1']
            # send the data to the server
            requests.get(generate_request(HOST, 'b00fd670-adb6-11eb-8893-7fdf4bd4f3dd', ts, power_ac))
            requests.get(generate_request(HOST, 'ffc5c8d0-adb6-11eb-89cf-99b51da8f4b3', ts, total_energy))
            requests.get(generate_request(HOST, '42927f00-adb7-11eb-87ea-e5b8fd381a43', ts, day_energy))
        file.close()
        print('File ' + str(idx+1) + ' from ' + str(length))
        # move file to backup-subfolder
        os.rename(dirpath + '\\' + f[idx], dirpath + '\\backup\\' + f[idx])


def generate_request(host, uuid, ts, value):
    """ Generate the required url to send the data to the middelware API
    
    Keyword arguments:
    host -- hsotname or IP-adress from the middleware-server as string
    uuid -- the uuid from the data-source
    ts -- timestamp in milliseconds
    """
    res = "http://{0:s}/middleware.php/data/{1:s}.json?operation=add&ts={2}&value={3:3.1f}".format(host, uuid, ts, value)
    return res


if __name__ == "__main__":
    main()