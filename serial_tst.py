import serial
import time

print('Serial script started');

ser = serial.Serial('/dev/ttyACM0', 9600);

while True:
    out = ser.readline()
    print(out)
    out = out.decode("utf-8")
    out = out.replace('X=', '').replace('out=', '').replace('wart_star=', '').replace(',','');
    print(out);
