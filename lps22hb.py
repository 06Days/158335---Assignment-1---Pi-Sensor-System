#!/usr/bin/env python3
"""
LPS22HB pressure / temperature I2C driver for python - meant for the Waveshare sensor HAT (b/c) on a raspberry pi - written by Toby Cammock-Elliott
Sensor comes with an error of+-1.5 degrees celcius
"""
import time
import smbus
LPS22HB_I2C_ADDRESS = 0x5C
LPS22HB_ID          = 0xB1
class LPS22HB:
    REGISTERS = {
        'INT_CFG'      : 0x0B,
        'THS_P_L'      : 0x0C,
        'THS_P_H'      : 0x0D,
        'WHO_AM_I'     : 0x0F,
        'CTRL_REG1'    : 0x10,
        'CTRL_REG2'    : 0x11,
        'CTRL_REG3'    : 0x12,
        'FIFO_CTRL'    : 0x14,
        'REF_P_XL'     : 0x15,
        'REF_P_L'      : 0x16,
        'REF_P_H'      : 0x17,
        'RPDS_L'       : 0x18,
        'RPDS_H'       : 0x19,
        'RES_CONF'     : 0x1A,
        'INT_SOURCE'   : 0x25,
        'FIFO_STATUS'  : 0x26,
        'STATUS'       : 0x27,
        'PRESS_OUT_XL': 0x28,
        'PRESS_OUT_L' : 0x29,
        'PRESS_OUT_H' : 0x2A,
        'TEMP_OUT_L'  : 0x2B,
        'TEMP_OUT_H'  : 0x2C,
        'RES'          : 0x33
    }
    def __init__(self, address: int = LPS22HB_I2C_ADDRESS, bus_id: int = 1):
        """Create a new instance and power‑up the sensor."""
        self._address = address
        self._bus     = smbus.SMBus(bus_id)
        if self._read_byte(self.REGISTERS['WHO_AM_I']) != LPS22HB_ID:
            raise RuntimeError(f"Unexpected WHO_AM_I: 0x{self._read_byte(self.REGISTERS['WHO_AM_I']):02X}")
        self._reset()
        self._write_byte(self.REGISTERS['CTRL_REG1'], 0x02)  # 0.5 Hz, normal mode

    def _read_byte(self, reg: int) -> int:
        return self._bus.read_byte_data(self._address, reg)

    def _read_u16(self, reg: int) -> int:
        """Read a 16‑bit value from two consecutive registers (LSB first)."""
        lsb = self._bus.read_byte_data(self._address, reg)
        msb = self._bus.read_byte_data(self._address, reg + 1)
        return (msb << 8) | lsb

    def _write_byte(self, reg: int, value: int) -> None:
        self._bus.write_byte_data(self._address, reg, value)

    def _reset(self) -> None:
        """Soft reset – wait until the reset bit clears."""

        self._write_byte(self.REGISTERS['CTRL_REG2'], 0x04)  # Set reset bit
        while self._read_byte(self.REGISTERS['CTRL_REG2']) & 0x04:
            time.sleep(0.01)

    def start_oneshot(self) -> None:
        """Trigger a single pressure/temperature conversion."""
        self._write_byte(self.REGISTERS['CTRL_REG2'], 0x01)

    def read_pressure_hpa(self) -> float:
        """Return pressure in hPa (Pa / 100)."""
        self.start_oneshot()

        while not (self._read_byte(self.REGISTERS['STATUS']) & 0x01):
            time.sleep(0.005)

        raw = (self._read_byte(self.REGISTERS['PRESS_OUT_H']) << 16) | \
              (self._read_byte(self.REGISTERS['PRESS_OUT_L']) << 8) | \
              self._read_byte(self.REGISTERS['PRESS_OUT_XL'])
        return raw / 4096.0

    def read_temperature_c(self) -> float:
        """Return temperature in °C."""
        self.start_oneshot()

        while not (self._read_byte(self.REGISTERS['STATUS']) & 0x02):
            time.sleep(0.005)

        raw = (self._read_byte(self.REGISTERS['TEMP_OUT_H']) << 8) | \
              self._read_byte(self.REGISTERS['TEMP_OUT_L'])
        return raw / 100.0

def read_sensor(lps: LPS22HB) -> tuple[float, float]:
    """
    Take a single pressure/temperature sample and return it.
    requires passing a LPS22HB class instance
    returns:
    (pressure_hpa, temperature_c) : tuple[float, float]
    pressure given in hectopascals, temperature given in celcius
    """

    pressure = lps.read_pressure_hpa()
    temperature = lps.read_temperature_c()
    return pressure, temperature

if __name__ == "__main__":
    lps = LPS22HB()
    try:
        while True:
            p, t = read_sensor(lps)
            print(f"Pressure: {p:7.2f} hPa | Temp: {t:7.2f} °C", end="\r")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nExiting.")
