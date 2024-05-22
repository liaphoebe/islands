from soc import Population
import numpy as np
import random

class Kainanga:
	
	def __init__(self, sz=100):
		pop = Population(sz)
		P = pop.flattened_P() 

		random.shuffle(P) 

		
