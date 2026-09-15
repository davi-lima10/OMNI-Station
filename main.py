# ============================================================================
#  Bibliotecas
# ============================================================================
import time, gc
from machine import Pin, I2C

# Módulos
from Modulos.ui import Colors, output_oled, output_terminal, output_debug
from Modulos.calculos import calculos_atmosfericos

# ============================================================================
#  Configurações
# ============================================================================
space_terminal = 60
dots_terminal = 55
dots_terminal_debug = 105
dots_adjust_1 = "."
dots_adjust_2 = ".."
dots_oled = 8

updates = 0
tentativas_erro = 0
usage_ram = 0.0

temperatura = None
umidade_relativa = None
pressao_atm_hpa = None

sht = None
bmp = None
rtc = None
oled = None

scan_i2c0 = []
scan_i2c1 = []

error_i2c0 = "N/A"
error_i2c1 = "N/A"

# ----------------------------------------------------------------------------
#  Barramento I2C
# ----------------------------------------------------------------------------
try:
    i2c0 = I2C(0, scl=Pin(17), sda=Pin(16), freq=400000)
    i2c1 = I2C(1, scl=Pin(3), sda=Pin(2), freq=400000)
except Exception as e:
    error_i2c0 = f"{Colors.RED}{e}"
    error_i2c1 = f"{Colors.RED}{e}"

# ----------------------------------------------------------------------------
#  Sensores (I2C0)
# ----------------------------------------------------------------------------
def setup_i2c0():
    global sht, bmp, error_i2c0
    try:
        from Bibliotecas import sensors_env
        time.sleep(0.5)
        sht = sensors_env.SHT4x(i2c0)
        bmp = sensors_env.BMP280(i2c0)
    except Exception as e:
        error_i2c0 = f"{Colors.RED}{e}"

setup_i2c0()

# ----------------------------------------------------------------------------
#  RTC + OLED (I2C1)
# ----------------------------------------------------------------------------
try:
    from Bibliotecas import urtc
    from Bibliotecas.ssd1306 import SSD1306_I2C
    rtc = urtc.DS3231(i2c1)
    oled = SSD1306_I2C(128, 64, i2c1)
    error_i2c1 = "N/A"
except Exception as e:
    error_i2c1 = f"{Colors.RED}{e}"

# ============================================================================
#  Loop principal
# ============================================================================
while True:
    # ------------------------------------------------------------------------
    #  Leitura dos sensores
    # ------------------------------------------------------------------------
    if sht is not None and bmp is not None:
        try:
            soma_temperatura = 0
            soma_umidade_relativa = 0
            soma_pressao_atm_hpa = 0

            for _ in range(25):
                temperatura, umidade_relativa = sht.measure()  # type: ignore
                _, pressao_atm_hpa = bmp.measure()  # type: ignore

                soma_temperatura += temperatura
                soma_umidade_relativa += umidade_relativa
                soma_pressao_atm_hpa += pressao_atm_hpa
                time.sleep(0.1)

            temperatura = soma_temperatura / 25
            umidade_relativa = soma_umidade_relativa / 25
            pressao_atm_hpa = soma_pressao_atm_hpa / 25

            error_i2c0 = "N/A"
            tentativas_erro = 0

        except Exception as e:
            error_i2c0 = f"{Colors.RED}{e}"
            temperatura = None
            umidade_relativa = None
            pressao_atm_hpa = None
            tentativas_erro += 1

            if tentativas_erro >= 5:
                status = "Reconectando I2C0"
                setup_i2c0()
                tentativas_erro = 0

    # ------------------------------------------------------------------------
    #  Cálculos e output
    # ------------------------------------------------------------------------
    if temperatura is not None and umidade_relativa is not None and pressao_atm_hpa is not None:
        # RTC
        if rtc is not None:
            try:
                dt = rtc.get_time()
                timestamp_display = f"{dt[2]:02d}/{dt[1]:02d} {dt[3]:02d}:{dt[4]:02d}"
                error_i2c1 = "N/A"
            except Exception as e:
                error_i2c1 = f"{Colors.RED}{e}"
                timestamp_display = "00/00 00:00"
        else:
            timestamp_display = "00/00 00:00"

        # Correções
        if umidade_relativa >= 100:
            umidade_relativa = 99.99
        if temperatura >= 100:
            temperatura = 99.99

        # Cálculos
        calc = calculos_atmosfericos(temperatura, umidade_relativa, pressao_atm_hpa)

        # Debug
        gc.collect()
        free_ram = gc.mem_free()
        allocated_ram = gc.mem_alloc()
        usage_ram = allocated_ram / (allocated_ram + free_ram) * 100
        updates += 1
        scan_i2c0 = [hex(a) for a in i2c0.scan()]
        scan_i2c1 = [hex(a) for a in i2c1.scan()]

        # Output
        try:
            output_oled(updates, calc, oled, dots_oled)
        except Exception as e:
            error_i2c1 = f"{Colors.RED}{e}"

        if error_i2c0 == "N/A" and error_i2c1 == "N/A":
            status = "Funcionando"
        else:
            status = f"{Colors.RED}Erros detectados"

        output_terminal(timestamp_display, calc, dots_terminal, dots_adjust_1, dots_adjust_2, space_terminal)
        output_debug(updates, scan_i2c0, scan_i2c1, error_i2c0, error_i2c1, usage_ram, status, dots_terminal_debug, dots_adjust_1, dots_adjust_2)

    else:
        print(f"{Colors.CLEAR}")
        status = f"{Colors.RED}Erro crítico detectado"
        updates = 0
        usage_ram = 0
        output_debug(updates, scan_i2c0, scan_i2c1, error_i2c0, error_i2c1, usage_ram, status, dots_terminal_debug, dots_adjust_1, dots_adjust_2)
        time.sleep(2.5)