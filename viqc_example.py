import json
import time
import time,hmac,base64,hashlib,urllib,urllib2,json
from hashlib import sha256
from decimal import Decimal
import datetime
import sys
import os
from time import gmtime, strftime
import random
#Adapted from Gox Class

class kraken:
	timeout = 15
	tryout = 0

	def __init__(self, key='PUT KEY HERE', secret='PUT SECRET HERE', agent='Kraken PHP API Agent'):
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
		funds_error=False
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
				
				if funds_error:
					raise Exception('Funds')       
				else:
					raise Exception('Timeout')                              




def place_limit_order(krak,kraken_pair,price,volume,side,flags):
	#Placing An Order
	for key, value in krak.req(api_version+'private/AddOrder',
		 {'pair': kraken_pair,
		  'type': side,
		  'ordertype': 'limit',
		  'price':price,
		  'volume':volume,
		  'oflags':flags,
		  }).iteritems():
		if key=="txid":
			return value[0]
	return 0


import socket
sock_timeout=30
socket.setdefaulttimeout(sock_timeout)


api_version="/0/"
krak = kraken()


kraken_pair="XXBTZEUR"
cancel_pair='XBTEUR'

px=400
amount=10.0

try:
	print place_limit_order(krak,'XXBTZEUR',px,amount,'buy','viqc')
	
except Exception, e:
	print str(e)
	exc_type, exc_obj, exc_tb = sys.exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	print(exc_type, fname, exc_tb.tb_lineno)	    
	time.sleep(3)





    
    
