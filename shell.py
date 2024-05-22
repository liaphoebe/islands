class Shell:
	def __init__(self, simulator, server_receiver):
		self.sim = simulator
		self.rcv = server_receiver

	def run(self):
		x = 0
		while True:
			print(self.rcv.recv())
			x += 1
			if x == 2:
				break

		print('done')
				
