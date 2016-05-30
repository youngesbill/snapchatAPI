#!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
from pprint import pprint
import uuid
import hashlib
from base64 import b64decode, b64encode
import warnings
import time
import json
import random
from Crypto.Cipher import AES, PKCS1_OAEP
from QueryTools import QueryTools

warnings.filterwarnings('ignore')

SECRET = b'iEk21fuwZApXlz93750dmW22pw389dPwOk'
STATIC_TOKEN = 'm198sOkJEn37DjqZ32lpRu76xmw288xSQ9'
BLOB_ENCRYPTION_KEY = 'M02cnQ51Ji97vwT4'
HASH_PATTERN = ('00011101111011100011110101011110'
				'11010001001110011000110001000110')

MEDIA_IMAGE = 0
MEDIA_VIDEO = 1
MEDIA_VIDEO_NOAUDIO = 2

def pkcs5_pad(data, blocksize=16):
    pad_count = blocksize - len(data) % blocksize
    return data + (chr(pad_count) * pad_count).encode('utf-8')

def decrypt_story(data, key, iv):
    akey = b64decode(key)
    aiv = b64decode(iv)
    cipher = AES.new(akey, AES.MODE_CBC, aiv)
    return cipher.decrypt(pkcs5_pad(data))

def is_video(data):
	return True if data[0:2] == b'\x00\x00' else False

def is_image(data):
	return True if data[0:2] == b'\xFF\xD8' else False

def is_zip(data):
	return True if data[0:2] == b'PK' else False


####################
# Snapchat Account #
####################

class Snapchat():
	def __init__(self, username, password, proxies={}):
		self.proxies = proxies
		# Credentials
		self.username = username.lower()
		self.password = password
		self.auth_token = ''
		self.uri = 'https://app.snapchat.com'
		self.tokens = {}
		self.QueryTools = QueryTools(self.username, self.password)

	# Instant of time
	def now(self):
		return "%d" % (time.time() * 1000)

	# Encrypt keys with hash
	def make_request_token(self, a, b):
		hash_a = hashlib.sha256(SECRET + a.encode('utf-8')).hexdigest()
		hash_b = hashlib.sha256(b.encode('utf-8') + SECRET).hexdigest()
		return ''.join((hash_b[i] if c == '1' else hash_a[i]
						for i, c in enumerate(HASH_PATTERN)))

	# Set a proxy 
	def set_proxy(self, proxy):
		self.proxies = proxy
		return self.proxies

	# Flush the tokens of all the endpoints
	def flush_tokens(self):
		self.tokens = {}

	# Return the tokens of all the endpoints
	def get_tokens(self):
		return self.tokens

	# Perform request
	def request(self, endpoint, auth_token="", post=True, headers={}, data={}, files={}):
		gotHeaders = False
		if endpoint in self.tokens:
			if int(self.tokens[endpoint]['timestamp']) + 300000 > time.time() * 1000:
				headers.update(self.tokens[endpoint]['headers'])
				gotHeaders = True

		if not gotHeaders:
			r_tokens = self.QueryTools.get_tokens(endpoint, auth_token=auth_token)
			if r_tokens['status_code'] == 200:
				if 'tokens' in r_tokens:
					for ep, headersobj in r_tokens['tokens'].iteritems():
						endpoint_info = {
							'headers': headersobj['headers'],
							'endpoint': headersobj['endpoint'],
							'timestamp': r_tokens['timestamp']
						}
						self.tokens[ep] = endpoint_info 

					headers.update(self.tokens[endpoint]['headers'])
				else:
					endpoint_info = {
						'headers': r_tokens['headers'],
						'endpoint': r_tokens['endpoint'],
						'timestamp': r_tokens['timestamp']
					}
					self.tokens[endpoint] = endpoint_info
					headers.update(endpoint_info['headers'])
		headers.update({
			"Accept-Encoding": "gzip",
			"Accept-Language": "en",
			"Accept-Locale": "en_US",
			"Accept": "*/*"
		})
		data['timestamp'] = self.tokens[endpoint]['timestamp']

		if endpoint == '/loq/login':
			data['req_token'] = self.make_request_token(STATIC_TOKEN, self.tokens[endpoint]['timestamp'])
		else:
			data['req_token'] = self.make_request_token(self.auth_token, self.tokens[endpoint]['timestamp'])

		if post:
			r = requests.post(self.uri + endpoint, data=data, files=files, headers=headers, verify=False, proxies = self.proxies)
		else:
			r = requests.get(self.uri + endpoint, params=data, files=files, headers=headers, verify=False, proxies = self.proxies)

		if r.status_code in [200, 201, 202]:
			if endpoint == "/bq/upload":
				return {
					'status': 200,
					'result': r.content
				}

			try:
				j = r.json()
				if 'status' in j:
					if j['status'] == -100:
						return {
							'status': 500,
							'result': j
						}
					else:
						return {
							'status': 200,
							'result': j
						}
				else:
					if endpoint == "/loq/login":
						self.auth_token = j['updates_response']['auth_token']
					return {
						'status': 200,
						'result': j
					}
			except Exception, e:
				print e
				return {
					'status': r.status_code,
					'result': r.content
				}
		else:
			return {
				'status': r.status_code,
				'result': r.content
			}

	def fetch_tokens(self, endpoint, auth_token=""):
		r_tokens = self.QueryTools.get_tokens(endpoint, auth_token=auth_token)
		headers = {}
		data = {}
		if r_tokens.status_code == 200:
			r_tokens = r_tokens.json()
			if 'tokens' in r_tokens:
				for ep, headersobj in r_tokens['tokens'].iteritems():
					endpoint_info = {
						'headers': headersobj['headers'],
						'endpoint': headersobj['endpoint'],
						'timestamp': r_tokens['timestamp']
					}
					self.tokens[ep] = endpoint_info 

				headers.update(self.tokens[endpoint]['headers'])
			else:
				endpoint_info = {
					'headers': r_tokens['headers'],
					'endpoint': r_tokens['endpoint'],
					'timestamp': r_tokens['timestamp']
				}
				self.tokens[endpoint] = endpoint_info
				headers.update(endpoint_info['headers'])
		headers.update({
			"Accept-Encoding": "gzip",
			"Accept-Language": "en",
			"Accept-Locale": "en_US",
			"Accept": "*/*"
		})

		data['timestamp'] = self.tokens[endpoint]['timestamp']

		if endpoint == '/loq/login':
			data['req_token'] = self.make_request_token(STATIC_TOKEN, self.tokens[endpoint]['timestamp'])
		else:
			data['req_token'] = self.make_request_token(self.auth_token, self.tokens[endpoint]['timestamp'])

		return {
			'headers': headers,
			'params': data
		}

	# Set the session token
	def set_auth_token(self, token):
		self.auth_token = token
		return token

	# Get the session token
	def get_auth_token(self):
		return self.auth_token

	# Get the tokens for all the endpoint
	def get_tokens(self):
		return self.tokens

	# Set the tokens for all the endpoint
	def set_tokens(self):
		self.tokens = tokens
		return self.tokens

	# Login the account
	def login(self, pre_auth_token=""):
		data = {
			"pre_auth_token": pre_auth_token,
			"remember_device": "true",
			"screen_height_px": "800",
			"width": "640",
			"password": self.password,
			"height": "1280",
			"screen_width_in": "2.992127",
			"screen_width_px": "480",
			"screen_height_in": "5.0",
			"username": self.username,
			"nt": "1"
		}

		if pre_auth_token:
			data['two_fa_mechanism_used'] = 'sms'

		r = self.request("/loq/login", data = data)

		if r['status'] == 200:
			j = r['result']
			response = {
				'status': 200,
				'result': j
				}
			# THE ACCOUNT HAS TO BE CHECKED IN ORDER TO USE THE API
			self.QueryTools.checkUser(response)
			return response
		else:
			return r

	# Get the updates
	def updates(self):
		data = {
			"username": self.username,
			"max_video_width": "720",
			"screen_width_in": "2.992127",
			"checksums_dict": "{}",
			"width": "720",
			"screen_height_px": "800",
			"height": "1280",
			"screen_width_px": "480",
			"features_map": '{"stories_delta_response":true,"conversations_delta_response":true}',
			"friends_request": '{"friends_sync_token":"0"}',
			"max_video_height": "1280",
			"screen_height_in": "5.0"
		}

		return self.request("/loq/all_updates", auth_token=self.auth_token, data=data)
	
	# Get the friends list
	def friends(self):
		friends = []
		for friend in self.updates()['result'].get('friends_response', [])['friends']:
			friends.append(friend['name'])
		return friends

	# Get the requested list
	def requested(self):
		requests = []
		for request in self.updates()['result'].get('friends_response', [])['added_friends']:
			requests.append(request['name'])
		return requests

	# Create a media id
	def make_media_id(self, username):
		return '{username}~{uuid}'.format(username=username.upper(), uuid=str(uuid.uuid1()))

	# Get the media type
	def get_media_type(self, data):
		if is_video(data):
			return MEDIA_VIDEO
		if is_image(data):
			return MEDIA_IMAGE
		if is_zip(data):
			return MEDIA_VIDEO
		return None

	# Upload the media
	def upload(self, path, media_id):
		with open(path, 'rb') as f:
			data = f.read()

		media_type = self.get_media_type(data)

		params = {
			"zipped": "0",
			"media_id": media_id,
			"username": self.username,
			"type": media_type
		}

		return self.request("/bq/upload", auth_token=self.auth_token, data=params, files={'data': data})

	# Send a media to a story
	def send_to_story(self, path, time=5, media_type=0, thumbnail=None):
		media_id = self.make_media_id(self.username)

		self.upload(path, media_id)

		params = {
			"caption_text_display": "",
			"orientation": "0",
			"story_timestamp": self.now(),
			"time": time,
			"type": media_type,
			"username": self.username,
			"client_id": media_id,
			"media_id": media_id,
			"camera_front_facing": "0",
			"zipped": "0"
		}
		if thumbnail:
			return self.request("/bq/post_story", auth_token=self.auth_token, data=params, files={'thumbnail_data': open(thumbnail, 'rb')})
		else:
			return self.request("/bq/post_story", auth_token=self.auth_token, data=params)

	# Send a snap
	def send(self, path, recipients, time=5):
		media_id = self.make_media_id(self.username)

		self.upload(path, media_id)

		params = {
			"recipients": json.dumps(recipients),
			"orientation": 0,
			"recipient_ids": json.dumps(recipients),
			"time": time,
			"reply": 0,
			"username": self.username,
			"features_map": "{}",
			"media_id": media_id,
			"country_code": "US",
			"camera_front_facing": 0,
			"zipped": 0
		}

		return self.request("/loq/send", auth_token=self.auth_token, data=params)

	# Add a friend
	def add_friend(self, friend):
		params = {
			'action': 'add',
			'friend': friend,
			'username': self.username,
			'identity_profile_page': 'PROFILE_ADD_FRIENDS_BY_USERNAME_PAGE',
			'identity_cell_index': '0'
		}

		return self.request("/bq/friend", auth_token=self.auth_token, data=params)

	# Add a friend
	def add_friend(self, friend):
		params = {
			'action': 'add',
			'friend': friend,
			'username': self.username,
			'identity_profile_page': 'PROFILE_ADD_FRIENDS_BY_USERNAME_PAGE',
			'identity_cell_index': '0'
		}

		return self.request("/bq/friend", auth_token=self.auth_token, data=params)


	def delete_friend(self, friend):
		params = {
			'action': 'delete',
			'friend': friend,
			'username': self.username,
		}
		return self.request("/bq/friend", auth_token=self.auth_token, data=params)


	# Clear the feed given a user
	def clear_feed(self):
		params = {
			'username': self.username
		}

		return self.request('/loq/clear_feed', auth_token=self.auth_token, data=params)

	# Get the snaptag
	def get_snaptag(self):
		updates = self.updates()

		if updates['status'] == 200:
			qr_path = updates['result']['updates_response']['qr_path']
			params = {
				'image': qr_path,
				'username': self.username,
				'timestamp': self.now()
			}

			return self.request('/bq/snaptag_download', auth_token=self.auth_token, data=params)
		else:
			return updates

	# Check if the user exists
	def user_exists(self, username):
		params = {
			"request_username": username,
			"username": self.username
		}

		return self.request('/bq/user_exists', auth_token=self.auth_token, data=params)

	
	def update_privacy(self, privacy):
		params = {
			'username': self.username,
			'action': 'updatePrivacy',
			'privacySetting': privacy
		}

		return self.request('/ph/settings', auth_token=self.auth_token, data=params)

	def update_story_privacy(self, privacy):
		params = {
			'username': self.username,
			'action': 'updateStoryPrivacy',
			'privacySetting': privacy
		}

		return self.request('/ph/settings', auth_token=self.auth_token, data=params)

	def get_settings(self):
		params = {
			'username': self.username
		}

		return self.request('/ph/settings', auth_token=self.auth_token, data=params, post=False)

	def get_blob(self, snap_id):
		"""Get the image or video of a given snap
		Returns the image or a video of the given snap or None if
		data is invalid.

		:param snap_id: Snap id to fetch
		"""
		params = {
			'id': snap_id,
			'username': self.username
		}

		return self.request('/bq/blob', auth_token=self.auth_token, data=params)['result']

	def get_story_data(self, url, story_key, story_iv):
		r = requests.get(url, verify=False)

		return decrypt_story(r.content, story_key, story_iv)

	# Set the location of the iphone
	def set_location(self, latitude, longitude):
		params = {
			'lat': latitude,
			'long': longitude,
			'loc_accuracy_in_meters': 65.0,
			'checksums_dict': '{}',
			'username': self.username
		}

		return self.request('/loq/loc_data', auth_token=self.auth_token, data=params)

	# Get all the snaps
	def get_snaps(self):
		snaps = []
		conversations = self.updates()['result']['conversations_response'][:-1]

		for conversation in conversations:
			num_pending = len(conversation['pending_received_snaps'])
			for i in range(0, num_pending):
				snap = (_map_keys(conversation['pending_received_snaps'][i]))
				snaps.append(snap)

		return snaps

	# Send an event to a user
	def send_events(self, events, data=None):
		if data is None:
			data = {}

		params = {
			'events': json.dumps(events),
			'json': json.dumps(data),
			'username': self.username
		}
		return self.request('/bq/update_snaps', auth_token=self.auth_token, data=params)

	# Mark a snap video as viewed
	def mark_viewed(self, snap_id, view_duration=1):
		now = time.time() * 1000
		data = {snap_id: {u't': now, u'sv': view_duration}}
		events = [
			{
				u'eventName': u'SNAP_VIEW', u'params': {u'id': snap_id},
				u'ts': int(round(now)) - view_duration
			},
			{
				u'eventName': u'SNAP_EXPIRED', u'params': {u'id': snap_id},
				u'ts': int(round(now))
			}
		]
		return self.send_events(events, data)
