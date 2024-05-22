class ORM(type):
	def relate(cls, obj):
		if obj is None:
			return cls

		try:
			setattr(cls, cls.relations_by_class[type(obj).__name__].pop(), obj)
		except KeyError:
			raise AttributeError(f"Object of type {type(obj)} not related to {type(cls)}")

		return cls

	def __new__(cls, what, bases=None, dict_=None):
		R = {}
		for rel_name, rel_class in dict_['__relations__'].items():
			try:
				R[rel_class].append(rel_name)
			except KeyError:
				R[rel_class] = [ rel_name ]

		dict_['relations_by_class'] = R
		dict_['belongs_to']         = cls.relate
		dict_['has_a']              = cls.relate

		return type.__new__(cls, what, bases, dict_)
