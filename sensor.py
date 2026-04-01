#!/usr/bin/python
# LPS22HB
import time
import smbus

# Device specifics
LPS22HB_I2C_ADDRESS = 0x5C
LPS_ID              = 0xB1

class LPS22HB(object):

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

    def __init__(self, address=LPS22HB_I2C_ADDRESS):
        self._address = address
        self._bus     = smbus.SMBus(1)


        self._reset()
        self._write_byte(self.REGISTERS.get('CTRL_REG1'), 0x02)
    def _read_byte(self, cmd):
        return self._bus.read_byte_data(self._address, cmd)

    def _read_u16(self, cmd):
        lsb = self._bus.read_byte_data(self._address, cmd)
        msb = self._bus.read_byte_data(self._address, cmd + 1)
        return (msb << 8) | lsb

    def _write_byte(self, cmd, val):
        self._bus.write_byte_data(self._address, cmd, val)

    def _reset(self):
        """Soft reset – wait until the reset bit clears."""
        buf = self._read_u16(self.REGISTERS.get('CTRL_REG2'))
        buf |= 0x04                     
        self._write_byte(self.REGISTERS.get('CTRL_REG2'), buf)


        while True:
            buf = self._read_u16(self.REGISTERS.get('CTRL_REG2'))
            if not (buf & 0x04):
                break

    def start_oneshot(self):
        """Trigger a single conversion."""
        buf = self._read_u16(self.REGISTERS.get('CTRL_REG2'))
        buf |= 0x01                      # Set ONE_SHOT
        self._write_byte(self.REGISTERS.get('CTRL_REG2'), buf)


if __name__ == '__main__':
    print("\nPressure Sensor Test Program ...\n")
    lps22hb = LPS22HB()

    PRESS_DATA = 0.0
    TEMP_DATA  = 0.0
    u8Buf = [0, 0, 0]

    try:
        while True:
            time.sleep(0.1)
            lps22hb.start_oneshot()


            if lps22hb._read_byte(lps22hb.REGISTERS.get('STATUS')) & 0x01:
                u8Buf[0] = lps22hb._read_byte(lps22hb.REGISTERS.get('PRESS_OUT_XL'))
                u8Buf[1] = lps22hb._read_byte(lps22hb.REGISTERS.get('PRESS_OUT_L'))
                u8Buf[2] = lps22hb._read_byte(lps22hb.REGISTERS.get('PRESS_OUT_H'))
                PRESS_DATA = ((u8Buf[2] << 16) + (u8Buf[1] << 8) + u8Buf[0]) / 4096.0


            if lps22hb._read_byte(lps22hb.REGISTERS.get('STATUS')) & 0x02:
                u8Buf[0] = lps22hb._read_byte(lps22hb.REGISTERS.get('TEMP_OUT_L'))
                u8Buf[1] = lps22hb._read_byte(lps22hb.REGISTERS.get('TEMP_OUT_H'))
                TEMP_DATA = ((u8Buf[1] << 8) + u8Buf[0]) / 100.0

            print(f"Pressure: {PRESS_DATA:7.2f} hPa | Temp: {TEMP_DATA:7.2f} °C", end='\r')
    except KeyboardInterrupt:
        print("\nExiting.")
