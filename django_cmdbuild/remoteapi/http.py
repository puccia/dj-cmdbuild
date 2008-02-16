"""
CMDBuild relies on the Shark workflow engine.  Each instance of the
Activity class, or one of its subclasses, represents a workflow process.
Therefore, CMDBuild needs to synchronize its own data model with the
engine's.  Interaction between the two takes place in these ways:

From CMDBuild to Shark
----------------------

1. The user alters a card for an Activity instance
#. CMDBuild stores the database change and invokes the Shark engine
#. Shark knows the new data and acts accordingly

From Shark to CMDBuild
----------------------

1. The XPDL workflow schema calls for CMDBuild-side actions, e.g.
changing an attribute's value, or advancing a process
#. Shark reads the XPDL file and notices that there is a "tool"
invoking a CMDBuild action
#. Shark calls a Java method that handles interaction with CMDBuild
#. The method prepares the data with JSON and calls the remote API
servlet
#. The servlet reads the data
#. The servlet changes the card and, in turns, invokes Shark as needed
(see above)
"""

import httplib
from cStringIO import StringIO

from django.utils import simplejson as json
from django_cmdbuild.serializer.jsonconverter import decorate, strip, ServerException

class Remote(object):
	class EmptyResponse(Exception):
		pass
	class GenericApplicationFailure(Exception):
		pass
	"""
	This class handles a remote connection towards CMDBuild's engine.
	"""
	def __init__(self, url=None):
		"""
		Prepare the connection object and connect to the server
		"""
		if url is None:
			from django.conf import settings
			url = settings.CMDBUILD_REMOTEAPI_URL
		self.proto, siteurl = url.split('://', 1)
		self.host, self.url = siteurl.split('/', 1)
		self.url = '/' + self.url
		self.conn = httplib.HTTPConnection(self.host)
		self.conn.connect()
		print self.conn, self.host, self.url

	def request(self, command, data):
		"""
		Encode the data in CMDBuild's JSON dialect and send the command,
		then return the decoded response
		"""
		self.conn.request('POST', self.url, json.dumps(decorate(data)), {
			'Content-Type': 'text/plain',
			'command': command
			})
		answer = self.conn.getresponse().read()
		if answer.isspace():
			raise self.EmptyResponse
		data = strip(json.loads(answer))
		if isinstance(data, ServerException):
			raise data
		return data