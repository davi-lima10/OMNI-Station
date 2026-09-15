from machine import Pin, I2C
import utime

i2c = I2C(1, scl=Pin(3), sda=Pin(2), freq=400000)
addr = 0x68  # endereço padrão

# Tenta ler o registro de segundos (0x00)
data = i2c.readfrom_mem(addr, 0x00, 1)
print("Registro 0x00:", hex(data[0]))