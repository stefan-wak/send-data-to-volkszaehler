# send-data-to-volkszaehler
scripts for reading data and sending to volkszaehler middelware

## send_to_volkszaehler.py
This script read json files (from Fronius SolarAPI) and sends the data to the volkszähler middelware via http request. This script is triggerd via cronjob on the server, which is providing the FTP upload from the Fronius inverter.
