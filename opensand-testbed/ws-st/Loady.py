import requests
from bs4 import BeautifulSoup
import re
import urllib.parse
import sys
from time import time

"""
Loady comes from : https://github.com/donjajo/loady/blob/master/Loady.py

MIT License

Copyright (c) 2017 Jajo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

class Loady:
	files = {
		'js' : {},
		'css' : {}
	}

	def __init__( self, url, headers = {} ):
		if not isinstance( headers, dict ):
			raise ValueError( 'Headers argument must be dict instance' )

		self.url = url
		self.total_time = 0
		self.js = []
		self.css = []
		self.http_headers = headers
		self.soup = None
		self.size = 0

	def _get( self, tag ):
		"""Gets all site additional files and prepares their URL to be loaded"""

		# Get current URL data 
		domain_scheme, domain, _, _, _, _ = urllib.parse.urlparse( self.url )
		urls = []

		if tag is 'script':
			# Get all script tag with src attribute
			tags = self.soup.find_all( 'script', { 'src' : re.compile( r'.*' ) } )
		else:
			# Get all link tag with rel=stylesheet
			tags = self.soup.find_all( 'link', { 'rel' : 'stylesheet' } )

		for each_tag in tags:
			# Get the value of src or href
			val = each_tag[ 'src' ] if tag is 'script' else each_tag[ 'href' ]

			# parse the URL of the gotten URL
			url = urllib.parse.urlparse( val )

			if not url[ 0 ] and url[ 1 ]:
				# If URL has no scheme but has domain name, we assume it is a URL that supports HTTP(S). We just append the main site scheme to it
				urls.append( '{0}:{1}'.format( domain_scheme, val ) )
			elif not url[ 1 ]:
				# URL has no domain, its a relative path. Append the domain name to it
				urls.append( '{0}://{1}{2}'.format( domain_scheme, domain, val ) )
			else:
				# Its an absolute path, no issues bro!
				urls.append( val )

		if tag is 'script':
			self.js = urls
		else:
			self.css = urls

	def _load( self, t ):
		"""Load the gotten links, check for response time and size. Appends it to self.files object"""

		for link in ( self.js if t is 'script' else self.css ):
			# Lets start work!
			start = time()
			r = requests.get( link )
			end = time()

			# Calculate the total time taken to load link
			response_time = ( end - start )

			# Page loaded successfully
			if r.status_code == 200:
				# Get the size of page content
				size = sys.getsizeof( r.text )

				# Add results to self.files object
				self.files[ 'css' if t is 'style' else 'js' ][ link ] = { 'byte_size' : size, 'load_time' : response_time }

				# Sum up total time to the existing load time 
				self.total_time += response_time
				self.size += size

	def get( self ):
		"""Loads the main website, calculate response time, page size and get additional files in site"""

		start = time()
		r = requests.get( self.url, headers = self.http_headers )
		stop = time()
		if r.status_code == 200:
			response = r.text
			self.total_time = self.total_time + ( stop - start )
			self.size += sys.getsizeof( response )
			self.soup = BeautifulSoup( response, 'html.parser' )

			self._get( 'script' )
			self._get( 'style' )

			self._load( 'style' )
			self._load( 'script' )