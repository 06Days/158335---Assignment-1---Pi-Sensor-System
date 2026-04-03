"""
SHTC3 humidity / temperature I2C driver for python - meant for the Waveshare sensor HAT (b/c) on a raspberry pi - written by Toby Cammock-Elliott
Sensor comes with an error of+-0.2 degrees celcius
"""
import time
import smbus

SHTC3_I2C_ADDRESS   = 0x70
CRC_POLYNOMIAL      = 0x0131

REGISTERS = {
    'SHTC3_WAKEUP': 0x3517,
    'SHTC3_SLEEP': 0xB098,
    'SHTC3_SOFTWARE_RES':0x805D,
    'SHTC3_NM_CD_READTH': 0x7866,
    'SHTC3_NM_CD_READRH': 0x58E0
}
