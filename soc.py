# Society Organization Concepts aka SOC

import random
import math
import numpy
import os
import uuid
from enum import Enum
import warnings

class Individual:
	
	# 0 == female, 1 == male
	def __init__(self, age=0, sex=0, id=None, yob=None, pop=None):
		self.age = age
		self.sex = sex
		self.id  = uuid.uuid4() if id is None else id
		self.yob = yob

		# Relations
		self.pop = pop

	def __str__(self):
		return f'{self.age} year old {"male" if self.sex == 1 else "female"}'

	def is_male(self):
		return self.sex == 1

	def is_female(self):
		return self.sex == 0

	def regen_id(self):
		self.id = uuid.uuid4()

	# Let's say that the islanders had an active interest in population control as part of their
	#  relationship with the land. They did not want to over-populate, and to that end they attempted
	#  to restrict birth rates. Hm...this is how far I've gotten.
	#
	# It's kind of astounding, looking at the graph of old population growth from 100 generations ago to 50 generations ago. 
	#   The population here rose from 1000 people to 3200 people-ish, which is a growth rate of 1.5 people per year or 
	#   3 people per two years. It really feels like pregnancies would've been something very intentional, and the
	#   unintentional ones were likely aborted or eventually infanticide-ed.  
	def eval_maternity(self):
		pass

	def set_age(self, age):
		old_age = self.age
		self.age = age
		if self.pop is not None:
			self.pop.validate_age_range(self, old_age)

	def grow(self, by=1):
		if self.is_female():
			self.eval_maternity()
		old_age = self.age
		self.age += by

		if self.pop is not None:
			self.pop.validate_age_range(self, old_age)

class AgeRange:

	# These defaults are for the 0-4 age range on the Mali 2017 demographic chart. The primary assumption here is that developing countries always look like this. 
	def __init__(self, population, range=(0,4), proportion=(9.2, 8.9)):
		self.min_age, self.max_age = range

		# Male rate and female rate in %
		self.mr, self.fr = proportion

		# RELATIONSHIP
		self.population = population

		# Survival Rates
		#
		# The intuition here is that the population will still be 'developing' for the entire time period
		#   we care about. So 12% of boys always won't make it to 5 years old, for example.
		if self.min_age != 0: 
			self.female_sr = self.fr / self.population.P[ self.min_age - 1 ].fr
			self.male_sr   = self.mr / self.population.P[ self.min_age - 1 ].mr

		# Death Remainders
		#
		# There's no guarantee that a certain 'death' fraction (so that's how many of a set of e.g. girls aging into a new age range will die then and there) 
		#   will be a whole number, which it needs to be since I can't kill half a person. Death remainders kill an extra person everytime it's >= 1. 
		#   It's like a leap year!
		self.fdr = 0.0
		self.mdr = 0.0		

		# Population set for this age range
		match self.mode:
			case PopulationType.HISTORICAL:
				self.set_historical_mode()
			case PopulationType.SIMULATED:
				self.set_simulated_mode()

	def __getitem__(self, key):
		assert self.mode == PopulationType.SIMULATED
		return self.P[key]

	def __setitem__(self, key, newvalue):
		assert self.mode == PopulationType.SIMULATED
		self.P[key] = newvalue

	def __delitem__(self, key):
		assert self.mode == PopulationType.SIMULATED
		del self.P[key]

	@property
	def mode(self):
		return self.population.mode

	@property
	def people(self):
		match self.mode:
			case PopulationType.HISTORICAL:
				return self.P
			case PopulationType.SIMULATED:
				return list(self.P.values())

	def set_historical_mode(self):
		self.P = []
		self.dead_P = []

	def set_simulated_mode(self):
		self.P = {}
		self.dead_P = {}

	def new_individual(self, birth=True):
		new_p = Individual( age = 0 if birth else random.randint( self.min_age, self.max_age ), sex = 0 if random.uniform( -1 * self.mr, self.fr ) < 0 else 1 ) 
		self.P.append(new_p)
		return new_p

	def append(self, p):
		if type(p) != Individual:
			raise TypeError(f'{type(self)} can only append objects of type Individual')

		match self.mode:
			case PopulationType.HISTORICAL:
				self.P.append(p)
			case PopulationType.SIMULATED:
				self.P[p.id] = p

	# Every year, an unknown amount of the population ages into the next age range, at which point we determine who survives entering the next
	#   age range. It's a fun abstraction, but I'd like to improve on this.
	#
	# Instead I want to do something like a preview. I'll write about it more down in the Population class. 
	def age_in(self, new_P, verbose=False):
		females = [ p for p in new_P if p.is_female() ]
		males   = list( set(new_P) - set(females) )

		if verbose:
			print(f'{len(females)} females and {len(males)} males aging in')

		immunity_idol_eqn = lambda p_set, survival_rate: math.modf( len(p_set) * survival_rate )

		female_remainder, female_idols = immunity_idol_eqn(females, self.female_sr)
		male_remainder,   male_idols   = immunity_idol_eqn(males,   self.male_sr  )

		self.fdr += female_remainder
		self.mdr += male_remainder

		if self.fdr >= 1:
			self.fdr     -= 1
			female_idols += 1

		if self.mdr >= 1:
			self.mdr   -= 1
			male_idols += 1

		if verbose:
			print(f'{female_idols} females and {male_idols} males survive')
			death_count = 0

		# From here on, I shouldn't have to differentiate between M/F for the code itself
		for segregated_P in [ zip(females, self.idol_set( female_idols, len(females) ) ), zip(males, self.idol_set( male_idols, len(males) ) ) ]:
			for tuple in segregated_P:
				person = tuple[0]
				if tuple[1] == 1:
					self.append( person )
				else:
					self.dead_P.append( person )

					if verbose:
						print(f'{person} died')
						death_count += 1

		if verbose:
			print(f'{death_count} deaths') 
				

	# 1 means you live, 0 means you die
	def idol_set(self, idol_count, p_len):
		idols = numpy.zeros(p_len)
		idols[:int(idol_count)] = 1
		numpy.random.shuffle(idols)
		return idols

	def reap(self):
		output = self.dead_P
		self.dead_P = []
		return output

	def elapse_year(self, verbose=False):
		if len(self.P) == 0:
			return

		for person in self.P:
			person.grow()
			
		age_out = [ p for p in self.P if p.age > self.max_age ]
		self.P = list( set(self.P) - set(age_out) )
		self.population.P[ self.max_age + 1].age_in( age_out, verbose=verbose )
		

	def __lt__(self, other):
		return self.max_age < other.max_age

	def by_sex(self):
		f_sz = len( [i for i in self.people if i.is_female()] )
		return f'{ f_sz } females and { len(self.P) - f_sz } males in { self }'

	def __str__(self, verbose=False):
		if verbose:
			return f'{ len(self.P) } aged { self.min_age } - { self.max_age } representing { self.mr + self.fr }% of the total population'
		else:
			return f'<AgeRange { self.min_age } - { self.max_age } at { hex(id(self)) }>'

	def __iter__(self):
		return AgeRangeIterator(self)

	# DEPRECATED
	# Number of people in this age range is greater than or equal to the total portion of the population that fits here
	def isFull(self, theoretical=None):
		return len(self.P) >= ( self.mr + self.fr ) / 100 * (theoretical if theoretical is not None else population.get_size())

class PopulationType(Enum):
	HISTORICAL, SIMULATED = range(2)

class Population:

	# default demography table
	# Each entry is structured as
	#   (age_floor, age_ceiling): (male_%, female_%)
	ddt = {
		(0,4)  : (9.2, 8.9),
		(5,9)  : (8.1, 7.8),
		(10,14): (6.8, 6.5),
		(15,19): (5.5, 5.2),
		(20,24): (4.4, 4.2),
		(25,29): (3.6, 3.5),
		(30,34): (3.0, 2.9),
		(35,39): (2.6, 2.5),
		(40,44): (2.1, 2.0),
		(45,49): (1.5, 1.6),
		(50,54): (1.1, 1.2),
		(55,59): (0.8, 0.9),
		(60,64): (0.7, 0.8),
		(65,69): (0.5, 0.6),
		(70,74): (0.3, 0.4),
		(75,79): (0.2, 0.2),
		(80,84): (0.1, 0.1),
		(85,1e5): (0.0, 0.0)
	}

	# I think this is really emblematic of what I'm describing as cultural upheaval over the course
	# of 17 generations, or roughtly 500 years (510), between 50 generations ago when I'm saying an additional wave
	# of immigrants arrived via the Caroline islands and settled on Savaii, and 33 generations ago when 
	# widespread surface modification began and the population skyrocketed. The graph I'm using I think puts the bottleneck too early 
	# on the line, because on the graph the bottleneck starts around 20-ish generations ago which is way too early since Savaii for
	# example would supposedly go from like 70000 people down to 16,000-ish, which would be a 75% population reduction 
	# (or thereabouts) and I just am skeptical that that came from anything except for disease from 
	# the Europeans. 
	#
	# So we're gonna say that population growth got big from like 33 generations ago to 10 generations ago. It's
	# weird that Upolu has the urban centers but Savaii like explodes in population size to almost double
	# Upolu. Maybe the thing about urban centers changed? 
	#
	# Savaii tops out at 63095 people and Upolu at 31622.
	# The population recovery started 1842. Give it 100 years of crash time and that puts us at 1742 or like 8.5
	# generations ago. So I want my spike to go from 33 generations to 8.5 generations, which is 735 years of spike time.
	#
	# So from 985 BCE (100 generations) to 522 CE (50 generations) remains relatively constant (may want more granularity here),
	# then let's say a pulse from Micronesia of like 100-200 people hits Savaii, and the population influx means maybe some disease
	# and emigration. 
	#
	# Shorelines have been progradating for awhile, the new people and the urban centers on Upolu lead to some stress. People abandon
	# pottery, chiefdoms emerge, and 1032 CE is when widespread agriculture begins, populations skyrocket, agriculture makes it to 
	# Upolu, the other islands, and population pulses from various islands of the archipelago (and elsewhere) 
	# start to migrate east. 
	#
	# Looks like carrying capacity for both islands was 3981 people. Savaii hits that 372 CE and Upolu at 1032 CE when agriculture is 
	# introduced. Which is to say that Upolu never really hits their carry cap. 
	#
	# Upolu looks like it logarithmically continues up to 4000 with the original growth rate, and Savaii dips to 2239 people by 972 CE. So let's say people arrived 
	# 50 generations ago, 522 CE, and recovers 1032 CE. 
	#
	# Logarithmic growth for both here with a K = 4000. And let's say that Savaii actually has 200 people fewer to account for the new people from 
	# Micronesia. This might change if it's not enough admixing at this initial pulse size but fine for now. 
	# Savaii also has a slightly larger initial growth rate than upolu. Savaii does 708 people to 3781 from 985 BCE - 522 CE = 2.04 new people per year
	# Upolu initial: 1000 people to 3981 from 985 BCE - 1032 CE = 1.48 new people per year.
	#
	# Savaii 522 CE - 972 CE: 3981 down to 2239 = 3.87 fewer people per year
	#
	# Spiketime: pretty rough estimate on Upolu just to account for its population hitting its max later than Savaii's.  Stupid graph.
	# Savaii 972 CE - 1742 CE: 2239 people up to 63095 = 79 new people per year holy crap
	# Upolu 1032 CE - 1800 CE: 3981 people up to 31622 = 36 new people per year
	# GROWTH_RATE = 1.5 # new people per year 

	# ATTEMPT #2
	#   I want a few key events that can vary in timing and also not vary in timing.  Gonna do that elsewhere though... 
	

	def __init__(self, target_sz=0, verbose=False, growth_rate=0, carry_cap=-1, mode=PopulationType.HISTORICAL):
		# Here we're working to make every age of an age range collide with every other age of that range. So, 0 1 2 3 and 4 all point to one object. 
		self.P = {}
		self.mode = mode
		for age_bracket in self.ddt.keys():
			self.P.update(dict.fromkeys( list( range( age_bracket[0], int(age_bracket[1]) + 1 )), AgeRange(self, age_bracket, self.ddt[age_bracket]) ))

		self.age_ranges = list(set(self.P.values()))
		self.age_ranges.sort(reverse=True)

		for ar in self.age_ranges:
			portion = math.floor(target_sz * (ar.mr + ar.fr) / 100 )
			if verbose:
				print( f'Allocating {portion} to {ar}' )
			for i in range(portion):
				ar.new_individual(birth=False)

		print( f'Generated population of { len(self) }' )
		if verbose:
			print(self)

		match self.mode:
			case PopulationType.HISTORICAL:
				# Birth Remainder. It's like death remainder. 
				self.br = 0.0

				self.growth_rate = growth_rate
				self.carry_cap   = carry_cap
				# Number of years of growth with the same growth rate and/or carry capacity. Resets in apply.
				self.year        = 0
			case PopulationType.SIMULATED:
				pass	

	def __getitem__(self, key):
		assert self.mode == PopulationType.SIMULATED

		for ar in self.age_ranges:
			try:
				return ar[key]
			except KeyError:
				pass

		return None

	def __setitem__(self, pid, person):
		assert self.mode == PopulationType.SIMULATED

		self.P[person.age][pid] = person

	def __len__(self):
		return sum( map( lambda ar: len( ar.P ), self.age_ranges ) )

	def __str__(self):
		return f'{os.linesep.join( [ ar.by_sex() for ar in self.age_ranges ] ) }'

	def __iter__(self):
		return PopulationIterator(self)

	def __iadd__(self, other):
		if type(other) == list:
			for p in other:
				self.P[p.age].append(p)
		elif type(other) == Individual:
			self.P[other.age].append(other) 

		return self

	def __contains__(self, p):
		match self.mode:
			case PopulationType.HISTORICAL:
				# I have not tested this!
				return p in iter(self)
			case PopulationType.SIMULATED:
				return self[p.id] is not None

	def set_historical(self):
		self.set_mode(PopulationType.HISTORICAL)

	def set_simulated(self):
		self.set_mode(PopulationType.SIMULATED) 

	def set_mode(self, mode):
		if mode == self.mode:
			return

		warnings.warn('WARNING: set_mode currently erases all extant population data')

		match mode:
			case PopulationType.HISTORICAL:
				self.mode = PopulationType.HISTORICAL
				for ar in self.age_ranges:
					ar.set_historical_mode()
			case PopulationType.SIMULATED:
				self.mode = PopulationType.SIMULATED
				for ar in self.age_ranges:
					ar.set_simulated_mode()

	def kill(self, pid):
		assert self.mode == PopulationType.SIMULATED
		assert self[pid] is not None

		for ar in self.age_ranges:
			try:
				person = ar[pid]
				del ar[pid]
				return person
			except KeyError:
				pass

	# Re-place a person in their appropriate age range, if they've aged
	def validate_age_range(self, person, old_age):
		if self.P[old_age] == self.P[person.age]:
			return

		del self.P[old_age][person.id]
		self.P[person.age][person.id] = person

	# This is a real meat and potatoes kind of function!
	# An event has 4 possible parameters: carry capacity change, population change, growth rate change, year
	#   carry_cap change: just gonna set this as a property. Currently nonfunctional
	#   population change: create a temp population and just add it to this one.
	#   growth rate change: if an event lacks the 'curve' property, this just sets the property. But if it has the curve property,
	#     we want to set up a function which will fit population size at year t to a curve.
	def apply(self, event, curve=None):
		try:
			event.params['Population Change'].convert('raw')
		except KeyError:
			pass

		event.params['Growth Rate'].convert('raw / year')

		self.year = 0

		#if event.name == "Agriculture Start":
		#	self.trace = True

		for param in event.params.values():
			match param.type_:
				case 'Year':
					pass
				case 'Carry Capacity':
					self.carry_cap = param.value
				case 'Population Change':
					tmp_pop = Population( event.params['Population Change'].value )
					self   += tmp_pop
				case 'Growth Rate':
					self.growth_rate = param.value

					match event.curve:
						case 'square root':
							# Linear function
							assert hasattr(event.params['Growth Rate'], 'measured_time')
							time = event.params['Growth Rate'].measured_time
							b    = event.params['Population Change'].value
							line = lambda x: self.growth_rate * x + b

							# Nonlinear fit
							m    = ( line(time) - b ) / ( time**0.5 ) 
							self.population_curve = lambda x: m * (x**0.5) + b

						case 'logistic':
							# Linear function
							assert hasattr(event.params['Growth Rate'], 'measured_time')
							time = event.params['Growth Rate'].measured_time
							b = len(self)
							line = lambda x: self.growth_rate * x + b

							# Nonlinear fit
							A  = (self.carry_cap - b) / b
							m  = self.carry_cap / line(time) - 1
							m /= A
							m  = math.log(m)
							m /= -1 * time

							self.population_curve = lambda x: self.carry_cap / (1 + A * ( math.e**( -1 * m * x ) ) )
							

	@property
	def growth(self):
		if hasattr(self, "population_curve"):
			return self.population_curve(self.year) 
		else:
			return self.growth_rate + len(self)

	def flattened_P(self):
		return [individual for age_range in self.age_ranges for individual in age_range]
		#match self.mode:
		#	case PopulationType.HISTORICAL:
		#		return [individual for age_range in self.age_ranges for individual in age_range]
		#	case PopulationType.SIMULATED:
		#		return [individual for age_range in self.age_ranges for individual in age_range.values()]

	def print_statistics(self):
		for ar in self.age_ranges:
			print(ar.by_sex())

	# For the luls
	def elapse_years(self, count):
		for _ in range(count):
			self.elapse_year()

	# I want this to return a hash that looks like:
	# { births: [ { id: person.id, sex: person.sex }... ], deaths: [] } 
	def elapse_year(self, verbose=False):
		self.year += 1
		# We do this up here because the death block modifies the population in-place, so len(self) changes.
		new_people = self.growth - len(self) 

		if hasattr(self, 'trace') and self.trace:
			print(f'{self.year}: {new_people}')

		# Death Block
		cemetery = []

		for ar in self.age_ranges:
			if verbose:
				print(f'Growing {ar}')
			ar.elapse_year(verbose=verbose)

		# We accumulate all the dead people in a separate loop bc each iteration above piles dead bodies in the next age range up
		#   but we process in reverse order so we never actually see the bodies. Oops! 
		for ar in self.age_ranges:
			cemetery += ar.reap()

		if verbose:
			print(f'{len(cemetery)} deaths')

		# Birth Block
		births   = len(cemetery)
		self.br += new_people
	
		self.br, extra = math.modf(self.br)
		births += int(extra)	
	
		baby_ar = self.age_ranges[-1]
		birth_data = []
		for _ in range(births):
			baby = baby_ar.new_individual()
			birth_data.append( { 'id': baby.id, 'sex': baby.sex } )

		return { 'births': birth_data, 'deaths': [ p.id for p in cemetery ] }

	# DEPRECATED
	def oldest_available_age(self, target_size):
		for ar in self.age_ranges:
			if not ar.isFull(theoretical=target_size):
				return random.randint( ar.min_age, ar.max_age )
	

class PopulationIterator:
	def __init__(self, pop):
		self._pop = pop.flattened_P()
		self._index = 0

	def __next__(self):
		if self._index < len( self._pop ):
			result = self._pop[ self._index ]
			self._index += 1
			return result
		raise StopIteration

class AgeRangeIterator:
	def __init__(self, ar):
		self._ar = ar.people
		self._index = 0
	
	def __next__(self):
		if self._index < len( self._ar ):
			result = self._ar[ self._index ]
			self._index += 1
			return result
		raise StopIteration
	
# DEPRECATED	
class Pulse:
	# Some params:
	#  sz: Population size of pulse
	#  yr: Year of pulse
	#  mf_t: Male-female tuple e.g. 5 men for every woman
	#
	# mf_t == (1.05, 1) represents the current global average. Could consider changing this default if you want. 
	def __init__(self, sz=0, yr=0, mf_t=(1.05,1)):
		male_rate, female_rate = mf_t
		self.women = math.ceil( female_rate * sz / ( female_rate + male_rate ) )
		self.men = sz - self.women

		self.yr = yr

	def pop(self):
		return self.men + self.women

	def oldest_available_age_slot(self):
		pass


