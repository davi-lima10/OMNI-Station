from Bibliotecas import stratum as st

# ============================================================================
#  Cores ANSI para terminal
# ============================================================================
class Colors:
    BLUE    = "\x1b[94m"
    MAGENTA = "\x1b[95m"
    YELLOW  = "\x1b[33m"
    CYAN    = "\x1b[96m"
    GREEN   = "\x1b[32m"
    RED     = "\x1b[31m"
    GRAY    = "\x1b[90m"
    RESET   = "\x1b[0m"
    BOLD    = "\x1b[1m"
    CLEAR   = "\033[H\033[J"

# ============================================================================
#  ASCII Art
# ============================================================================
Banner_OMNI = r'''
  /██████  /██      /██ /██   /██ /██████        /██████   /██                 /██     /██                    
 /██__  ██| ███    /███| ███ | ██|_  ██_/       /██__  ██ | ██                | ██    |__/                    
| ██  \ ██| ████  /████| ████| ██  | ██        | ██  \__//██████    /██████  /██████   /██  /██████  /███████ 
| ██  | ██| ██ ██/██ ██| ██ ██ ██  | ██        |  ██████|_  ██_/   |____  ██|_  ██_/  | ██ /██__  ██| ██__  ██
| ██  | ██| ██  ███| ██| ██  ████  | ██         \____  ██ | ██      /███████  | ██    | ██| ██  \ ██| ██  \ ██
| ██  | ██| ██\  █ | ██| ██\  ███  | ██         /██  \ ██ | ██ /██ /██__  ██  | ██ /██| ██| ██  | ██| ██  | ██
|  ██████/| ██ \/  | ██| ██ \  ██ /██████      |  ██████/ |  ████/|  ███████  |  ████/| ██|  ██████/| ██  | ██
 \______/ |__/     |__/|__/  \__/|______/       \______/   \___/   \_______/   \___/  |__/ \______/ |__/  |__/'''


Numeros_ASCII = {
    '1': [r'  _   ',
          r' / |  ',
          r' | |  ',
          r' |_|  '],
    
    '2': [r' ___  ',
          r'|_  ) ',
          r' / /  ',
          r'/___| '],
    
    '3': [r' ____ ',
          r'|__ / ',
          r' |_ \ ',
          r'|___/ '],
    
    '4': [r' _ _  ',
          r'| | | ',
          r'|_  _|',
          r'  |_| '],
    
    '5': [r' ___  ',
          r'| __| ',
          r'|__ \ ',
          r'|___/ '],
    
    '6': [r'  __  ',
          r' / /  ',
          r'/ _ \ ',
          r'\___/ '],
    
    '7': [r' ____ ',
          r'|__  |',
          r'  / / ',
          r' /_/  '],
    
    '8': [r' ___  ',
          r'( _ ) ',
          r'/ _ \ ',
          r'\___/ '],
    
    '9': [r' ___  ',
          r'/ _ \ ',
          r'\_, / ',
          r' /_/  '],
    
    '0': [r'  __  ',
          r' /  \ ',
          r'| () |',
          r' \__/ '],
    
    '/': [r'   __ ',
          r'  / / ',
          r' / /  ',
          r'/_/   '],
    
    ':': [r'      ',
          r'  ()  ',
          r'  ()  ',
          r'      '],
    
    ' ': [r'      ',
          r'      ',
          r'      ',
          r'      ']}

# ============================================================================
#  Relógio em ASCII Art
# ============================================================================
def hora_ascii(texto):
    linhas = ['', '', '', '']
    for char in texto:
        digitos_linha = Numeros_ASCII.get(char, Numeros_ASCII[' '])
        for i in range(4):
            linhas[i] += digitos_linha[i] + ' '
    return '\n'.join(linhas)


# ============================================================================
#  Output OLED
# ============================================================================
def output_oled(updates, calc, oled, dots_oled):
    if oled is not None:
        oled.fill(0)
        oled.text(f"Dados Essenciais", 0, 0)
        oled.text(f"----------------", 0, 8)
        oled.text(f"{f'T':.<{dots_oled}}{calc['temperatura']:.1f} C", 0, 16)
        oled.text(f"{f'Td':.<{dots_oled}}{calc['ponto_orvalho']:.1f} C", 0, 24)
        oled.text(f"{f'UR':.<{dots_oled}}{calc['umidade_relativa']:.1f} %", 0, 32)
        oled.text(f"{f'P':.<{dots_oled}}{calc['pressao_atm']:.1f} kPa", 0, 40)
        oled.text(f"{f'Updates...':.<{dots_oled}}{updates}", 0, 56)
        oled.show()

def output_oled_error(updates, usage_ram, oled, dots_oled):
    if oled is not None:
        oled.fill(0)
        oled.text(f"Debug", 0, 0)
        oled.text(f"----------------", 0, 8)
        oled.text(f"{f'Updates':.<{dots_oled}}{updates}", 0, 16)
        oled.text(f"{f'RAM':.<{dots_oled}}{usage_ram:.1f}%", 0, 24)
        oled.text(f"{f'Status':.<{dots_oled}}ERRO", 0, 32)
        oled.show()
        
# ============================================================================
#  Output Terminal
# ============================================================================
def output_terminal(timestamp_display, calc, dots_terminal, dots_adjust_1, dots_adjust_2, space_terminal):
    if calc['bulbo_umido'] is not None:
        bulbo_umido_txt = f"{Colors.MAGENTA}{calc['bulbo_umido']:.2f}°C{Colors.RESET}"
    else:
        bulbo_umido_txt = f"{Colors.RED}N/A{Colors.RESET}"

    # Banner
    print(Colors.CLEAR)
    print(f"{Colors.CYAN}{Banner_OMNI}{Colors.RESET}")

    # Relógio em ASCII
    print(f"{Colors.CYAN}", end="")
    print(hora_ascii(timestamp_display))
    print(f"{Colors.RESET}")
    print("")

    # ----------------------------------------------------------------------------
    #  Variáveis do Terminal
    # ----------------------------------------------------------------------------
    division_string = f"{Colors.GRAY}╰────────────────────────────────────────────────────────────╯{Colors.RESET}"

    dados_entrada_string         =      f"{Colors.GRAY}╭───── {Colors.BLUE}Dados de Entrada {Colors.GRAY}─────────────────────────────────────╮{Colors.RESET}"
    energia_ar_string            =      f"{Colors.GRAY}╭───── {Colors.MAGENTA}Energia do Ar {Colors.GRAY}────────────────────────────────────────╮{Colors.RESET}"
    propriedades_umidade_string  =      f"{Colors.GRAY}╭───── {Colors.MAGENTA}Propriedades da Umidade {Colors.GRAY}──────────────────────────────╮{Colors.RESET}"
    estado_atmosferico_string    =      f"{Colors.GRAY}╭───── {Colors.MAGENTA}Estado Atmosférico {Colors.GRAY}───────────────────────────────────╮{Colors.RESET}"

    temperatura_string           =      f"{Colors.RESET}{f'  Temperatura{Colors.GRAY}':.<{dots_terminal}}{Colors.BLUE}{calc['temperatura']:.2f}°C{Colors.RESET}"
    umidade_relativa_string      =      f"{Colors.RESET}{f'  Umidade Relativa{Colors.GRAY}':.<{dots_terminal}}{Colors.BLUE}{calc['umidade_relativa']:.2f}%{Colors.RESET}"
    pressao_atm_string           =      f"{Colors.RESET}{f'  Pressão Atmosférica{Colors.GRAY}':.<{dots_terminal}}{dots_adjust_2}{Colors.BLUE}{calc['pressao_atm']:.1f} kPa{Colors.RESET}"
    
    entalpia_ar_string           =      f"{Colors.RESET}{f'    Entalpia do Ar Úmido{Colors.GRAY}':.<{dots_terminal}}{dots_adjust_1}{Colors.MAGENTA}{calc['entalpia_ar']:.2f} kJ/kg{Colors.RESET}"
    energia_latente_string       =      f"{Colors.RESET}{f'    Energia Latente{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['energia_latente']:.2f} kJ/kg{Colors.RESET}"
    temperatura_potencial_string =      f"{Colors.RESET}{f'    Temperatura Potencial{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['temperatura_potencial']:.2f} K{Colors.RESET}"

    ponto_orvalho_string         =      f"{Colors.RESET}{f'  Ponto de Orvalho{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['ponto_orvalho']:.2f}°C{Colors.RESET}"
    avp_string                   =      f"{Colors.RESET}{f'  AVP{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['avp']:.2f} kPa{Colors.RESET}"
    svp_string                   =      f"{Colors.RESET}{f'  SVP{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['svp']:.2f} kPa{Colors.RESET}"
    vpd_string                   =      f"{Colors.RESET}{f'  VPD{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['vpd']:.2f} kPa{Colors.RESET}"
    umidade_absoluta_string      =      f"{Colors.RESET}{f'  Umidade Absoluta{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['umidade_absoluta']:.2f} g/m³{Colors.RESET}"
    volume_especifico_string     =      f"{Colors.RESET}{f'  Volume Específico do Ar{Colors.GRAY}':.<{dots_terminal}}{dots_adjust_1}{Colors.MAGENTA}{calc['volume_especifico']:.2f} m³/kg{Colors.RESET}"

    bulbo_umido_string           =      f"{Colors.RESET}{f'    Bulbo Úmido{Colors.GRAY}':.<{dots_terminal}}{dots_adjust_1}{Colors.MAGENTA}{bulbo_umido_txt}{Colors.RESET}"
    lcl_string                   =      f"{Colors.RESET}{f'    LCL{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['lcl']:.0f} m{Colors.RESET}"
    temperatura_virtual_string   =      f"{Colors.RESET}{f'    Temperatura Virtual{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['temperatura_virtual']:.2f}°C{Colors.RESET}"
    densidade_ar_string          =      f"{Colors.RESET}{f'    Densidade do Ar{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{calc['densidade_ar']:.2f} kg/m³{Colors.RESET}"
    razao_mistura_string         =      f"{Colors.RESET}{f'    Razão de Mistura{Colors.GRAY}':.<{dots_terminal}}{Colors.MAGENTA}{dots_adjust_1}{calc['razao_mistura_g']:.2f} g/kg{Colors.RESET}"

    # Dados de Entrada | Energia do Ar
    st.text(dados_entrada_string,        space_terminal,      energia_ar_string)
    st.text(temperatura_string,          space_terminal,      entalpia_ar_string)
    st.text(umidade_relativa_string,     space_terminal,      energia_latente_string)
    st.text(pressao_atm_string,          space_terminal,      temperatura_potencial_string)
    st.text(division_string,            space_terminal,      division_string)
    print("")

    # Propriedades da Umidade | Estado Atmosférico
    st.text(propriedades_umidade_string, space_terminal,      estado_atmosferico_string)
    st.text(ponto_orvalho_string,        space_terminal,      bulbo_umido_string)
    st.text(avp_string,                  space_terminal,      lcl_string)
    st.text(svp_string,                  space_terminal,      temperatura_virtual_string)
    st.text(vpd_string,                  space_terminal,      densidade_ar_string)
    st.text(umidade_absoluta_string,     space_terminal,      razao_mistura_string)
    st.text(volume_especifico_string,    space_terminal)
    st.text(division_string,            space_terminal,      division_string)
    print("")

# ============================================================================
#  Output Debug
# ============================================================================
def output_debug(updates, scan_i2c0, scan_i2c1, error_i2c0, error_i2c1, usage_ram, status, dots_terminal_debug, dots_adjust_1, dots_adjust_2):
    division_string = f"{Colors.GRAY}╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯{Colors.RESET}"
    
    print(f"{Colors.GRAY}╭───── {Colors.YELLOW}Debug {Colors.GRAY}─────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮{Colors.RESET}")
    print(f"{Colors.RESET}{f'  Updates{Colors.GRAY}':.<{dots_terminal_debug}}{Colors.YELLOW}{updates}{Colors.RESET}")
    print(f"{Colors.RESET}{f'  RAM (Heap){Colors.GRAY}':.<{dots_terminal_debug}}{Colors.YELLOW}{usage_ram:.2f}%{Colors.RESET}")
    print(f"{Colors.RESET}{f'  Erros I2C0{Colors.GRAY}':.<{dots_terminal_debug}}{Colors.YELLOW}{error_i2c0}{Colors.RESET}")
    print(f"{Colors.RESET}{f'  Erros I2C1{Colors.GRAY}':.<{dots_terminal_debug}}{Colors.YELLOW}{error_i2c1}{Colors.RESET}")
    print(f"{Colors.RESET}{f'  Endereços I2C0 (Sensores){Colors.GRAY}':.<{dots_terminal_debug}}{dots_adjust_1}{Colors.YELLOW}{scan_i2c0}{Colors.RESET}")
    print(f"{Colors.RESET}{f'  Endereços I2C1 (Periféricos){Colors.GRAY}':.<{dots_terminal_debug}}{dots_adjust_2}{Colors.YELLOW}{scan_i2c1}{Colors.RESET}")
    print(f"{Colors.RESET}{f'  Status{Colors.GRAY}':.<{dots_terminal_debug}}{Colors.YELLOW}{status}{Colors.RESET}")
    print(f"{division_string}")