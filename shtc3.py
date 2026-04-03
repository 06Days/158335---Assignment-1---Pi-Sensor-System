"""
SHTC3 humidity / temperature I2C driver for python - meant for the Waveshare sensor HAT (b/c) on a raspberry pi - written by Toby Cammock-Elliott
Sensor comes with an error of+-0.2 degrees celcius
"""
import time
import lgpio as sbc

SHTC3_I2C_ADDRESS   = 0x70
CRC_POLYNOMIAL      = 0x0131

REGISTERS = {
    'SHTC3_WAKEUP': 0x3517,
    'SHTC3_SLEEP': 0xB098,
    'SHTC3_SOFTWARE_RES':0x805D,
    'SHTC3_NM_CD_READTH': 0x7866,
    'SHTC3_NM_CD_READRH': 0x58E0
}

class SHTC3:
    def __init__(self, address: int = SHTC3_I2C_ADDRESS, bus_id: int=1):
        self._address= address
        self._fd = sbc.i2c_open(bus_id, address)
        self._reset()
    # Check the checksum coming from the incoming data this helps with error detection
    def _check_crc(self,data:list, length:int, checksum:int)-> bool:
        crc= 0xFF
        for byteCtr in range(0, length):
            crc=crc^data[byteCtr]
            for bit in range(0,8):
                if crc & 0x80:
                    crc= (crc <<1)^CRC_POLYNOMIAL
                else:
                    crc=crc << 1
            crc &=0xFF
        return crc==checksum
    def _write_command(self,cmd_key: str) ->None:
        cmd = REGISTERS[cmd_key]
        sbc.i2c_write_byte_data(self._fd, cmd >> 8, cmd & 0xFF)
    def _reset(self) -> None:
        self._write_command('SHTC3_SOFTWARE_RES')
        time.sleep(0.05)
    def wakeup(self) ->None:
        try:
            self._write_command('SHTC3_WAKEUP')
            time.sleep(0.05)
        except OSError:
            pass
    def sleep(self)->None:
        self._write_command('SHTC3_SLEEP')
        time.sleep(0.05)
    def read_temperature_c(self)->float:
        self.wakeup()
        self._write_command('SHTC3_NM_CD_READTH')
        time.sleep(0.1)
        count, buffer = sbc.i2c_read_device(self._fd, 3)
        self.sleep()
        if count==3 and self._check_crc(buffer,2,buffer[2]):
            raw=(buffer[0]<<8) | buffer[1]
            return (raw * 175.0/65536.0) -45.0
        return 0.0
    # relative means 'at the position of the sensor'
    def read_humidity_relative(self) ->float:
        self.wakeup()
        self._write_command('SHTC3_NM_CD_READRH')
        time.sleep(0.05)
        count,buffer=sbc.i2c_read_device(self._fd,3)
        # gtself.sleep()
        if count==3 and self._check_crc(buffer, 2,buffer[2]):
            raw=(buffer[0]<<8) | buffer[1]
            return 100.0 *raw/65536.0
        return 0.0
def read_sensor(sht: SHTC3) -> tuple [float,float]:
    temperature = sht.read_temperature_c()
    humidity = sht.read_humidity_relative()
    return temperature, humidity

if __name__ == "__main__":
    sht = SHTC3()
    try:
        while True:
            t, h = read_sensor(sht)
            print(f"Temperature: {t:7.2f} °C | Humidity: {h:7.2f} %", end="\r")
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\nExiting.")
