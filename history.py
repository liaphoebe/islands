from enum import Enum
import random
import matplotlib.pyplot as plt
import numpy as np
import scipy.stats as stats

class EventType(Enum):
	BIRTH, DEATH, PREG = range(3)

class Event:
	# Exact moment is the second when this event would occur. A random value is generated for a fallback.
	def __init__(self, type_, id_, year, exact_moment=None, **additional_values):
		self.type_ = type_
		self.id    = id_
		self.year  = year

		if type_ == EventType.BIRTH:
			assert 'sex' in additional_values
			self.sex   = additional_values['sex'] 

		self.value = exact_moment if exact_moment is not None else random.uniform(0,1) * 86400 * 365.25 # The number of seconds in a Julian year



class History:
	# TODO month offsets like what does it mean to be born in December? 
	def __init__(self, pop, y0):
		self.record = {}
		self.current_year  = y0
		self.starting_year = y0
		self.pop = pop
		if len(pop) > 0:
			self.initial_births()

	# This can be used to generate birth events for any members of a population (so, every individual that comes from a major event,
	#   which is to say every individual I'm using lol) that don't already have them. This won't generate duplicate birth events
	#   (or at least it shouldn't), so I'm just gonna be calling it after every major event with a population change.
	def initial_births(self):
		for i in self.pop:
			self.record_event(EventType.BIRTH, i.id, self.current_year - i.age)

	def run(self, runtime, verbose=False):
		# So the first iteration will be y0, and over the course of this year we'll see births and deaths. 
		#   Because deaths go by "aging in" to the next age range, the Population object kills individuals at years that
		#   are multiples of 5 of those individuals' ages. So like 20 kids will always die when they turn 5, for example. 
		#   And because this holds true for every single age range, we don't need to care about what specific age range a
		#   given person hit and just kill them in 1 of the 5 preceding years (current included).
		#
		# This loop looks like:
		#   1. Elapse the year
		#   2. Create records
		#   3. Increment the year count
		y0 = self.current_year 
		for yr in range(runtime):
			if verbose and (y0 + yr) % 50 == 0:
				print(f'{y0 + yr} {"CE" if y0 + yr >= 0 else "BCE"}\t{len(self.pop)}')
			results = self.pop.elapse_year()
			for person_id in results['deaths']:
				yod = y0 + random.randrange(yr - 4, yr) # Year of death
				self.record_event( EventType.DEATH, person_id, yod )
			for birth in results['births']:
				yob = y0 + random.randrange(yr - 4, yr) # Year of birth
				self.record_event( EventType.BIRTH, birth['id'], yob, sex=birth['sex'] )
			
			self.current_year += 1

		self.recorded_years  = len(self.record)
		self.recorded_events = sum(list(map(lambda key: len(self.record[key]), self.record.keys())))


	# Questions of timekeeping...
	#   the Samoan word for year is tausauga, although it originally meant season. (so, wet and dry)
	#   Pleiades called Mataalii (eyes of the chiefs)
	#   there's been evidence in tradition from other places of what marks the beginning of a year, but none from Samoa.
	#     starting with, in a way, palolo fishing (calculated to the very night without error) which was a great time to catch and share
	#     palolo
	#  
	#
	# Alright so check it out: I was never doing any binding of timekeeping to physical phenomena like the revolving/rotating of the earth
	#   or moon, which is usually what we approximate with lunisolar calendars (and other calendars of course).  So let's just say that
	#   every year recorded here is a Julian year, taken as 86400 seconds * 365.25 days exactly. When we go to run the simulation itself we'll start 
	#   at like 4000 BCE or whatever and let the celestial bodies move in the way they do, and after like 3000 Julian years minus however many
	#   to accommodate the entire vital record we'll just start running the history. So for now abstracting away celestial bodies.
	def record_event(self, event_type, iid, year, exact_moment=None, sex=None):
		ev = Event(event_type, iid, year, exact_moment=exact_moment, sex=sex)

		if year not in self.record:
			self.record[year] = {} 

		# Corner case of babies dying the year they're born, which feels like it could happen lol. 
		if ev.id not in self.record[year]: 
			self.record[year][ev.id] = [ev]
		else:
			self.record[year][ev.id].append(ev)

		# Anyone not born on the island (or I guess close enough to being on the island?) doesn't get an
		#   an associated pregnancy event. Probably help make that starting data for the "before times" 
		#   a little less goofy to deal with in the future. 
		if ev.type_ == EventType.BIRTH and ev.year > self.starting_year:
			# Comes from
			# http://hawaii.hawaii.edu/math/Courses/Math100/Chapter4/Notes/Exercises/Demo434.htm 
			PREGNANCY_LENGTH_MEAN = 266 #days
			PREGNANCY_LENGTH_SIGMA = 16 #days
			preg_value = stats.norm( loc = PREGNANCY_LENGTH_MEAN * 86400, scale = PREGNANCY_LENGTH_SIGMA * 86400 ).rvs()
			self.record_event(EventType.PREG, iid, year if ev.value - preg_value < 0 else year - 1, exact_moment=preg_value)
		

	def target_births(self, year):
		return len(list(filter(lambda key: self.record[year][key].type_ == EventType.BIRTH, self.record[year].keys())))

	def target_deaths(self, year):
		return len(list(filter(lambda key: self.record[year][key].type_ == EventType.DEATH, self.record[year].keys())))

	def growth_plot(self):
		years = list(self.record.keys())
		growth_rates = list(map(lambda year: self.target_births(year) - self.target_deaths(year), years))

		theta = np.polyfit(years, growth_rates, 1)
		y_line = theta[1] + theta[0] * np.array(years)

		plt.scatter(years, growth_rates)
		plt.plot(years, y_line, 'r')

		plt.show()

	# TODO these don't work yet
	def advance_population(self, by=1):
		self.reconstruct_population(self.current_year + by, mode='MODIFY')

	def rewind_population(self, by=1):
		self.reconstruct_population(self.current_year - by, mode='MODIFY')

	# This method attempts to answer the question "who was alive during a given (julian) year?"
	# In the current savai'i record, 1674 is when the pop most closely resembles sav pop in 2006. Cool! 
	def reconstruct_population(self, year, mode='NEW_POP'):
		from soc import Population, Individual, PopulationType

		def advance_to(pop, year):
			# The number of people alive during any given year is a function of
			#   who has been 'recently' born but hasn't yet died. 100 is a 
			#   nice round number that is also longer than I'm letting anyone
			#   actually live in this (for now anyway mua-ha-ha!).
			for i in range(year - 100, year + 1):
				for event_set in self.record[i].values():
					for event in event_set:
						if event.type_ == EventType.BIRTH:
							pop[event.id] = Individual(id=event.id, yob=event.year, pop=pop, sex=event.sex if hasattr(event, 'sex') else None)
						elif event.type_ == EventType.DEATH and pop[event.id] is not None:
							pop.kill(event.id)

			return pop

		def find_birth(event):
			for i in range(event.year - 100, event.year + 1):
				try:
					for e in self.record[i][event.id]:
						if e.type_ == EventType.BIRTH:
							return e
				except KeyError:
					pass

		# Currently to say we are moving to a year is more like to the end of that year when all is said and done. 
		match mode:
			case 'NEW_POP':
				pop = Population(mode=PopulationType.SIMULATED)
				advance_to(pop, year)
				self.pop = pop
			case 'MODIFY':
				import warnings
				warnings.warn('This does not work as expected right now. See comments and maybe don\'t use it :)') 
				# TODO this does not return the same result as if I just reconstructed the population for that year. 
				#   I might move on for now considering this is more a curiosity than anything else at this 
				#   point. 
				delta = year - self.current_year 
				if delta > 0:
					advance_to(self.pop, year)
				elif delta < 0:
					# The last thing we undo will be the year after our target year, 
					#   and the first thing we undo will be the current_year. 
					for i in reversed(range(year + 1, self.current_year + 1)):
						for event_set in self.record[i].values():
							for event in event_set:
								if event.type_ == EventType.BIRTH:
									self.pop.kill(event.id)
								elif event.type_ == EventType.DEATH:
									birth = find_birth(event)
									self.pop[event.id] = Individual(id=event.id, yob=birth.year, pop=self.pop, sex=birth.sex)


		for p in self.pop:
			p.set_age(year - p.yob) 
				
		self.current_year = year

