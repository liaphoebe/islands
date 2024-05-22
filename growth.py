from multiprocessing import Process, Manager, Queue, Pipe, Event
from pickle import UnpicklingError
import sys
import os
import uuid
import matplotlib.pyplot as plt
import math
import random
import argparse

#Remember this is exponential! There are no limiting factors here like space which would
# modify what happened in say Tahiti

#todo "sudden" immigration/emigration
#population limits by island size
#generational data
#food calculator 

# What a funny thing, huh? It's a lot like you to step this far back and not want to abstract that much lol. 
# They will not have names until they name each other! Goofball.
class Individual:
	
	def __init__(self, age=0):
		self.age = age

	def age(self, by=1):
		self.age += by

	# This will matter for initially populating a pulse. 
	def float(self, pulse):
		pass

class AgeRange:

	# These defaults are for the 0-4 age range on the Mali 2017 demographic chart. The primary assumption here is that developing countries always look like this. 
	def __init__(self, population, range=(0,4), proportion=(9.2, 8.9) ):
		self.min_age, self.max_age = range

		# Male rate and female rate in %
		self.mr, self.fr = proportion

		# Population set for this age range
		self.P = []

		# RELATIONSHIP
		self.population = population

	def __iadd__(self, p):
		if type(p) != Individual:
			raise TypeError(f'{type(self) can only append objects of type Individual')
		self.P.append(p)

	# Number of people in this age range is greater than or equal to the total portion of the population that fits here
	def isFull(self, theoretical=None):
		return len(self.P) >= ( self.mr + self.fr ) / 100 * (theoretical if theoretical is not None else population.get_size())


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
	
	def __init__(self, initial_sz=0):
		self.P = {}
		for age_bracket in ddt.keys():
			self.P.update(dict.fromkeys( list( range( age_bracket[0], age_bracket[1] + 1 )), AgeRange(self, age_bracket, self.P[age_bracket]) ))

		self.age_ranges = list(set(self.P.values()))
		# Set this to True so it's faster to access the smallest brackets during the float operation
		self.age_ranges.sort(reverse=True)

		for i in range(initial_sz):
			my_age = self.oldest_available_age()
			self.P[ my_age ] += Individual( my_age )
	
	def oldest_available_age(self, target_size):
		for ar in self.age_ranges:
			if not ar.isFull(theoretical=target_size):
				return random.randint( ar.min_age, ar.max_age )
	
				
		
 
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



new_zealand = {
	"name": "Aotearoa",
	"gr" : .0143,
	"K": 1e6,
	"pulses" : [
		Pulse(sz=200, yr=1320)
	]
}

upolu = {
	"name": "Upolu",
	"gr": .0063,
	"K": 1e5,
	"pulses": [
		Pulse(sz=974, yr=-978)
	]
}

upolu_2 = {
	"name": "Upolu",
	"gr": 0
}

# in two waves? 1219-1266
# origin year of 1060 is uh, disputable
hawaii_1450 = {
	"pop": 200,
	"gr": .015,
	"year": 1060,
	"pulse": 100,
	"pulse_period": 30
}

pop = 200
gr = .018
year = -1000
pulse = 100
pulse_period = 30

### CONSTANTS
t0 = year
initial_island_config = [
	new_zealand,
	upolu
]

class Message:
	def __init__(self, cmd, **kwargs):
		self.cmd = cmd
		self.kwargs = kwargs
		for key, value in kwargs.items():
			setattr(self, key, value)

	def __str__(self):
		return f'{self.cmd}: {str(self.kwargs)}'
		

class Island(Process):

	def __init__(self, **kwargs):
		super(Island, self).__init__()
		self.id = str( uuid.uuid4() )
		self.men = 0
		self.women = 0
		self.history = []
		for key, value in kwargs.items():
			setattr(self, key, value)

	def run(self):
		self.main()

	def register(self):
		self.ir[self.name] = self.q
		self.main()

	def do_births(self):
		pass

	def do_deaths(self):
		pass

	def main(self):
		flag = False
		year = self.ns.year
		while True:
			# Message Block
			try:
				match self.q.get_nowait():
					case Message(cmd='KILL'):
						return
					case Message(cmd='DUMP'):
						self.log.send(Message('LOG', **{ 
							'text': f'{self.name}: {self.pop}'
						}))
					case Message(cmd='PLOT') as msg:
						self.log.send(Message('PLOT', **{ 'history': self.history, 'name': self.name }))
					case _:
						print(self.name)
			except:
				pass

			# Sentinel Block
			if self.ns.year == year and flag:
				continue
			flag = True
			year = self.ns.year

			# Growth Block 
			# This version modifies the current population in line with logarithmic growth. 
			# self.pop += self.pop * self.gr * ( ( self.K - self.pop ) / self.K )

			# Now, let's say that we wanted to model population growth by birth and death rate. 
			# self.pop += self.do_births()

			# self.pop -= self.do_deaths()

			for pulse in self.pulses:
				if pulse.yr == year + 1:
					self.men += pulse.men
					self.women += pulse.women

			self.history.append( (self.ns.year, 0 if self.pop == 0 else math.log(self.pop, 10) ) )

			# End Year
			self.tc.send(Message('GO'))

#
# Currently, return True to end the program
# 
def shell(ns, ps, log):
	if ns.year != t0 and ns.year % gc.check_period == 0:
		log.send( Message('LOG', **{ 
			'decoration_count': 2, 
			'text': f'--------\nYear {ns.year}\n--------',
			'order': 0
		}))

		log.send( Message('LOG', **{
			'order': 2,
			'text': '>>> '
		}))

		for island in ps:
			island.q.put(Message('DUMP'))

		match input(''):
			case 'q':
				for island in ps:
					island.q.put(Message('KILL'))
				log.send(Message('KILL'))
				return True
			case 'plot':
				for island in ps:
					island.q.put(Message('PLOT'))
			case _:
				pass
		
	
	

def sync_time(timecall_out, ir, ns, ps, log):
	ready = False
	buf = 0
	while True:
		match timecall_out.recv():
			case Message(cmd='ACK'):
				print('sup')
			case Message(cmd='GO'):
				buf += 1
				if buf == len(ir):
					buf = 0

					if gc.interactive and shell(ns, ps, log):
						break

					# The years won't tick by unless we increment this, so before this point execution is effectively paused
					ns.year += 1
			case Message(cmd='READY'):
				ready = True


# For every logging action we want to first build a payload, which happens here
# 
#
def log(ns, ir, log_out):
	buf = []
	decoration_count = None
	while True:
		# TODO continue addressing this trainwreck
		try:
			X = log_out.recv()
		except UnpicklingError as err:
			print(err)
			print(X)
			print(X.history)
			print(X.name)

		match X:
			case Message(cmd='LOG') as msg:
				buf.append( msg )
				
				try: 
					decoration_count = msg.decoration_count
				except AttributeError:
					pass

				if decoration_count is not None and len(buf) == decoration_count + len(ir):
					buf.sort( key=lambda x: x.order if hasattr(x, 'order') else 1 )
					print( '\n'.join( map( lambda x: x.text, buf ) ), end='' )
					buf = []
				
			case Message(cmd='PLOT') as msg:
				buf.append( msg )
				if len(buf) == len(ir):
					plotter = Process( target=plot, args=(buf,) )
					buf = []
					plotter.start()
					plotter.join()
			case Message(cmd='KILL'):
				return
			case None:
				pass
			
				
def plot(msg_buf):
	for msg in msg_buf:
		x,y = list(map(list, zip(*msg.history)))
		plt.plot( x, y, label = msg.name )
	plt.show()			

if __name__ == '__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument( "-p", action="store", dest="check_period", type=int )
	parser.add_argument( "-e", action="store", dest="end_year", type=int, default=1800 )
	gc = parser.parse_args()

	### DEFAULTS
	gc.interactive = gc.check_period is not None

	with Manager() as manager:
		ns = manager.Namespace()
		ns.year = t0

		# Island registry
		ir = manager.dict()

		# Time pipe
		timecall_out, timecall_in = Pipe()

		# Log pipe
		log_out, log_in = Pipe()

		ps = []
		for config in initial_island_config:
			config['q'] = manager.Queue()
			config['ns'] = ns
			config['ir'] = ir
			config['tc'] = timecall_in
			config['log'] = log_in

			island = Island(**config)
			ir[island.id] = island.q
			ps.append(island)
			island.start()

		logger = Process( target=log, args=(ns, ir, log_out) )
		logger.start()

		sync_time(timecall_out, ir, ns, ps, log_in)
		#Now that this has returned, clean-up all processes

		logger.join()
		for p in ps:
			p.join()

