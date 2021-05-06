#!/usr/bin/env python3
import time
import serial
import sys

MAX_RMS = 100
I_SCALE = 12.5
LINE_LEN = 4

ser = serial.Serial(
    port='/dev/ttyACM0',
    baudrate=57600,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS,
    timeout=1
)
ser.flushInput()    # clear all input from input-buffer

cnt = 0        # counter for argv[1] current values
sum_i1 = 0; sum_i2 = 0; sum_i3 = 0; sum_i4 = 0;

ser.flushInput()    # clear all input from input-buffer
while cnt < int(sys.argv[1]):
    #print("cnt:", cnt)
    cur = [0.0, 0.0, 0.0, 0.0]
    x = ser.readline()
    current = x.split()
    if (len(current) == LINE_LEN):
        for i in range(0, LINE_LEN):
            cur[i] = float(current[i])/float(I_SCALE)
            #print(cur[i])
        if ((cur[0] >= 0) and (cur[0] < MAX_RMS) and
            (cur[1] >= 0) and (cur[1] < MAX_RMS) and
            (cur[2] >= 0) and (cur[2] < MAX_RMS) and
            (cur[3] >= 0) and (cur[3] < MAX_RMS)):
            sum_i1 += cur[0]; sum_i2 += cur[1]; sum_i3 += cur[2]; sum_i4 += cur[3];
        cnt += 1
    else:
        #print("don`t get a complete line!")
        continue

sum_i = [sum_i1, sum_i2, sum_i3, sum_i4]
t = time.time()
for i in range(0, 4):
    print(round(t)*1000, ": i"+str(i+1), " = ", round(sum_i[i]*100/cnt) / 100)