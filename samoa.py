samoa = {
	"name": "Samoa",
	"size": 1093,
	"pop": 202506
}
rapa = {
	"name": "Rapa Nui",
	"size": 63.17,
	"pop": 7750
}
tonga = {
	"name": "Tonga",
	"size": 289,
	"pop": 100209
}

def bigger(one, other):
	print( f'{ one["name"] } is { round( one["size"] / other["size"], 2 ) } times bigger than { other["name"] } and has { round( one["pop"] / other["pop"], 2 ) } times more people' )

bigger(samoa, rapa)
bigger(samoa, tonga)
bigger(tonga, rapa)
