"""
sensors_env.py — MicroPython drivers: AHT20, BMP280, VEML7700, SCD40
Usage:
    from sensors_env import AHT20, BMP280, VEML7700, SCD40
    aht = AHT20(i2c)
    temperature, humidity = aht.measure()

MIT License — v1.0.0
"""

from machine import I2C
import struct
import time

# ============================================================================
#  CRC-8 Sensirion (poly 0x31, init 0xFF) — used by SCD40
# ============================================================================

_CRC_TABLE = []
for _b in range(256):
    _c = _b
    for _ in range(8):
        _c = ((_c << 1) ^ 0x31) & 0xFF if (_c & 0x80) else (_c << 1)
    _CRC_TABLE.append(_c)


def _crc8(data: bytes) -> int:
    crc = 0xFF
    for b in data:
        crc = _CRC_TABLE[crc ^ b]
    return crc


# ============================================================================
#  AHT20 — Temperature / Humidity  (I2C addr 0x38)
# ============================================================================

AHT20_I2C_ADDR = const(0x38)
AHT20_CMD_CALIBRATE = const(0xBE)
AHT20_CMD_MEASURE = const(0xAC)
AHT20_CMD_RESET = const(0xBA)


class AHT20:
    """Aosong AHT20 temperature/humidity sensor.

    Usage:
        aht = AHT20(i2c)
        temperature, humidity = aht.measure()
    """

    def __init__(self, i2c: I2C, addr: int = AHT20_I2C_ADDR):
        self.i2c = i2c
        self.addr = addr
        time.sleep_ms(40)  # power-on settling
        status = i2c.readfrom(addr, 1)[0]
        if not (status & 0x08):  # calibration-enabled bit
            i2c.writeto(addr, bytes([AHT20_CMD_CALIBRATE, 0x08, 0x00]))
            time.sleep_ms(10)

    def measure(self):
        """Returns (temperature_C, humidity_%). ~80 ms per reading."""
        self.i2c.writeto(self.addr, bytes([AHT20_CMD_MEASURE, 0x33, 0x00]))
        time.sleep_ms(80)
        d = self.i2c.readfrom(self.addr, 7)
        if d[0] & 0x80:
            raise ValueError("AHT20: sensor busy")
        h_raw = ((d[1] << 16) | (d[2] << 8) | d[3]) >> 4
        t_raw = ((d[3] & 0x0F) << 16) | (d[4] << 8) | d[5]
        humidity = h_raw * 100.0 / 1048576.0
        temperature = t_raw * 200.0 / 1048576.0 - 50.0
        return temperature, max(0.0, min(100.0, humidity))

    def reset(self) -> None:
        self.i2c.writeto(self.addr, bytes([AHT20_CMD_RESET]))
        time.sleep_ms(20)


# ============================================================================
#  BMP280 — Temperature / Pressure  (I2C addr 0x76 or 0x77)
# ============================================================================

BMP280_I2C_ADDR = const(0x76)
BMP280_REG_ID = const(0xD0)
BMP280_REG_RESET = const(0xE0)
BMP280_REG_STATUS = const(0xF3)
BMP280_REG_CTRL_MEAS = const(0xF4)
BMP280_REG_CONFIG = const(0xF5)
BMP280_REG_PRESS_MSB = const(0xF7)
BMP280_CALIB_START = const(0x88)
BMP280_MODE_NORMAL = const(0x03)
BMP280_MODE_SLEEP = const(0x00)
BMP280_OSRS_4X = const(0x03)
BMP280_FILTER_4 = const(0x02)


class BMP280:
    """Bosch BMP280 pressure sensor.

    Usage:
        bmp = BMP280(i2c)
        temperature, pressure_hpa = bmp.measure()
    """

    def __init__(self, i2c: I2C, addr: int = BMP280_I2C_ADDR):
        self.i2c = i2c
        self.addr = addr
        chip_id = i2c.readfrom_mem(addr, BMP280_REG_ID, 1)[0]
        if chip_id not in (0x58, 0x60):
            raise RuntimeError("BMP280: unexpected chip ID 0x{:02X}".format(chip_id))
        self.t_fine = 0
        self._load_calibration()
        self.normal_mode()

    def _load_calibration(self) -> None:
        (self.dig_T1, self.dig_T2, self.dig_T3,
         self.dig_P1, self.dig_P2, self.dig_P3,
         self.dig_P4, self.dig_P5, self.dig_P6,
         self.dig_P7, self.dig_P8, self.dig_P9) = struct.unpack(
            '<HhhHhhhhhhhh', self.i2c.readfrom_mem(self.addr, BMP280_CALIB_START, 24))

    def normal_mode(self) -> None:
        self.i2c.writeto_mem(self.addr, BMP280_REG_CTRL_MEAS,
                             bytes([(BMP280_OSRS_4X << 5) | (BMP280_OSRS_4X << 2)
                                    | BMP280_MODE_NORMAL]))
        self.i2c.writeto_mem(self.addr, BMP280_REG_CONFIG,
                             bytes([BMP280_FILTER_4 << 2]))

    def sleep(self) -> None:
        self.i2c.writeto_mem(self.addr, BMP280_REG_CTRL_MEAS,
                             bytes([BMP280_MODE_SLEEP]))

    def measure(self):
        """Returns (temperature_C, pressure_hPa)."""
        for _ in range(25):  # wait for conversion, max ~25 ms
            if not (self.i2c.readfrom_mem(self.addr, BMP280_REG_STATUS, 1)[0] & 0x08):
                break
            time.sleep_ms(1)
        d = self.i2c.readfrom_mem(self.addr, BMP280_REG_PRESS_MSB, 6)
        press_raw = (d[0] << 12) | (d[1] << 4) | (d[2] >> 4)
        temp_raw = (d[3] << 12) | (d[4] << 4) | (d[5] >> 4)

        # Temperature compensation (Bosch datasheet)
        var1 = (temp_raw / 16384.0 - self.dig_T1 / 1024.0) * self.dig_T2
        var2 = ((temp_raw / 131072.0 - self.dig_T1 / 8192.0) ** 2) * self.dig_T3
        self.t_fine = int(var1 + var2)
        temperature = (var1 + var2) / 5120.0

        # Pressure compensation (Bosch datasheet)
        var1 = (self.t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * self.dig_P6 / 32768.0
        var2 = var2 + var1 * self.dig_P5 * 2.0
        var2 = (var2 / 4.0) + (self.dig_P4 * 65536.0)
        var1 = (self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.dig_P1
        if abs(var1) < 1e-12:
            return temperature, 0.0
        p = 1048576.0 - press_raw
        p = (p - (var2 / 4096.0)) * 6250.0 / var1
        var1 = self.dig_P9 * p * p / 2147483648.0
        var2 = p * self.dig_P8 / 32768.0
        p = p + (var1 + var2 + self.dig_P7) / 16.0
        return temperature, p / 100.0

    def altitude(self, sea_level_pressure: float = 1013.25) -> float:
        _, pressure = self.measure()
        return 44330.0 * (1.0 - (pressure / sea_level_pressure) ** (1.0 / 5.255))


# ============================================================================
#  VEML7700 — Ambient Light  (I2C addr 0x10)
# ============================================================================

VEML7700_I2C_ADDR = const(0x10)
VEML7700_REG_ALS_CONF = const(0x00)
VEML7700_REG_ALS = const(0x04)
VEML7700_REG_WHITE = const(0x05)

# gain code -> bits 12:11
_VEML_GAIN = {1.0: 0x00, 2.0: 0x01, 0.125: 0x02, 0.25: 0x03}
# it code -> bits 9:6 (100=0b0000, 200=0b0001, 400=0b0010, 800=0b0011, 50=0b1000, 25=0b1100)
_VEML_IT = {100: 0x00, 200: 0x01, 400: 0x02, 800: 0x03,
            50: 0x08, 25: 0x0C}

# Escada de sensibilidade: mais sensível -> menos sensível (auto-range)
_VEML_LADDER = ((2.0, 800), (2.0, 400), (1.0, 200), (0.25, 100), (0.25, 50),
                (0.125, 100), (0.125, 50), (0.125, 25))


class VEML7700:
    """Vishay VEML7700 ambient light sensor, 0 ~ ~120.000 lx (auto-range).

    Usage:
        veml = VEML7700(i2c)
        lux = veml.measure()
    """

    def __init__(self, i2c: I2C, addr: int = VEML7700_I2C_ADDR,
                 gain: float = 1.0, it_ms: int = 100):
        self.i2c = i2c
        self.addr = addr
        self._write_reg(VEML7700_REG_ALS_CONF, 0x0000)  # power on
        time.sleep_ms(3)
        self.auto_range = True
        self.ladder_pos = _VEML_LADDER.index((gain, it_ms)) \
            if (gain, it_ms) in _VEML_LADDER else 3
        self._apply_config()

    def _write_reg(self, reg: int, value: int) -> None:
        self.i2c.writeto_mem(self.addr, reg, struct.pack('<H', value))

    def _read_reg(self, reg: int) -> int:
        return struct.unpack('<H', self.i2c.readfrom_mem(self.addr, reg, 2))[0]

    def _apply_config(self) -> None:
        self.gain, self.it_ms = _VEML_LADDER[self.ladder_pos]
        conf = (_VEML_GAIN[self.gain] << 11) | (_VEML_IT[self.it_ms] << 6)
        self._write_reg(VEML7700_REG_ALS_CONF, conf)
        # 2x o tempo de integracao para o ALS estabilizar apos reconfig
        time.sleep_ms(2 * self.it_ms + 10)
        self._read_reg(VEML7700_REG_ALS)  # descarta a 1a leitura pos-config

    def _read_raw(self) -> int:
        time.sleep_ms(int(self.it_ms * 1.2) + 5)
        return self._read_reg(VEML7700_REG_ALS)

    def _lux(self, raw: int) -> float:
        lux = 5.76 * raw / (self.it_ms * self.gain)
        # Correcao de nao-linearidade (Vishay app note), p/ luz alta
        if lux > 1000.0:
            x = lux
            lux = (6.0135e-13 * x**4 - 9.3924e-9 * x**3
                   + 8.1488e-5 * x**2 + 1.0023 * x + 2.274e-4)
        return lux

    def measure(self) -> float:
        """Returns ambient light in lux (0 ~ ~120.000 lx)."""
        if not self.auto_range:
            return self._lux(self._read_raw())
        for _ in range(4):  # converge o auto-range, max 4 iteracoes
            raw = self._read_raw()
            if raw > 10000 and self.ladder_pos < len(_VEML_LADDER) - 1:
                self.ladder_pos += 1   # saturando -> menos sensibilidade
                self._apply_config()
            elif raw < 100 and self.ladder_pos > 0:
                self.ladder_pos -= 1   # escuro -> mais sensibilidade
                self._apply_config()
            else:
                break
        return self._lux(raw)

    def read_white(self) -> int:
        """White channel raw counts (uncalibrated broadband)."""
        return self._read_reg(VEML7700_REG_WHITE)

    def power_off(self) -> None:
        self._write_reg(VEML7700_REG_ALS_CONF, 0x0001)


# ============================================================================
#  SCD40 — CO2 / Temperature / Humidity  (I2C addr 0x62)
# ============================================================================

SCD40_I2C_ADDR = const(0x62)
SCD40_CMD_START_PERIODIC = const(0x21B1)
SCD40_CMD_STOP_PERIODIC = const(0x3F86)
SCD40_CMD_READ_MEASUREMENT = const(0xEC05)
SCD40_CMD_GET_DATA_READY = const(0xE4B8)
SCD40_CMD_WAKE_UP = const(0x36F6)
SCD40_CMD_INIT = const(0x3639)
SCD40_CMD_SET_TEMP_OFFSET = const(0x241D)
SCD40_CMD_SET_ALTITUDE = const(0x2427)


class SCD40:
    """Sensirion SCD40 true-CO2 sensor (NDIR photoacoustic).

    Usage:
        scd = SCD40(i2c)
        scd.start_periodic()
        # then, at most once per 5 s:
        co2_ppm, temperature, humidity = scd.measure()
    """

    def __init__(self, i2c: I2C, addr: int = SCD40_I2C_ADDR):
        self.i2c = i2c
        self.addr = addr
        try:
            self._write_words(SCD40_CMD_WAKE_UP, [])
        except OSError:
            pass  # no ACK during wake-up is expected
        time.sleep_ms(20)
        self._write_words(SCD40_CMD_STOP_PERIODIC, [])
        time.sleep_ms(500)
        self._write_words(SCD40_CMD_INIT, [])
        time.sleep_ms(100)

    def _write_words(self, cmd: int, words: list) -> None:
        data = bytes([cmd >> 8, cmd & 0xFF])
        for w in words:
            data += bytes([w >> 8, w & 0xFF,
                           _crc8(bytes([w >> 8, w & 0xFF]))])
        self.i2c.writeto(self.addr, data)

    def _read_words(self, cmd: int, n_words: int, delay_ms: int = 0) -> list:
        self.i2c.writeto(self.addr, bytes([cmd >> 8, cmd & 0xFF]))
        if delay_ms:
            time.sleep_ms(delay_ms)
        raw = self.i2c.readfrom(self.addr, n_words * 3)
        out = []
        for i in range(n_words):
            b = raw[i * 3:i * 3 + 3]
            if _crc8(b[0:2]) != b[2]:
                raise ValueError("SCD40: CRC mismatch")
            out.append((b[0] << 8) | b[1])
        return out

    def set_temperature_offset(self, celsius: float) -> None:
        """Compensate board self-heating (e.g. 4.0). Call before start_periodic()."""
        self._write_words(SCD40_CMD_SET_TEMP_OFFSET,
                          [int(celsius * 65536.0 / 175.0)])

    def set_altitude(self, meters: int) -> None:
        """Pressure compensation by altitude. Call before start_periodic()."""
        self._write_words(SCD40_CMD_SET_ALTITUDE, [meters])

    def start_periodic(self) -> None:
        """Start continuous measurement (1 new reading every 5 s)."""
        self._write_words(SCD40_CMD_START_PERIODIC, [])

    def stop_periodic(self) -> None:
        self._write_words(SCD40_CMD_STOP_PERIODIC, [])

    def data_ready(self) -> bool:
        return bool(self._read_words(SCD40_CMD_GET_DATA_READY, 1)[0])

    def measure(self):
        """Returns (co2_ppm, temperature_C, humidity_%).
        Returns None if no new reading is available yet (5 s interval)."""
        if not self.data_ready():
            return None
        w = self._read_words(SCD40_CMD_READ_MEASUREMENT, 3)
        co2 = w[0]
        temperature = -45.0 + 175.0 * w[1] / 65535.0
        humidity = 100.0 * w[2] / 65535.0
        return co2, temperature, humidity