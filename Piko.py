#!/usr/bin/python

# Name     : Piko Inverter communication software
# Rel      : 1.4.1
# Author   : Romuald Dufour
# Contrib. : emoncms export code by Peter Hasse (peter.hasse@fokus.fraunhofer.de)
# Licence  : GPL v3
# History  : 1.4.1 - 20160218 - Add MySQL support
#          : 1.3.3 - 20140117 - Exception handling on emoncms
#                    20140110 - Added support for emoncms export (http://emoncms.org)
#                               json and requests modules depencies added
#                               ('easy_install requests' maybe needed)
#          : 1.3.2 - 20131115 - Bug fixes for some inverter software
#                               (old release not responding to some request)
#          : 1.3.1 - 20130731 - Bug fixes, temp by model, get FW version
#          : 1.3.0 - 20130730 - Csv export (WebSolarLog, ...), -a option
#                               Get additional data (timers, model, strings, phases, ...)
#          : 1.2.6 - 201303xx - Bug fix in comm error handling
#          : 1.2.5 - 20130227 - Add RS485 bus address parameter (--id=xxx)
#          : 1.2.4 - 20121026 - No change (keep rel nb in sync w. Pyko_db)
#          : 1.2.3 - 20110907 - Correct small bug in history import (F=-.-)
#          : 1.2.1 - 20110825 - Temp Decoding beter accuracy
#          : 1.2.0 - 20110824 - Realtime DB save + Status/Temp Decoding
#          : 1.1.0 - 20110817 - History DB save
#          : 1.0.0 - 20110816 - History data
#          : 0.5.0 - 20110812 - Realtime data
#          : 0.1.0 - 20110810 - Online protocol
#
# TODO     : ...

import sys
import socket
import urllib2
import csv
import sqlite3
import MySQLdb as mdb
# import requests
# import json
from optparse import OptionParser, OptionGroup
from datetime import datetime, timedelta


RelVer="1.4.1"
RelDate="20160218"
TRef="c800"
P="?"

# if sys.version_info < (2, 6) or sys.version_info > (2, 9):
#  raise "You must use Python 2.6.x or 2.7.x - Support for 3.x is not yet ready"


# General Functions
def PrintHexa(Txt, St):
    HexSt = ''
    TxtSt = ''
    for i in range(len(St)):
        HexSt += "%02x" % ord(St[i])
        if ((ord(St[i]) >= 0x20) and (ord(St[i]) < 0x7f)):
            TxtSt += St[i]
        else:
            TxtSt += '.'
    #print "%s%s %s" % (Txt, HexSt, TxtSt)
    print "%s%s" % (Txt, HexSt)

def DspTimer(Txt, Timer, fmt):
  St = ""; Space = ""
  if fmt==1: Space=" "
  d = datetime(1,1,1)+timedelta(seconds=Timer)
  if Timer>86400:
    St = "%s%dh%s%02dm%s%02ds" % (Txt, (Timer//86400)*24+d.hour, Space, d.minute, Space, d.second)
  else:
    St = "%s%02dh%s%02dm%s%02ds" % (Txt, d.hour, Space, d.minute, Space, d.second)
  return St

def SndRecv(Addr, Snd, Dbg) :
  Snd="\x62"+chr(Addr)+"\x03"+chr(Addr)+Snd
  Snd+=chr(CalcChkSum(Snd))+"\x00"
  s.send(Snd)
  i = 0
  Recv = ''
  data = ''
  while (1):
    try :
      data = s.recv(4096)
    except :
      Recv += data
      break
    if (i < 5):
        Recv += data
        data = ''
    if not data:
        break
  if (len(Recv)>0) and (ord(Recv[0])==255):
    Recv=""          
  if Dbg and (len(Recv)>0) and (ord(Recv[0])!=255):
    PrintHexa("Sent:", Snd)
    PrintHexa("Recv:", Recv)
  return Recv

def ChkSum(St):
  Chk = 0
  if len(St) == 0: return 0
  for i in range(len(St)):
    Chk += ord(St[i])
    Chk %= 256
  if Chk == 0:
    return 1
  else:
    return 0

def CalcChkSum(St):
  Chk = 0
  if len(St) == 0: return 0
  for i in range(len(St)):
    Chk -= ord(St[i])
    Chk %= 256
  return Chk

def GetWord(St, Idx):
  Val = 0
  Val = ord(St[Idx])+256*ord(St[Idx+1])
  return Val

def GetDWord(St, Idx):
  Val = 0
  Val = ord(St[Idx])+256*ord(St[Idx+1])+65536*ord(St[Idx+2])+256*65536*ord(St[Idx+3])
  return Val

def CnvTemp(Val):
  T=(int("0x"+TRef, 16)-Val)/448.0+22
  if T<0.0: T=0.0
  if T>99.99: T=99.99
  return T

def CnvCA_S(Val):
  # Maybe some mising bit value
  L1="1" if Val & 0x04 else "-"
  L2="2" if Val & 0x08 else "-"
  L3="3" if Val & 0x10 else "-"
  L=L1+L2+L3
  L="L"+L if L!="---" else "-"+L
  I="I" if Val & 0x01 else "-"
  C="C" if Val & 0x02 else "-"
  E="E" if Val & 0x100 else "-"
  return E+I+C+L

def CnvStatusTxt(Val):
  Txt = "Communication error"
  if Val == 0: Txt = "Off"
  if Val == 1: Txt = "Idle"
  if Val == 2: Txt = "Starting"
  if Val == 3: Txt = "Running-MPP"
  if Val == 4: Txt = "Running-Regulated"
  if Val == 5: Txt = "Running"
  return Txt

def GetHistInt(St):
  St = St.strip()
  if len(St) > 0:
    return int(St.replace(".", ""))
  else: return 0;

def GetHistTime(t, tref, now):
  dt=timedelta(seconds=tref-t)
  ht=now-dt
  ht=ht.replace(microsecond=0)
  return ht.isoformat()

def DBConnect(DBName):
  global P
  if len(opt.DBSrv) > 0:
    cnx = mdb.Connect(host=opt.DBSrv, user=opt.DBUsr, passwd=opt.DBPwd, db=DBName)
    P = '%s'
  else:
    cnx = sqlite3.connect(DBName)
    cnx.isolation_level = None
    cnx.row_factory = sqlite3.Row
    P = '?'
  return cnx

def PushToEmon():
# Send like : http://myserver.org/emoncms/input/post.json?json={...ACP:200....}&apikey=1234fc03f4437df98e5a71fe07021234&node=1
    if opt.EmonURL != None and opt.EmonKey != None:
        if Verbose:
            print "- - - - - - - -  E M O N C M S   E X P O R T S  - - - - - - - -"
        if opt.EmonID == None:
            opt.EmonID = 0
            if Verbose:
                print "No EmonID supplied will use 0 as default"
        data = {'STA':Status,
            'DC1U': CC1_U, 'DC1P': CC1_P, 'DC1I': CC1_I,
            'DC2U': CC2_U, 'DC2P': CC2_P, 'DC2I': CC2_I,
            'DC3U': CC3_U, 'DC3P': CC3_P, 'DC3I': CC3_I,
            'AC1U': CA1_U, 'AC1P': CA1_P, 'AC1I': CA1_I,
            'AC2U': CA2_U, 'AC2P': CA2_P, 'AC2I': CA2_I,
            'AC3U': CA3_U, 'AC3P': CA3_P, 'AC3I': CA3_I,
            'ACP': CA_P, 'DCP': CC_P
        }
        payload = {'apikey':opt.EmonKey, 'node':opt.EmonID,'json':json.dumps(data)}
        url = opt.EmonURL + "post.json"
        try:
            r = requests.get(url, params=payload)
            if opt.Dbg:
                print "Emoncms Call:" + str(r.url)
                print "Emoncms Resp:" + str(r)
            if Verbose:
                print "Done..."
        except:
            if Verbose:
                print "Network error while posting result on emoncms"

# Defaults
Dbg = False


# Get CmdLine Args
parser = OptionParser(usage="usage: %prog --host IP [options]", version="%prog v"+RelVer+" - "+RelDate)
parser.add_option("-v", "--verbose", help="Verbose mode, print headers", dest="Headers", action="store_true", default=False)
parser.add_option("-q", "--quiet", help="Quiet mode, print only values", dest="Verbose", action="store_false", default=True)
parser.add_option("", "--timestamp", help="Output timestamp", dest="Timestamp", action="store_true", default=False)
parser.add_option("", "--db", help="database name", dest="DBName", metavar="DB NAME", default="")
SQLGroup=OptionGroup(parser, "SQL connection management", "Management functions to connect to an SQL Server")
SQLGroup.add_option("", "--my", help="Connect to a MySQL server", dest="DBSql", action="store_true", default=False)
SQLGroup.add_option("", "--my-srv", help="Mysql server IP or hostname", dest="DBSrv", metavar="SERVER", default="")
SQLGroup.add_option("", "--my-usr", help="Mysql username", dest="DBUsr", metavar="USERNAME", default="")
SQLGroup.add_option("", "--my-pwd", help="Mysql password", dest="DBPwd", metavar="PASSWORD", default="")
parser.add_option_group(SQLGroup)
HostGroup=OptionGroup(parser, "Inverter online communication options", "Define the inverter IP (or DNS name) and the port to connect to")
HostGroup.add_option("", "--host", help="IP address or DNS name", dest="InvHost", metavar="HOSTNAME", default="127.0.0.1")
HostGroup.add_option("", "--port", help="TCP online port", type=int, dest="InvPort", metavar="81", default="81")
HostGroup.add_option("", "--id", help="RS485 bus address", type=int, dest="Addr", metavar="255", default="255")
HostGroup.add_option("", "--tref", help="Temp reference", dest="TRef", metavar="c800", default="0")
HostGroup.add_option("", "--debug", help="Show data frames", dest="Dbg", action="store_true", default=False)
parser.add_option_group(HostGroup)
HistGroup=OptionGroup(parser, "Inverter history communication options", "Define the inverter http credential")
HistGroup.add_option("", "--user", help="http username", dest="InvUser", metavar="USERNAME", default="pvserver")
HistGroup.add_option("", "--password", help="http password", dest="InvPassword", metavar="PASSWORD", default="pvwr")
parser.add_option_group(HistGroup)
DataGroup=OptionGroup(parser, "Inverter data options", "Select the data to be fetched from inverter")
DataGroup.add_option("-s", "--status", help="Get inverter status", dest="ShowStatus", action="store_true", default=False)
DataGroup.add_option("-i", "--index", help="Get inverter total index (Wh)", dest="ShowTotalIndex", action="store_true", default=False)
DataGroup.add_option("-d", "--daily", help="Get inverter daily index (Wh)", dest="ShowDailyIndex", action="store_true", default=False)
DataGroup.add_option("-p", "--power", help="Get inverter current power (W)", dest="ShowPower", action="store_true", default=False)
DataGroup.add_option("-n", "--name", help="Get inverter name", dest="ShowName", action="store_true", default=False)
DataGroup.add_option("-r", "--serial", help="Get inverter serial number", dest="ShowSN", action="store_true", default=False)
DataGroup.add_option("-m", "--model", help="Get inverter model", dest="ShowModel", action="store_true", default=False)
DataGroup.add_option("-e", "--timers", help="Get inverter timers", dest="ShowTimers", action="store_true", default=False)
DataGroup.add_option("-y", "--history", help="Get history", dest="ShowHistory", action="store_true", default=False)
DataGroup.add_option("-t", "--tech", help="Get technical data", dest="ShowTech", action="store_true", default=False)
DataGroup.add_option("-a", "--all", help="Get all realtime data and print as text", dest="ShowALL", action="store_true", default=False)
DataGroup.add_option("-c", "--csv", help="Get all realtime data and export as csv", dest="ShowCSV", action="store_true", default=False)
parser.add_option_group(DataGroup)
EmonGroup = OptionGroup(parser, "EmonCMS api options", "Define the emon http credential")
EmonGroup.add_option("-u", "--emonurl", help="URL of emoncms to export data", dest="EmonURL", action="store",default=None)
EmonGroup.add_option("-k", "--emonkey", help="API key of emoncms to export data", dest="EmonKey", action="store",default=None)
EmonGroup.add_option("", "--emonid", help="Node ID of emoncms to export data", dest="EmonID", action="store",default=None)
parser.add_option_group(EmonGroup)
(opt, args) = parser.parse_args()

Dbg=opt.Dbg
Verbose=opt.Verbose
if opt.ShowALL:
  opt.ShowStatus = opt.ShowTotalIndex = opt.ShowDailyIndex = opt.ShowPower = opt.ShowName = opt.ShowSN = opt.ShowTech = opt.ShowModel = opt.ShowTimers = True

if opt.DBSql:
  if len(opt.DBSrv)==0: opt.DBSrv='localhost'
  if len(opt.DBName)==0: opt.DBName='piko'
  if len(opt.DBUsr)==0: opt.DBUsr=opt.DBName
  if len(opt.DBPwd)==0: opt.DBPwd=opt.DBName

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

host = opt.InvHost
port = opt.InvPort


# Setup TCP socket
s.settimeout(5)
NetStatus=0
try:
  s.connect((host, port))
  s.settimeout(1)
except socket.error, msg:
  NetStatus=msg


# Initials Prints
if opt.Headers and Verbose and not opt.ShowCSV :
  print  "Comm software   : Piko v%s - %s" % (RelVer, RelDate)
  print  "Comm host       : %s" % host
  print  "Comm port       : %d" % port
  print  "Comm status     : %s" % NetStatus

Now=datetime.now()
if opt.Timestamp and not opt.ShowCSV :
  print  ("%", "Date and time   : %s")[Verbose] % Now.isoformat()

# DB cnx
if len(opt.DBName) > 0:
  UseDB = True
  try:
    DB = DBConnect(opt.DBName)
  except:
    UseDB = False
    if Verbose: print "DB Connection Error"
else:
  UseDB = False


# Get Inverter Status (0=Stop; 1=dry-run; 3..5=running)
if Dbg: print "- - - - - - - - - -  D A T A   F R A M E S  - - - - - - - - - -"
Status = -1; ErrorCode = 0;
if NetStatus == 0:
  Snd="\x00\x57"
  Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    Status = ord(Recv[5]);
    Error = ord(Recv[6]);
    ErrorCode = GetWord(Recv, 7)
  if (Status > 5): Status = -1

StatusTxt = CnvStatusTxt(Status)
if Status != -1:

  # Get Inverter Model
  InvModel = ""
  InvString = 1
  InvPhase = 1
  Snd="\x00\x90"
  Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0 and len(Recv)>=21:
    for i in range(16):
      if 0x20 <= ord(Recv[5+i]) <= 0x7f: InvModel+=Recv[5+i]
    InvString = ord(Recv[5+16])
    InvPhase = ord(Recv[5+23])

  # Get Inverter Version
  InvVer1 = InvVer2 = InvVer3 = 0
  InvVer = ""
  Recv=""; Snd="\x00\x8a"
  Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0 and len(Recv)==13:
    InvVer1 = GetWord(Recv, 5)
    InvVer2 = GetWord(Recv, 7)
    InvVer3 = GetWord(Recv, 9)
    InvVer = "%04x %02x.%02x %02x.%02x" % (InvVer1, InvVer2//256, InvVer2%256, InvVer3//256, InvVer3%256)

  # Calc TRef (Default 0xc800)
  if InvModel == "convert 10T":
    TRef="c800"
  if InvModel == "PIKO 8.3":
    TRef="c800"
  if InvModel == "PIKO 5.5":
    TRef="8000"
  if opt.TRef != "0": TRef = opt.TRef

  # Get Inverter Name
  InvName = ""
  Recv=""; Snd="\x00\x44"
  if opt.ShowName or opt.ShowCSV: Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    for i in range(15):
      if 0x20 <= ord(Recv[5+i]) <= 0x7f: InvName+=Recv[5+i]

  # Get Inverter SN
  InvSN = ""; InvRef = ""
  Recv=""; Snd="\x00\x50"
  if opt.ShowSN or opt.ShowCSV: Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    if len(Recv) == 20:
      for i in range(13):
        if 0x20 <= ord(Recv[5+i]) <= 0x7f: InvSN+=Recv[5+i]
    if len(Recv) == 12:
      SN1=ord(Recv[5]); SN2=ord(Recv[6]); SN3=ord(Recv[7]); SN4=ord(Recv[8]); SN5=ord(Recv[9])
      InvSN+="%1x%1x%1x%1x%1x%1x%1x%1x%1x" % (SN1//16, SN1%16, SN3%16, SN2//16, SN2%16, SN5//16, SN5%16, SN4//16, SN4%16)
  Recv=""; Snd="\x00\x51"
  if opt.ShowSN or opt.ShowCSV: Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    InvRef=GetDWord(Recv, 5)

  # Get Total Wh
  TotalWh = -1
  Recv=""; Snd="\x00\x45"
  Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    TotalWh=GetDWord(Recv, 5)

  # Get Today Wh
  TodayWh = -1
  Recv=""; Snd="\x00\x9d"
  Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    TodayWh=GetDWord(Recv, 5)

  # Total Running time
  InvRunTime = 0
  Recv=""; Snd="\x00\x46"
  if opt.ShowTimers or opt.ShowCSV: Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    InvRunTime=GetDWord(Recv, 5)

  # Total Install time
  InvInstTime = 0
  Recv=""; Snd="\x00\x5b"
  if opt.ShowTimers or opt.ShowCSV: Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    InvInstTime=GetDWord(Recv, 5)
  
  # Last history update time and interval
  InvHistTime = 0
  Recv=""; Snd="\x00\x5d"
  if opt.ShowTimers or opt.ShowCSV: Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    InvHistTime=InvInstTime - GetDWord(Recv, 5)
    if InvHistTime < 0: InvHistTime = 0
  InvHistStep = 0
  Recv=""; Snd="\x00\x5e"
  if opt.ShowTimers or opt.ShowCSV: Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    InvHistStep=GetDWord(Recv, 5)

  # Portal Name & Update Timer
  InvPortalTime = 0
  Recv=""; Snd="\x00\x92"
  if opt.ShowTimers or opt.ShowCSV: Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    InvPortalTime=GetDWord(Recv, 5)
    if InvPortalTime==0xffffffff: InvPortalTime=0;
  InvPortalName = ""
  Recv=""; Snd="\x00\xa6"
  if opt.ShowTimers or opt.ShowCSV: Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0:
    for i in range(32):
      if 0x20 <= ord(Recv[5+i]) <= 0x7f: InvPortalName+=Recv[5+i]

  # Debug options
  if Dbg and not Verbose and opt.ShowALL:
    for i in range(256):
      if (i != 0x50) and (i != 81):
        Recv=""; Snd="\x00"+chr(i)
        Recv=SndRecv(opt.Addr, Snd, Dbg)

  # Get Technical data
  TechData = -1
  Recv=""; Snd="\x00\x43"
  Recv=SndRecv(opt.Addr, Snd, Dbg)
  if ChkSum(Recv) != 0 and (len(Recv)>65):
    TechData = 1
    CC1_U=GetWord(Recv, 5)*1.0/10
    CC1_I=GetWord(Recv, 7)*1.0/100
    CC1_P=GetWord(Recv, 9)
    CC1_T=GetWord(Recv, 11)
    CC1_S=GetWord(Recv, 13)
    CC2_U=GetWord(Recv, 15)*1.0/10
    CC2_I=GetWord(Recv, 17)*1.0/100
    CC2_P=GetWord(Recv, 19)
    CC2_T=GetWord(Recv, 21)
    CC2_S=GetWord(Recv, 23)
    CC3_U=GetWord(Recv, 25)*1.0/10
    CC3_I=GetWord(Recv, 27)*1.0/100
    CC3_P=GetWord(Recv, 29)
    CC3_T=GetWord(Recv, 31)
    CC3_S=GetWord(Recv, 33)
    CA1_U=GetWord(Recv, 35)*1.0/10
    CA1_I=GetWord(Recv, 37)*1.0/100
    CA1_P=GetWord(Recv, 39)
    CA1_T=GetWord(Recv, 41)
    CA2_U=GetWord(Recv, 43)*1.0/10
    CA2_I=GetWord(Recv, 45)*1.0/100
    CA2_P=GetWord(Recv, 47)
    CA2_T=GetWord(Recv, 49)
    CA3_U=GetWord(Recv, 51)*1.0/10
    CA3_I=GetWord(Recv, 53)*1.0/100
    CA3_P=GetWord(Recv, 55)
    CA3_T=GetWord(Recv, 57)
    CA_S=GetWord(Recv, 61)
    CC_P=CC1_P+CC2_P+CC3_P
    CA_P=CA1_P+CA2_P+CA3_P
    if CC_P<1: Eff=0
    else : Eff=CA_P*100.0/CC_P

if Dbg: print "- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -"
s.close()

if UseDB and Status >= 1 and opt.ShowTech:
  T_ISO=GetHistTime(0, 0, Now)
  cur = DB.cursor()
  if CC_P > 0: EFF="%4.1f" % (CA_P*100.0/CC_P)
  else: EFF=0
  try:
    cur.execute("insert into RealTime(TIME, DC1_U, DC1_I, DC1_P, DC1_T, DC1_S, \
                 DC2_U, DC2_I, DC2_P, DC2_T, DC2_S, DC3_U, DC3_I, DC3_P, DC3_T, DC3_S, \
           AC1_U, AC1_I, AC1_P, AC1_T, AC2_U, AC2_I, AC2_P, AC2_T, \
           AC3_U, AC3_I, AC3_P, AC3_T, DC_P, AC_P, EFF, \
           AC_S, Inv_Status, Inv_TodayWh, Inv_TotalWh)\
           values ("+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+",\
                   "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+",\
               "+P+", "+P+", "+P+", "+P+", "+P+")",\
           (T_ISO,\
            "%.1f"%CC1_U, "%.2f"%CC1_I, CC1_P, CC1_T, CC1_S,\
            "%.1f"%CC2_U, "%.2f"%CC2_I, CC2_P, CC2_T, CC2_S,\
            "%.1f"%CC3_U, "%.2f"%CC3_I, CC3_P, CC3_T, CC3_S,\
            "%.1f"%CA1_U, "%.2f"%CA1_I, CA1_P, CA1_T,\
            "%.1f"%CA2_U, "%.2f"%CA2_I, CA2_P, CA2_T,\
            "%.1f"%CA3_U, "%.2f"%CA3_I, CA3_P, CA3_T,\
            CC_P, CA_P, EFF, \
            CA_S, Status, TodayWh, TotalWh))
  except:
    if Dbg or Verbose : print "Failed to insert realtime data into DB"
    pass


if opt.ShowHistory:
  URL = 'http://%s/LogDaten.dat' % host
  PwdMan = urllib2.HTTPPasswordMgrWithDefaultRealm()
  PwdMan.add_password(None, URL, opt.InvUser, opt.InvPassword)
  AuthHandler = urllib2.HTTPBasicAuthHandler(PwdMan)
  Opener = urllib2.build_opener(AuthHandler)
  urllib2.install_opener(Opener)
  PageHandle = urllib2.urlopen(URL)
  Now=datetime.now()
  Page=PageHandle.read()

  Lines=Page.split("\n")
  Reader=csv.reader(Lines, delimiter='\t')
  for Row in Reader:
    if len(Row) == 2:
      if Row.pop(0)=='akt. Zeit:':
        TRef=GetHistInt(Row.pop(0))
    if len(Row) >= 38:
      St=Row.pop(0).strip()
      if St.isdigit():
    T=GetHistInt(St)
    T_ISO=GetHistTime(T, TRef, Now)
        DC1_U=GetHistInt(Row.pop(0))*1.0
        DC1_I=GetHistInt(Row.pop(0))*1.0/1000
        DC1_P=GetHistInt(Row.pop(0))
        DC1_T=GetHistInt(Row.pop(0))
        DC1_S=GetHistInt(Row.pop(0))
        DC2_U=GetHistInt(Row.pop(0))*1.0
        DC2_I=GetHistInt(Row.pop(0))*1.0/1000
        DC2_P=GetHistInt(Row.pop(0))
        DC2_T=GetHistInt(Row.pop(0))
        DC2_S=GetHistInt(Row.pop(0))
        DC3_U=GetHistInt(Row.pop(0))*1.0
        DC3_I=GetHistInt(Row.pop(0))*1.0/1000
        DC3_P=GetHistInt(Row.pop(0))
        DC3_T=GetHistInt(Row.pop(0))
        DC3_S=GetHistInt(Row.pop(0))
        AC1_U=GetHistInt(Row.pop(0))*1.0
        AC1_I=GetHistInt(Row.pop(0))*1.0/1000
        AC1_P=GetHistInt(Row.pop(0))
        AC1_T=GetHistInt(Row.pop(0))
        AC2_U=GetHistInt(Row.pop(0))*1.0
        AC2_I=GetHistInt(Row.pop(0))*1.0/1000
        AC2_P=GetHistInt(Row.pop(0))
        AC2_T=GetHistInt(Row.pop(0))
        AC3_U=GetHistInt(Row.pop(0))*1.0
        AC3_I=GetHistInt(Row.pop(0))*1.0/1000
        AC3_P=GetHistInt(Row.pop(0))
        AC3_T=GetHistInt(Row.pop(0))
    try:
      F=GetHistInt(Row.pop(0))*1.0/10
    except:
      F=0
    FCI=GetHistInt(Row.pop(0))
    AIN1=GetHistInt(Row.pop(0))
    AIN2=GetHistInt(Row.pop(0))
    AIN3=GetHistInt(Row.pop(0))
    AIN4=GetHistInt(Row.pop(0))
        AC_S=GetHistInt(Row.pop(0))
        ERR=GetHistInt(Row.pop(0))
    ENV_S=GetHistInt(Row.pop(0))
    ENV_ERR=GetHistInt(Row.pop(0))
        if len(Row)>=3:
          KB_S=Row.pop(0).strip()
      E=GetHistInt(Row.pop(0))*1000
      R=GetHistInt(Row.pop(0))
        else: KB_S = ""; E=R=0;
    if (len(Row)>0):
      Msg=Row.pop(0)
    else: Msg = ""

        if UseDB:
          cur = DB.cursor()
      DC_P=DC1_P+DC2_P+DC3_P
      AC_P=AC1_P+AC2_P+AC3_P
      if DC_P > 0: EFF="%4.1f" % (AC_P*100.0/DC_P)
      else: EFF=0
      try:
            cur.execute("insert into History(T, TIME, DC1_U, DC1_I, DC1_P, DC1_T, DC1_S, \
                DC2_U, DC2_I, DC2_P, DC2_T, DC2_S, DC3_U, DC3_I, DC3_P, DC3_T, DC3_S, \
                AC1_U, AC1_I, AC1_P, AC1_T, AC2_U, AC2_I, AC2_P, AC2_T, \
                AC3_U, AC3_I, AC3_P, AC3_T, DC_P, AC_P, EFF, F, FCI, AIN1, AIN2, AIN3, AIN4, \
                AC_S, ERR, ENV_S, ENV_ERR, KB_S, E, R, MSG)\
                values ("+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+",\
                        "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+",\
                        "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+", "+P+")",\
                (T, T_ISO,\
                 DC1_U, DC1_I, DC1_P, DC1_T, DC1_S,\
                 DC2_U, DC2_I, DC2_P, DC2_T, DC2_S,\
                 DC3_U, DC3_I, DC3_P, DC3_T, DC3_S,\
                 AC1_U, AC1_I, AC1_P, AC1_T,\
                 AC2_U, AC2_I, AC2_P, AC2_T,\
                 AC3_U, AC3_I, AC3_P, AC3_T,\
                 DC_P, AC_P, EFF, F, FCI, AIN1, AIN2, AIN3, AIN4,\
                 AC_S, ERR, ENV_S, ENV_ERR,\
                 KB_S, E, R, Msg))
      except:
        pass

if UseDB:
  DB.commit()
  DB.close()                                                        

# Results Prints
if (Status != -1):
  if opt.ShowName and len(InvName) >= 0 and not opt.ShowCSV :
    print ("%s", "Inverter Name   : %s")[Verbose] % InvName

  if opt.ShowSN and len(InvSN) >= 0 and not opt.ShowCSV :
    print ("%s", "Inverter SN     : %s")[Verbose] % InvSN
    print ("%08x", "Inverter Ref    : %08x")[Verbose] % InvRef

  if opt.ShowModel and len(InvModel) >= 0 and not opt.ShowCSV :
    print ("%s", "Inverter Model  : %s")[Verbose] % InvModel
    print ("%s", "Inverter Version: %s")[Verbose] % InvVer
    print ("%d", "Inverter String : %d")[Verbose] % InvString
    print ("%d", "Inverter Phase  : %d")[Verbose] % InvPhase

  if opt.ShowTimers and InvInstTime>1 and not opt.ShowCSV :
    print ("%s %d", "Total Time      : %s (%d j)")[Verbose] % (DspTimer("", InvInstTime, 1), InvInstTime//86400)
    print ("%s", "Running Time    : %s")[Verbose] % DspTimer("", InvRunTime, 1)
    print ("%s", "Last Port. upld : %s")[Verbose] % DspTimer("", InvPortalTime, 1)
    print ("%s", "Last Hist. updt : %s")[Verbose] % DspTimer("", InvHistTime, 1)
    print ("%s", "Hist. updt step : %s")[Verbose] % DspTimer("", InvHistStep, 1)

if opt.ShowStatus and not opt.ShowCSV :
  if Verbose: print "Inverter Status : %d (%s)" % (Status, StatusTxt)
  else : print "%d" % Status
  print ("%s", "Inverter Error  : %s")[Verbose] % ErrorCode

if (Status != -1) and not opt.ShowCSV :
  if opt.ShowTotalIndex and TotalWh != -1 :
    print ("%d", "Total energy    : %d Wh")[Verbose] % TotalWh

  if opt.ShowDailyIndex and TodayWh != -1 :
    print ("%d", "Today energy    : %d Wh")[Verbose] % TodayWh

  if opt.ShowPower and TechData != -1 :
    print ("%d %d %.1f", "DC Power        : %4d W\nAC Power        : %4d W\nEfficiency      : %4.1f%%")[Verbose] % (CC_P, CA_P, Eff)

  if opt.ShowTech and TechData != -1 :
    if Verbose:
      print 'DC String 1     : %5.1f V   %4.2f A   %4d W   T=%04x (%5.2f C)  S=%04x' % (CC1_U, CC1_I, CC1_P, CC1_T, CnvTemp(CC1_T), CC1_S)
      print 'DC String 2     : %5.1f V   %4.2f A   %4d W   T=%04x (%5.2f C)  S=%04x' % (CC2_U, CC2_I, CC2_P, CC2_T, CnvTemp(CC2_T), CC2_S)
      print 'DC String 3     : %5.1f V   %4.2f A   %4d W   T=%04x (%5.2f C)  S=%04x' % (CC3_U, CC3_I, CC3_P, CC3_T, CnvTemp(CC3_T), CC3_S)
      print 'AC Phase 1      : %5.1f V   %4.2f A   %4d W   T=%04x (%5.2f C)' % (CA1_U, CA1_I, CA1_P, CA1_T, CnvTemp(CA1_T))
      print 'AC Phase 2      : %5.1f V   %4.2f A   %4d W   T=%04x (%5.2f C)' % (CA2_U, CA2_I, CA2_P, CA2_T, CnvTemp(CA2_T))
      print 'AC Phase 3      : %5.1f V   %4.2f A   %4d W   T=%04x (%5.2f C)' % (CA3_U, CA3_I, CA3_P, CA3_T, CnvTemp(CA3_T))
      print 'AC Status       : %d (%04x %s)' % (CA_S, CA_S, CnvCA_S(CA_S))
    else:
      print '%5.1f %4.2f %4d %04x %04x' % (CC1_U, CC1_I, CC1_P, CC1_T, CC1_S)
      print '%5.1f %4.2f %4d %04x %04x' % (CC2_U, CC2_I, CC2_P, CC2_T, CC2_S)
      print '%5.1f %4.2f %4d %04x %04x' % (CC3_U, CC3_I, CC3_P, CC3_T, CC3_S)
      print '%5.1f %4.2f %4d %04x' % (CA1_U, CA1_I, CA1_P, CA1_T)
      print '%5.1f %4.2f %4d %04x' % (CA2_U, CA2_I, CA2_P, CA2_T)
      print '%5.1f %4.2f %4d %04x' % (CA3_U, CA3_I, CA3_P, CA3_T)

if (Status != -1) and opt.ShowCSV and TechData != -1 :
  print 'PRO,Piko,1,%s,%s' % (RelVer, RelDate)
  print 'TIM,%s,%s,%s' % (Now.isoformat(), DspTimer("", InvInstTime, 0), DspTimer("", InvRunTime, 0))
  print 'INF,%s,%s,%s,%s,%s,%s,%d,%d' % (InvSN, InvName, host, port, opt.Addr, InvModel, InvString, InvPhase)
  print 'VER,%s' % (InvVer)
  print 'STA,%d,%s,%d,%s,%d' % (Status, StatusTxt, CA_S, CnvCA_S(CA_S), ErrorCode)
  print 'ENE,%d,%d' % (TotalWh, TodayWh)
  print 'PWR,%d,%d,%.1f' % (CC_P, CA_P, Eff)
  print 'DC1,%.1f,%.2f,%d,%.2f,%04x,%04x' % (CC1_U, CC1_I, CC1_P, CnvTemp(CC1_T), CC1_T, CC1_S)
  print 'DC2,%.1f,%.2f,%d,%.2f,%04x,%04x' % (CC2_U, CC2_I, CC2_P, CnvTemp(CC2_T), CC2_T, CC2_S)
  print 'DC3,%.1f,%.2f,%d,%.2f,%04x,%04x' % (CC3_U, CC3_I, CC3_P, CnvTemp(CC3_T), CC3_T, CC3_S)
  print 'AC1,%.1f,%.2f,%d,%.2f,%04x' % (CA1_U, CA1_I, CA1_P, CnvTemp(CA1_T), CA1_T)
  print 'AC2,%.1f,%.2f,%d,%.2f,%04x' % (CA2_U, CA2_I, CA2_P, CnvTemp(CA2_T), CA2_T)
  print 'AC3,%.1f,%.2f,%d,%.2f,%04x' % (CA3_U, CA3_I, CA3_P, CnvTemp(CA3_T), CA3_T)
  print 'PRT,%s,%s' % (InvPortalName, DspTimer("", InvPortalTime, 1))
  print 'HST,%s,%s' % (DspTimer("", InvHistTime, 0), DspTimer("", InvHistStep, 0))

PushToEmon()

# Done

