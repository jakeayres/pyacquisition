import pyvisa, time

rm = pyvisa.ResourceManager()

print(rm.list_resources())

my_instrument = rm.open_resource(
	"GPIB0::26::1::INSTR",
	read_termination='\r',
	write_termination='\r',
	#query_delay=0.1,
	#send_end=False,
	timeout=1000,
	)




my_instrument.write('R0')

data = my_instrument.read_raw()
print(data)