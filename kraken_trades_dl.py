import json
import time,hmac,base64,hashlib,urllib,urllib2,json
from hashlib import sha256
from decimal import Decimal
import datetime
from datetime import datetime
import sys
import os
import math
import calendar

class kraken:
	timeout = 15
	tryout = 0

	def __init__(self, key=None, secret=None, agent='Kraken PHP API Agent'):
		self.key, self.secret, self.agent = key, secret, agent
		self.time = {'init': time.time(), 'req': time.time()}
		self.reqs = {'max': 10, 'window': 10, 'curr': 0}
		self.base = 'https://api.kraken.com'
		
	def throttle(self):
		# check that in a given time window (10 seconds),
		# no more than a maximum number of requests (10)
		# have been sent, otherwise sleep for a bit
		diff = time.time() - self.time['req']
		if diff > self.reqs['window']:
			self.reqs['curr'] = 0
			self.time['req'] = time.time()
		self.reqs['curr'] += 1
		if self.reqs['curr'] > self.reqs['max']:
			print 'Request limit reached...'
			time.sleep(self.reqs['window'] - diff)

	def makereq(self, path, data , nonce):
		
		# bare-bones hmac rest sign
		sign=str(hmac.new(base64.b64decode(self.secret), path +
				  sha256(nonce+data).digest()
				  , hashlib.sha512).digest())
		return urllib2.Request(self.base + path, data, {
			'User-Agent': self.agent,
			'API-Key: ': self.key,
			'API-Sign: ': base64.b64encode(sign)
		})

	def req(self, path, inp={}):
		t0 = time.time()
		tries = 0
		while True:
			# check if have been making too many requests
			self.throttle()

			try:
				# send request to mtgox
				n=str(int(time.time() * 1e6))
				inp['nonce'] = n
				inpstr = urllib.urlencode(inp.items())
				req = self.makereq(path, inpstr,n)
				response = urllib2.urlopen(req, inpstr)

				# interpret json response
				output = json.load(response)
				if 'error' in output:
					if output['error']!=[]:
						print output
						raise ValueError(output['error'])


				return output['result']
				
			except Exception as e:
				print "Error: %s" % e

			# don't wait too long
			tries += 1
			if time.time() - t0 > self.timeout or tries > self.tryout:
				raise Exception('Timeout')


key='KEY GOES HERE'
secret='SECRET GOES HERE'

api_version="/0/"
krak = kraken(key,secret)
pairs={}
ledger_type="deposit"

header=""
header+="timestamp"+"\t"
header+='fee'+"\t"
header+='vol'+"\t"
header+='ordertype'+"\t"
header+='ordertxid'+"\t"
header+='pair'+"\t"
header+='cost'+"\t"
header+='type'+"\t"
header+='price'+"\n"

results=open('trades.txt','w')
results.write(header)


dt_end=None    
x=0
count=10
while count>1:
	count=0	
	try:
		if dt_end == None:
			txs=krak.req(api_version+'private/TradesHistory')
		else:
			txs=krak.req(api_version+'private/TradesHistory',{'end':dt_end})
		
		ledger_items=txs['trades']
		for tx in ledger_items:
			count+=1

			t=math.ceil(ledger_items[tx]['time'])

			#DT_END becomes the highest time from the result set
			if dt_end==None:
				dt_end=ledger_items[tx]['time']
			elif dt_end>ledger_items[tx]['time']:
				dt_end=ledger_items[tx]['time']
			
			try:
				dt_print=str(datetime.fromtimestamp(t))
			except:
				dt_print="N\A"
			
			#Construct THe Row
			print_string=""
			print_string+=dt_print+"\t"
			print_string+=str(ledger_items[tx]['fee'])+"\t"
			print_string+=str(ledger_items[tx]['vol'])+"\t"
			print_string+=str(ledger_items[tx]['ordertype'])+"\t"
			print_string+=str(ledger_items[tx]['ordertxid'])+"\t"
			print_string+=str(ledger_items[tx]['pair'])+"\t"
			print_string+=str(ledger_items[tx]['cost'])+"\t"
			print_string+=str(ledger_items[tx]['type'])+"\t"
			print_string+=str(ledger_items[tx]['price'])+"\n"

			#Print and Flush it
			results.write(print_string)
			results.flush()

		#How Many Rows were added... Most likely the max at 50
		print str(datetime.fromtimestamp(math.ceil(dt_end)))+" : "+str(x)+" : "+str(count)
		
		#Sleep So We Don't Timeout the Api
		time.sleep(5)
		x+=1
	except Exception, e:
	    print "Error Script Died"
	    print str(e)     

