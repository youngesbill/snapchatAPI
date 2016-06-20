import requests
from base64 import b64decode, b64encode
import Crypto.Cipher.AES
import json

##################################
# QueryTools to perform requests #
##################################

class QueryTools():
	def __init__(self, username, password):
		# URL AND KEY FOR API
		self.url = 'ASK FOR url AT youngesbilld@gmail.com'
		self.privateKey = 'ASK FOR KEY AT youngesbilld@gmail.com'
		self.publicKey = 'ASK FOR KEY AT youngesbilld@gmail.com'
		# Account Credentials
		self.username = username
		self.password = password


	def pad(self, s):
	    remainder = (len(s) % 16)
	    return s + chr(16 - remainder) * (16 - remainder)


	def unpad(self, s):
	    for i in ['\x0a', '\x0b', '\x0c', '\x0d', '\x0e', '\x0f', '\x00', '\x01', '\x02', '\x03', '\x04', '\x05', '\x06', '\x07', '\x08', '\x09', '\n']:
	        s = s.replace(i, '')
	    return s

	# To encrypt
	def encryption(self, s):
		padded = self.pad(s)
		return b64encode(Crypto.Cipher.AES.new(self.privateKey, Crypto.Cipher.AES.MODE_CBC, "\x00" * 16).encrypt(padded.encode('utf8')))

	# To decrypt
	def decryption(self, s):
		return self.unpad(Crypto.Cipher.AES.new(self.privateKey, Crypto.Cipher.AES.MODE_CBC, "\x00" * 16).decrypt(b64decode(s)))

	# Get the tokens with the good endpoint
	def get_tokens(self, endpoint = "/loq/login", auth_token = ""):
		dataJson = {
				"username": self.username,
				"password": self.password,
				"endpoint": endpoint
				}
		if len(auth_token):
			dataJson['token'] = auth_token
		dataEncoded = self.encryption(json.dumps(dataJson))
		params = {
				'data': dataEncoded,
				'publicKey': self.publicKey
		}
		try:
			r = requests.get(self.url + '/endpoint/auth', params = params)
			return r.json()
		except Exception, e:
			print e
			return {
				'status_code': 500
			}

	# Check the user, it has to be done in order to perform other queries than endpoint = '/loq/login'
	def checkUser(self, rlogin):
		data = {
				'data': json.dumps(rlogin),
				'username': self.username,
				'password': self.password
		}
		try:
			r = requests.post(self.url + '/check/check', data = data)
			return r.json()
		except Exception, e:
			print e
			return {
				'status_code': 500
			}
