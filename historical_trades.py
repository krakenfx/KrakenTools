import os
import re
import urllib2
import sys
import json
import math
from datetime import datetime, timedelta
import time

dt_start=datetime(2014,6,11,0,0,0)

output_file=open('trades.csv','w')
output_file.write("Timestamp,Tid,Price,Volume\n")
pair='XXBTZEUR'

stop=False
max_id=0

count=0
q=1000
max_id=int((dt_start - datetime(1970,1,1)).total_seconds()*1000000000)

while q>1:
    opener = urllib2.build_opener()

    
    api_pair=pair.replace("_","")
    api_pair=str(api_pair).upper()
    opener.addheaders = [('User-agent', 'Mozilla/5.0 (Windows NT 6.2; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/32.0.1667.0 Safari/537.36')]
    

    response = opener.open("https://api.kraken.com/0/public/Trades?pair="+pair+"&since="+str(max_id))
    print("https://api.kraken.com/0/public/Trades?pair="+pair+"&since="+str(max_id))
    
    json_result=json.load(response)
    x=json_result['result'][pair]

    q=0
    for iHist in x:
        t=math.ceil((iHist[2]))
        tid=int(float(iHist[2])*1000000000)
        q+=1
        if tid>max_id:
            max_id=tid

        output_file.write(str(datetime.fromtimestamp(t))+","+str(tid)+","+str(iHist[0])+","+str(iHist[1])+"\n")

    print(str(q)+" : Trades Processed")
    count+=1
    time.sleep(5)

output_file.close()
