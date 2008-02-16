"""
This class handles conversions to and from CMDBuild's own JSON format.

During encoding, lists are converted to "collections", and basic types
to a dictionary explicitly declaring the base type itself.

This may be extended in the future to talk more precisely to CMDBuild,
once the need arises and the format is decoded.
"""

class Bean(object):
	"""
	Encapsulates objects to be recognised by CMDBuild's deserializer.
	"""
	def __init__(self, **kwargs):
		self._map = dict(**kwargs)
	def json_map(self):
		"""
		Advertises the bean's original class and returns the property dictionary
		"""
		serializable_map = self._map.copy()
		if hasattr(self, 'original_class'):
			serializable_map['json.converter.original.class'] = self.original_class
		return serializable_map

class AssetBean(Bean):
	original_class = 'cmdbuild.collection.AssetBean'

class ServerException(Exception):
	def __init__(self, e):
		if not 'JSONConverter.exception' in e:
			raise TypeError, '%s must be initialized with proper ' \
				'JSON-decoded response' % self.__class__.__name__
		self.exc = e
		super(ServerException, self).__init__(self._get_msg())
	def _get_msg(self):
		msg = ['Server-side exception: "%s" in class %s' % (
			self.exc['exception.message'],
			self.exc['exception.original.class'])]
		msg.extend(['%s.%s() in %s:%s' % (l['class.name'], 
			l['method.name'], l['file.name'],
			l['line.number']) for l in self.exc['stacktrace']])
		return "\n".join(msg)

def decorate(obj):
	"""
	Turns an object into a JSONConverter-palatable form *before* serialization.
	"""
	def add_type(obj, converter_type):
		"Converts a value into a map"
		return { 'json.converter.original.class': converter_type,
			'JSONConverter.value': obj }
	
	if hasattr(obj, 'json_map'):
		return obj.json_map()
	elif isinstance(obj, int):
		return add_type(obj, 'java.lang.Integer')
	elif isinstance(obj, basestring):
		return add_type(obj, 'java.lang.String')
	elif isinstance(obj, bool):
		return add_type(obj, 'java.lang.Boolean')
	elif isinstance(obj, (list, tuple)):
		conv_objs = [decorate(o) for o in obj]
		return {'JSONConverter.iscollection':
			True, 'JSONConverter.collection': conv_objs }
	elif isinstance(obj, dict):
		d = dict([(k, decorate(v)) for k,v in obj.items()])
		d['JSONConverter.map'] = True
		return d
	raise TypeError, 'Cannot serialize type %s (content: %s)' \
		% (type(obj), obj)

def clean_attributes(obj):
	"""
	Inside a dictionary, find all items with a NULL value and delete them.
	"""
	for name, value in obj.items():
		if value == 'json.converter.null':
			del obj[name]
	return obj

def strip(obj):
	"""
	Take CMDBuild's conversion output and strip it of its Java boring details;
	duck typing will do, for us.
	"""
	# Case 1: collection
	if 'JSONConverter.iscollection' in obj:
		return [strip(item) for item in obj['JSONConverter.collection']]
	if 'JSONConverter.map' in obj:
		del obj['JSONConverter.map']
		return dict([(k, strip(v)) for k,v in obj.items()])
	# Case 2: encoded class
	try:
		original_class = obj['json.converter.original.class']
		del obj['json.converter.original.class']
	except KeyError:
		original_class = None
	if original_class:
		# Act according to the class type
		if original_class in ('java.lang.String', 'java.lang.Boolean'):
			return obj['JSONConverter.value']
		elif original_class in ('cmdbuild.collection.LookupBean',):
			return clean_attributes(obj)
		raise TypeError, "Cannot decode original class %s "\
			"(content: '%s')" % (original_class, obj)
	# Server exceptions
	if 'JSONConverter.exception' in obj:
		return ServerException(obj)
	# Last case: anything else
	raise TypeError, 'Cannot decode %s' % obj

def as_string(value):
	"""
	Converts a Python value into a string suitable for SQL-like representation.
	"""
	if value is False:
		return "false"
	elif value is True:
		return "true"
	elif value is None:
		return ""
	elif isinstance(value, int):
		return "%s" % value
	elif isinstance(value, basestring):
		return value
	else:
		raise TypeError, "Can't convert data of type %s" % type(value)
