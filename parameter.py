from enum import Enum
import random
import scipy.stats as stats

class Parameter:

	# Every lambda is how to convert the unit given by that lambda's key to the unit
	#   given by the enclosing dictionary's key. So like each dict is a collection of 
	#   how to convert other units to that unit. 
	CONVERSION_TABLE = {
		'generations ago': {
			'years ago': lambda x: x / 30
		},
		'years ago': {
			'generations ago': lambda x: x * 30
		},
		'raw': { # As in number of people
			'log(Ne)': lambda x: 10 ** x
		},
		'CE': {
			
		}
	}

	def __init__(self, type_, value, unit, follow=None, distribution=None, verbose=False):
		self.type_ = type_
		self.unit = unit

		if verbose:
			print(f'\t\tType: {self.type_}')
			print(f'\t\tDistribution: {distribution}')
			print(f'\t\tFollows: {follow}') 

		self.follow = follow

		self.initial_value = value
		self.distribution = distribution
		self.roll()

	# I'm gonna need everyone here to roll initiative!
	def roll(self):
		value = self.initial_value
		distribution = self.distribution

		# Straight numbers are interpreted as constants, so...
		if type(value) is not list and distribution is None:
			self.value = value
		# But if the value is given as a list, there's a special case for the growth rate param so...
		elif self.type_ == 'Growth Rate':
			assert distribution == None
			min_, max_, time = value
			# Assume time is in years ago and convert min_ and max_ raw
			min_ = self.CONVERSION_TABLE['raw']['log(Ne)']( random.uniform(*min_) )
			max_ = self.CONVERSION_TABLE['raw']['log(Ne)']( random.uniform(*max_) )
			self.value = ( max_ - min_ ) / time
			self.measured_time = time
			self.unit = "raw / year"
		else:
			match distribution:
				# Uniform by default, so...
				case None:
					self.value = random.uniform(*value)
				case { 'type_': 'normal' }:
					mu = distribution['mu']
					sigma = distribution['sigma']
					distro_params = { 'loc': mu, 'scale': sigma }
					# Assume None means do not truncate
					if value == None:
						X = stats.norm(**distro_params)
					else:
						lower, upper = value
						X = stats.truncnorm( (lower - mu) / sigma, (upper - mu) / sigma, **distro_params)

					self.value = X.rvs()

			

	def __repr__(self):
		return f'{str(self.value)} {self.unit}'

	def __iadd__(self, other):
		assert self.type_ == other.type_

		if self.value is None:
			self.value = other.value
			return self

		if self.unit != other.unit:
			other.convert(self.unit)

		# For generations or years ago, adding one value to another is meant to represent
		#   progressing further along the timeline. So, adding 12 generations ago to 50 generations ago
		#   should equal 38 generations ago. Hence the subtraction rule. 
		if 'ago' in self.unit:
			self.value = abs(self.value - other.value)
		else:
			self.value += other.value

		return self

	def __lt__(self, other):
		assert self.type_ == other.type_
		return self.value < other.convert(self.unit)

	def convert(self, new_unit):
		if self.unit != new_unit:
			ct = self.CONVERSION_TABLE
			assert new_unit in ct and self.unit in ct[new_unit]

			self.value = ct[new_unit][self.unit](self.value) 
			self.unit  = new_unit

		return self.value

		
