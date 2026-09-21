import math # Biblioteca para funções matemáticas

def calcular_svp_avp(temperatura, umidade_relativa):
    svp = 0.61121 * math.exp(((18.678 - temperatura / 234.5) * temperatura) / (257.14 + temperatura))
    avp = svp * (umidade_relativa / 100)
    return svp, avp

def calcular_vpd(svp, avp):
    vpd = max(0, svp - avp)
    return vpd

def calcular_ponto_orvalho(temperatura, avp):
    td_min = -150
    td_max = temperatura + 0.25
    for _ in range(75):
        td_teste = (td_min + td_max) / 2
        svp_teste = 0.61121 * math.exp(((18.678 - td_teste / 234.5) * td_teste) / (257.14 + td_teste))
        if svp_teste < avp:
            td_min = td_teste
        else:
            td_max = td_teste
    ponto_orvalho = (td_min + td_max) / 2
    if ponto_orvalho > temperatura:
        ponto_orvalho = temperatura
    return ponto_orvalho

def calcular_umidade_absoluta(avp, temperatura_k):
    avp_hpa = avp * 10
    umidade_absoluta = (216.7 * avp_hpa) / temperatura_k
    return umidade_absoluta

def calcular_densidade_ar(pressao_atm_pa, avp_pa, temperatura_k):
    pressao_ar_seco = pressao_atm_pa - avp_pa
    densidade_ar = pressao_ar_seco / (287.05 * temperatura_k) + avp_pa / (461.5 * temperatura_k)
    return densidade_ar

def calcular_volume_especifico(densidade_ar):
    volume_especifico = 1 / densidade_ar
    return volume_especifico

def calcular_razao_mistura(avp, pressao_atm):
    razao_mistura = 0.622 * (avp / (pressao_atm - avp))
    razao_mistura_g = razao_mistura * 1000
    return razao_mistura, razao_mistura_g

def calcular_energia_latente(temperatura, razao_mistura):
    energia_latente = (2501 - 2.361 * temperatura) * razao_mistura
    return energia_latente

def calcular_temperatura_potencial(temperatura_k, pressao_atm_hpa):
    temperatura_potencial = temperatura_k * (1000 / pressao_atm_hpa) ** 0.286
    return temperatura_potencial

def calcular_temperatura_virtual(temperatura_k, razao_mistura):
    temperatura_virtual = (temperatura_k * (1 + 0.61 * razao_mistura)) - 273.15
    return temperatura_virtual

def calcular_entalpia_ar(temperatura, razao_mistura):
    entalpia_ar = 1.006 * temperatura + razao_mistura * (2501 + 1.86 * temperatura)
    return entalpia_ar

def calcular_lcl(temperatura, ponto_orvalho):
    lcl = (temperatura - ponto_orvalho) * 125
    return lcl

def calcular_bulbo_umido(temperatura, umidade_relativa):
    if not (-20 <= temperatura <= 50):
        return None
    if umidade_relativa < 5:
        return None
    try:
        bulbo_umido = (temperatura * math.atan(0.151977 * math.sqrt(umidade_relativa + 8.313659))
                      + math.atan(temperatura + umidade_relativa)
                      - math.atan(umidade_relativa - 1.676331)
                      + 0.00391838 * umidade_relativa ** 1.5 * math.atan(0.023101 * umidade_relativa)
                      - 4.686035)
        return bulbo_umido
    except (ValueError, ZeroDivisionError):
        return None

def calculos_atmosfericos(temperatura, umidade_relativa, pressao_atm_hpa, lux):
    # Conversões Básicas de Unidades
    pressao_atm = pressao_atm_hpa / 10
    pressao_atm_pa = pressao_atm_hpa * 100
    temperatura_k = temperatura + 273.15

    # SVP, AVP e VPD
    svp, avp = calcular_svp_avp(temperatura, umidade_relativa)
    avp_pa = avp * 1000
    vpd = calcular_vpd(svp, avp)

    # Ponto de Orvalho e Depressão do Ponto de Orvalho
    ponto_orvalho = calcular_ponto_orvalho(temperatura, avp)

    # Umidade Absoluta e Razão de Mistura
    umidade_absoluta = calcular_umidade_absoluta(avp, temperatura_k)
    razao_mistura, razao_mistura_g = calcular_razao_mistura(avp, pressao_atm)

    # Densidade do Ar e Volume Específico
    densidade_ar = calcular_densidade_ar(pressao_atm_pa, avp_pa, temperatura_k)
    volume_especifico = calcular_volume_especifico(densidade_ar)

    # Temperaturas Derivadas
    temperatura_potencial = calcular_temperatura_potencial(temperatura_k, pressao_atm_hpa)
    temperatura_virtual = calcular_temperatura_virtual(temperatura_k, razao_mistura)
    bulbo_umido = calcular_bulbo_umido(temperatura, umidade_relativa)

    # Energia Latente
    energia_latente = calcular_energia_latente(temperatura, razao_mistura)
    entalpia_ar = calcular_entalpia_ar(temperatura, razao_mistura)

    # Indicadores Atmosféricos
    lcl = calcular_lcl(temperatura, ponto_orvalho)

    return {
    # Dados de entrada
    'temperatura': temperatura,
    'umidade_relativa': umidade_relativa,
    'pressao_atm_hpa': pressao_atm_hpa,
    'lux': lux,
    
    # Conversões
    'temperatura_k': temperatura_k,
    'pressao_atm': pressao_atm,
    'pressao_pa': pressao_atm_pa,
    
    # Umidade
    'svp': svp,
    'avp': avp,
    'vpd': vpd,
    'ponto_orvalho': ponto_orvalho,
    'umidade_absoluta': umidade_absoluta,
    'razao_mistura': razao_mistura,
    'razao_mistura_g': razao_mistura_g,
    
    # Ar
    'densidade_ar': densidade_ar,
    'volume_especifico': volume_especifico,
    
    # Temperaturas derivadas
    'temperatura_virtual': temperatura_virtual,
    'temperatura_potencial': temperatura_potencial,
    'bulbo_umido': bulbo_umido,   # Pode ser None!
    
    # Energia
    'energia_latente': energia_latente,
    'entalpia_ar': entalpia_ar,
    
    # Indicadores
    'lcl': lcl,
}