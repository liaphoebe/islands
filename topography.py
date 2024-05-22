# This is a component of an Island meant to represent the spatial arrangement of 
#   villages. This does not have a time concept, which the island does. This will
#   relate to the Island's Population with what is effectively a join table, where
#   an Individual.id relates to the id of a specific village. 
from orm import ORM

class Topography(metaclass=ORM):
	__relations__ = { 'island': 'Island' }

	def __init__(self):
		pass
