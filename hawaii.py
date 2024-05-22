year = 1770
pop  = 638000

print ( f'{pop} in {year}' )
while True: 
	if year % 50 == 0:
		print( f'{ pop } in { year }' )
		if input() == 'q':
			break
	year -= 1
	pop /= 1.009

