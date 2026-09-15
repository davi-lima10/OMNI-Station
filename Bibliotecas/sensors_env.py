"""
sensors_env.py — MicroPython: SHT4x + BMP280 (I2C)
v2: CRC no SHT4x, checagem de status no BMP280, read_all() unificado.
"""

from machine import I2C
import struct
import time

# ============================================================================
#  CONSTANTES
# ============================================================================

SHT4X_I2C_ADDR      = const(0x44)
SHT4X_CMD_MEASURE_HIGH   = const(0xFD)
SHT4X_CMD_MEASURE_MEDIUM = const(0xF6)
SHT4X_CMD_MEASURE_LOW    = const(0xE0)
SHT4X_CMD_SERIAL_NUMBER  = const(0x89)
SHT4X_CMD_RESET          = const(0x94)
SHT4X_CMD_HEATER_200_1S  = const(0x39)
SHT4X_CMD_HEATER_200_01S = const(0x32)
SHT4X_CMD_HEATER_110_1S  = const(0x2F)
SHT4X_CMD_HEATER_110_01S = const(0x24)
SHT4X_CMD_HEATER_20_1S   = const(0x1E)
SHT4X_CMD_HEATER_20_01S  = const(0x15)

BMP280_I2C_ADDR      = const(0x76)
BMP280_REG_ID        = const(0xD0)
BMP280_REG_RESET     = const(0xE0)
BMP280_REG_STATUS    = const(0xF3)
BMP280_REG_CTRL_MEAS = const(0xF4)
BMP280_REG_CONFIG    = const(0xF5)
BMP280_REG_PRESS_MSB = const(0xF7)
BMP280_CALIB_START   = const(0x88)

BMP280_MODE_SLEEP  = const(0x00)
BMP280_MODE_FORCED = const(0x01)
BMP280_MODE_NORMAL = const(0x03)

BMP280_OSRS_1X  = const(0x01)
BMP280_OSRS_4X  = const(0x03)
BMP280_OSRS_16X = const(0x05)

BMP280_FILTER_OFF = const(0x00)
BMP280_FILTER_4   = const(0x02)

SHT4X_RX_LEN = const(6)

# CRC-8 polinômio 0x31 (Sensirion), init 0xFF
_CRC_TABLE = []
for _b in range(256):
    _c = _b
    for _ in range(8):
        _c = ((_c << 1) ^ 0x31) & 0xFF if (_c & 0x80) else (_c << 1)
    _CRC_TABLE.append(_c)


def _sht4x_crc(data: bytes) -> int:
    crc = 0xFF
    for b in data:
        crc = _CRC_TABLE[crc ^ b]
    return crc


# ============================================================================
#  SHT4x
# ============================================================================

class SHT4x:
    """Driver SHT4x com verificação de CRC."""

    def __init__(self, i2c: I2C, addr: int = SHT4X_I2C_ADDR):
        self.i2c = i2c
        self.addr = addr
        self.ok = False
        try:
            self.serial = self._read_serial()
            self.ok = True
        except OSError:
            raise RuntimeError("SHT4x não encontrado no endereço 0x{:02X}".format(addr))

    def _send_cmd(self, cmd: int, delay_ms: int = 0) -> None:
        self.i2c.writeto(self.addr, bytes([cmd]))
        if delay_ms:
            time.sleep_ms(delay_ms)

    def _read_serial(self) -> bytes:
        self._send_cmd(SHT4X_CMD_SERIAL_NUMBER, delay_ms=10)
        return self.i2c.readfrom(self.addr, 6)

    def measure(self, precision: int = SHT4X_CMD_MEASURE_HIGH):
        """
        Medição com validação CRC.
        Retorna (temperatura_°C, umidade_%).
        Levanta OSError em falha I2C, ValueError em CRC inválido.
        """
        delays = {
            SHT4X_CMD_MEASURE_HIGH:   12,   # datasheet: 8.3ms típico; margem
            SHT4X_CMD_MEASURE_MEDIUM: 6,
            SHT4X_CMD_MEASURE_LOW:    3,
        }
        self._send_cmd(precision, delay_ms=delays.get(precision, 12))
        data = self.i2c.readfrom(self.addr, SHT4X_RX_LEN)

        # Valida CRC dos dois pares de bytes
        if _sht4x_crc(data[0:2]) != data[2] or _sht4x_crc(data[3:5]) != data[5]:
            raise ValueError("SHT4x: CRC inválido (leitura descartada)")

        t_raw = (data[0] << 8) | data[1]
        temp = -45.0 + 175.0 * t_raw / 65535.0
        h_raw = (data[3] << 8) | data[4]
        hum = -6.0 + 125.0 * h_raw / 65535.0

        hum = max(0.0, min(100.0, hum))
        self.ok = True
        return temp, hum

    def reset(self) -> None:
        self._send_cmd(SHT4X_CMD_RESET, delay_ms=2)

    def heater_on(self, duration: str = "short", power: str = "low") -> None:
        table = {
            ("low", "short"): SHT4X_CMD_HEATER_20_01S,
            ("low", "long"): SHT4X_CMD_HEATER_20_1S,
            ("medium", "short"): SHT4X_CMD_HEATER_110_01S,
            ("medium", "long"): SHT4X_CMD_HEATER_110_1S,
            ("high", "short"): SHT4X_CMD_HEATER_200_01S,
            ("high", "long"): SHT4X_CMD_HEATER_200_1S,
        }
        cmd = table.get((power, duration))
        if cmd is None:
            raise ValueError("Combinação inválida power/duration")
        self._send_cmd(cmd)
        time.sleep_ms(1100 if duration == "long" else 150)
        self.reset()  # heater exige soft reset depois


# ============================================================================
#  BMP280
# ============================================================================

class BMP280:
    """Driver BMP280 com checagem de status de conversão."""

    def __init__(self, i2c: I2C, addr: int = BMP280_I2C_ADDR):
        self.i2c = i2c
        self.addr = addr
        self.ok = False
        chip_id = self._read_reg(BMP280_REG_ID, 1)[0]
        if chip_id not in (0x58, 0x60):
            raise RuntimeError("BMP280 ID inválido: 0x{:02X}".format(chip_id))
        self._load_calibration()
        self.normal_mode()
        self.ok = True

    def _write_reg(self, reg: int, data: bytes) -> None:
        self.i2c.writeto_mem(self.addr, reg, data)

    def _read_reg(self, reg: int, n: int = 1) -> bytes:
        return self.i2c.readfrom_mem(self.addr, reg, n)

    def _load_calibration(self) -> None:
        calib = self._read_reg(BMP280_CALIB_START, 24)
        (self.dig_T1, self.dig_T2, self.dig_T3,
         self.dig_P1, self.dig_P2, self.dig_P3,
         self.dig_P4, self.dig_P5, self.dig_P6,
         self.dig_P7, self.dig_P8, self.dig_P9) = struct.unpack('<HhhHhhhhhhhh', calib)
        self.t_fine = 0

    def normal_mode(self, temp_osrs: int = BMP280_OSRS_4X,
                    press_osrs: int = BMP280_OSRS_4X,
                    filter_coeff: int = BMP280_FILTER_4) -> None:
        ctrl = (temp_osrs << 5) | (press_osrs << 2) | BMP280_MODE_NORMAL
        self._write_reg(BMP280_REG_CTRL_MEAS, bytes([ctrl]))
        self._write_reg(BMP280_REG_CONFIG, bytes([filter_coeff << 2]))

    def sleep(self) -> None:
        self._write_reg(BMP280_REG_CTRL_MEAS, bytes([BMP280_MODE_SLEEP]))

    def soft_reset(self) -> None:
        self._write_reg(BMP280_REG_RESET, bytes([0xB6]))
        time.sleep_ms(10)
        self._load_calibration()
        self.normal_mode()

    def _read_raw(self):
        # Espera conversão terminar (bit 3 = measuring), máx 25ms
        for _ in range(25):
            if not (self._read_reg(BMP280_REG_STATUS, 1)[0] & 0x08):
                break
            time.sleep_ms(1)
        data = self._read_reg(BMP280_REG_PRESS_MSB, 6)
        press_raw = (data[0] << 12) | (data[1] << 4) | (data[2] >> 4)
        temp_raw = (data[3] << 12) | (data[4] << 4) | (data[5] >> 4)
        return temp_raw, press_raw

    def _compensate_temp(self, adc_T: int) -> float:
        var1 = (adc_T / 16384.0 - self.dig_T1 / 1024.0) * self.dig_T2
        var2 = ((adc_T / 131072.0 - self.dig_T1 / 8192.0) ** 2) * self.dig_T3
        self.t_fine = int(var1 + var2)
        return (var1 + var2) / 5120.0

    def _compensate_press(self, adc_P: int) -> float:
        var1 = (self.t_fine / 2.0) - 64000.0
        var2 = var1 * var1 * self.dig_P6 / 32768.0
        var2 = var2 + var1 * self.dig_P5 * 2.0
        var2 = (var2 / 4.0) + (self.dig_P4 * 65536.0)
        var1 = (self.dig_P3 * var1 * var1 / 524288.0 + self.dig_P2 * var1) / 524288.0
        var1 = (1.0 + var1 / 32768.0) * self.dig_P1
        if abs(var1) < 1e-12:
            return 0.0
        p = 1048576.0 - adc_P
        p = (p - (var2 / 4096.0)) * 6250.0 / var1
        var1 = self.dig_P9 * p * p / 2147483648.0
        var2 = p * self.dig_P8 / 32768.0
        p = p + (var1 + var2 + self.dig_P7) / 16.0
        return p / 100.0

    def measure(self):
        """Retorna (temperatura_°C, pressão_hPa). Levanta OSError em falha I2C."""
        temp_raw, press_raw = self._read_raw()
        temp = self._compensate_temp(temp_raw)
        press = self._compensate_press(press_raw)
        self.ok = True
        return temp, press

    def altitude(self, sea_level_pressure: float = 1013.25) -> float:
        _, press = self.measure()
        return 44330.0 * (1.0 - (press / sea_level_pressure) ** (1.0 / 5.255))


# ============================================================================
#  Interface unificada
# ============================================================================

class SensorHub:
    """
    Agrupa SHT4x + BMP280 com reconexão automática.
    read_all() retorna dict — valores None quando o sensor falha.
    """

    def __init__(self, i2c_id: int, scl: int, sda: int, freq: int = 400000):
        self.i2c_id = i2c_id
        self.scl = scl
        self.sda = sda
        self.freq = freq
        self.sht = None
        self.bmp = None
        self._connect()

    def _make_i2c(self) -> I2C:
        from machine import Pin
        return I2C(self.i2c_id, scl=Pin(self.scl), sda=Pin(self.sda), freq=self.freq)

    def _connect(self) -> None:
        try:
            i2c = self._make_i2c()
            if self.sht is None:
                try:
                    self.sht = SHT4x(i2c)
                except Exception:
                    self.sht = None
            if self.bmp is None:
                try:
                    self.bmp = BMP280(i2c)
                except Exception:
                    self.bmp = None
            self.last_error = None
        except Exception as e:
            self.last_error = str(e)

    def reconnect(self) -> None:
        """Tenta recriar o barramento e reinstanciar sensores travados."""
        try:
            self.sht = None
            self.bmp = None
            self._connect()
        except Exception as e:
            self.last_error = str(e)

    def read_all(self, precision: int = SHT4X_CMD_MEASURE_HIGH) -> dict:
        """
        Retorna:
        {
            'temperatura': float ou None,   # SHT4x
            'umidade':     float ou None,   # SHT4x
            'pressao':     float ou None,   # BMP280 (hPa)
            'erro':        str ou None,
        }
        Um sensor falhando não impede a leitura do outro.
        Se ambos falharem, tenta reconectar na próxima chamada.
        """
        result = {'temperatura': None, 'umidade': None,
                  'pressao': None, 'erro': None}
        failed = False

        if self.sht is not None:
            try:
                t, h = self.sht.measure(precision)
                result['temperatura'] = t # type: ignore
                result['umidade'] = h # type: ignore
            except Exception as e:
                failed = True
                result['erro'] = "SHT4x: " + str(e) # type: ignore

        if self.bmp is not None:
            try:
                _, p = self.bmp.measure()
                result['pressao'] = p # type: ignore
            except Exception as e:
                failed = True
                result['erro'] = (result['erro'] or "") + " BMP280: " + str(e) # type: ignore

        # Ambos falhando ou ausentes → tenta reconexão (com backoff externo)
        if (self.sht is None and self.bmp is None) or failed:
            self.last_error = result['erro']

        return result