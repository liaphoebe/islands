class Simulation:
	def __init__(self, verbose=False):
		from island import Island
		import yaml

		with open("config.yaml", "r") as stream:
			self.island_registry = { island.name: island for island in [ Island(**doc, verbose=verbose) for doc in yaml.safe_load_all(stream) ] }

		self.resolve_event_dependencies(verbose=verbose)
		self.inject_multiprocessing_config()

	@property
	def islands(self):
		return self.island_registry.values() 	

	def run(self, history_mode='IMPORT', verbose=False):
		for island in self.islands: 
			island.history_mode = history_mode
			island.start()

		self.shell.run()

		for island in self.islands:
			island.join()

		print('bingo bango bongo')

	def inject_multiprocessing_config(self):
		from multiprocessing import Pipe
		from shell import Shell

		server_out, server_in = Pipe() 
		receiver = server_out
		for island in self.islands:
			island_out, island_in = Pipe()
			island.bind_multiprocessing_communication_channels(**{
				'server': server_in,
				'island': island_in,
				'receiver': island_out
			})

		self.shell = Shell(self, receiver) 
		
	def timeline_dump(self):
		for island in self.island_registry.values():
			print(f'{island}')
			for event in island.events.values():
				print(f'\t{event.name}: {event.params}')
				

	def reroll(self):
		for island in self.island_registry.values():
			for event in island.events.values():
				event.reroll_year()
				event.reroll_growth_rate()
				event.reset_dependency_check()

		self.resolve_event_dependencies()

	def import_preflights(self):
		for island in self.islands:
			island.import_vital_record()

	def preflights(self):
		for island in self.islands:
			island.history_preflight()

	def preflight(self, island_name, verbose=False):
		self.island_registry[island_name].history_preflight(verbose=verbose)

	def resolve_event_dependencies(self, verbose=False):
		def resolve(dependent_event, verbose=False):
			island_name, independent_event = dependent_event.year.follow.split('::')

			if verbose:
				print(f'\t\tResolving {dependent_event} against {island_name}::{independent_event}')

			independent_event = self.island_registry[island_name].events[independent_event]

			if independent_event.has_unresolved_dependency:
				resolve(independent_event, verbose=verbose)

			if verbose:
				print(f'\t\tAdding {dependent_event.year} to {independent_event.year}')

			dependent_event.year += independent_event.year
			dependent_event.year.unit = independent_event.year.unit
			dependent_event.has_unresolved_dependency = False

		if verbose:
			print('Resolving event dependencies...')

		for island in self.island_registry.values():
			if verbose:
				print(f'\t{island}')
			for event in list( filter( lambda ev: ev.has_unresolved_dependency, island.events.values() ) ):
				# Double check for recursive case 
				if event.has_unresolved_dependency:
					resolve(event, verbose=verbose)

if __name__ == '__main__':
	s = Simulation()
	s.run()
