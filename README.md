# send-data-to-volkszaehler
scripts for reading data and sending to volkszaehler middelware

## send_to_volkszaehler.py
This script read json files (from Fronius SolarAPI) and sends the data to the volkszähler middelware via http request. This script is triggerd via cronjob on the server, which is providing the FTP upload from the Fronius inverter.

## read_serial_current.py
This script reads 4 current-values from serial port (there is a microcontroller for measuring the 4 current-values and sending them via virtual com port (VCP) each second) and calculate a mean value over the given time. The script needs one parameter, which is the time in seconds for accumulating the data from serial prot. read_serial_current.py will be triggerd by the vzlogger (see the attached part of the vzlooger.conf) each 30 secounds and will calculate the mean values for 15 seconds or 15 given lines of data.

```
  {
  "enabled": true,
  "allowskip": true,
  "protocol": "exec",
  "command": "/home/pi/read_serial_current.py 15",
  "format": "$t : $i  =  $v",
  "interval": 30,
  "channels": [
    {
      "uuid": "12345678-aaaa-aaaa-cccc-xxxxxxxxxxxx",
      "identifier": "i1",
      "middleware": "http://192.168.0.215/middleware.php",
      "duplicates": 60
    },
    {
      "uuid": "12345678-aaaa-aaaa-cccc-xxxxxxxxxxx1",
      "identifier": "i2",
      "middleware": "http://192.168.0.215/middleware.php",
      "duplicates": 60
    },
    {
      "uuid": "12345678-aaaa-aaaa-cccc-xxxxxxxxxxx2",
      "identifier": "i3",
      "middleware": "http://192.168.0.215/middleware.php",
      "duplicates": 60
    },
    {
      "uuid": "12345678-aaaa-aaaa-cccc-xxxxxxxxxxx3",
      "identifier": "i4",
      "middleware": "http://192.168.0.215/middleware.php",
      "duplicates": 60
    }
    ]
  }
```
