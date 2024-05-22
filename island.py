from parameter import Parameter
from history import History
from soc import Population

# One of these modifies the way a Population grows.
class MajorEvent:
	def __init__(self, name, type_, parameters, curve=None, verbose=False):
		self.name = name
		self.type_ = type_

		if verbose:
			print(f'\t{self.name}')

		self.params = { p.type_: p for p in [ Parameter(**param, verbose=verbose) for param in parameters ] }
		if self.year.value is not None and self.year.value < 0:
			self.reroll_year()
		self.reset_dependency_check()
		# This will let you fit population change to a curve. More on that in soc.py!
		self.curve = curve

	def __repr__(self):
		return self.name

	def __lt__(self, other):
		return self.year < other.year

	@property
	def year(self):
		return self.params['Year']

	@year.setter
	def year(self, value):
		self.params['Year'] = value

	@property
	def population_change(self):
		try:
			return self.params['Population Change']
		except KeyError:
			return None

	def reset_dependency_check(self):
		self.has_unresolved_dependency = self.year.follow is not None

	def reroll_year(self):
		self.year.roll()

	def reroll_growth_rate(self):
		self.params['Growth Rate'].roll() 
			

import uuid
from multiprocessing import Process
from topography import Topography

class Island(Process):

	THIS_YEAR = 2020 # CE
	END_YEAR  = 1866 # CE

	def __init__(self, name, events={}, verbose=False):
		super(Island, self).__init__()
		self.id = str( uuid.uuid4() )
		self.name = name
		if verbose:
			print(f'{self.name} parameters:')
		self.events = { e.name: e for e in [ MajorEvent(**event, verbose=verbose) for event in events ] }

		#self.topo = Topography().belongs_to(self)  

	def __repr__(self):
		return self.name

	@property
	def major_events(self):
		return self.events.values()

	@property
	def vital_record(self):
		return self.history.record

	def run(self):
		# 1. Redirect stdout for logging
		import sys
		sys.stdout = open(f'logs/{self.name}', 'w') 
		
		# 2. Load history
		match self.history_mode:
			case 'IMPORT':
				self.import_vital_record()
			case 'GENERATE': 
				self.history_preflight(verbose=True)
		
		self.server.send(f'{self.name} has {len(self.vital_record)} years to playback') 

	def bind_multiprocessing_communication_channels(self, **kwargs):
		for key, value in kwargs.items():
			setattr(self, key, value)

	# So testing runs a little faster, hopefully!
	def export_vital_record(self):
		import csv
		from history import EventType
		with open(f'histories/{self.name}.csv', 'w') as f:
			writer = csv.writer(f)

			header = ['year', 'person_id', 'type', 'exact_moment', 'sex (if applicable)']
			writer.writerow(header)
			for year, event_dict in self.vital_record.items():
				for person_id, events in event_dict.items():
					for event in events:
						writer.writerow([year, person_id, f'{event.type_.name}-{event.type_.value}', event.value, event.sex if event.type_ == EventType.BIRTH else ''])

	def import_vital_record(self, starting_year=-1000):
		import csv
		from history import Event, EventType
		with open(f'histories/{self.name}.csv', 'r') as f:
			reader = csv.DictReader(f)
			out = {} 
			for row in reader:
				year = int(row['year'])
				if year not in out:
					out[year] = {}

				person_id = row['person_id']
				if person_id not in out[year]:
					out[year][person_id] = []  

				_, type_id = row['type'].split('-')
				sex = row['sex (if applicable)']
				out[year][person_id].append( Event( EventType( int( type_id ) ), person_id, year, exact_moment=float( row['exact_moment'] ), sex=int(sex) if sex != '' else None ) )

			self.history = History(Population(0), starting_year) 
			self.history.record = out

	def history_preflight(self, starting_year=-1000, verbose=False): # 1000 BCE start by default
		def actual_year(year):
			if year.unit == "CE":
				return year.value
			return self.THIS_YEAR - year.convert("years ago")

		# This population is a concept I'm using to do the history run, where we're
		#   assuming no one will ever immigrate or emigrate. When we go to do the
		#   real run we'll be able to say e.g. we want a baby from Upolu, so pick
		#   a mother from Upolu and impregnate her, and classify that baby as from
		#   Upolu.  That way individuals can match the ones we create a record
		#   for here, and we can track actual ethnic makeup of people separately.
		history = History(Population(0), starting_year)
		pop = history.pop 

		timeline_dict = { actual_year(ev.year): ev for ev in self.major_events }
		timeline_dict[ starting_year ] = None
		timeline_dict[ self.END_YEAR ] = None
		timeline = list(timeline_dict.keys())
		timeline.sort()

		# timeline_dict = { 1000 BCE: None, 0 CE: Event-1, blah }
		# timeline = [ 1000 BCE, 0 CE, ... ]
		for i in range(len(timeline) - 1):
			lower = timeline[i]
			upper = timeline[i + 1]
			ev = timeline_dict[ timeline[i] ]
			if verbose and ev is not None:
				print(f'{ev} occurring {ev.year}')
			if ev is not None:
				pop.apply(ev)
				if ev.population_change is not None:
					history.initial_births()
			history.run( int(upper - lower), verbose=verbose )

		self.history = history
		
