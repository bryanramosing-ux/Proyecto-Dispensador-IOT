"""
Balance energético del dispensador (todas las hipótesis son editables).

    python calculo_energia.py
    python calculo_energia.py --celda-mah 3000 --horas-sol 5 --raciones-dia 6

Fuentes de los valores típicos:
  * ESP32: hoja de datos Espressif (TX 802.11b ~240 mA, RX ~95-100 mA a 3,3 V).
    Promedio de la PLACA DevKit con Wi-Fi conectado: ESTIMADO (incluye LDO,
    puente USB-serie y LED) -> MEDIR con multímetro en serie.
  * ESP32-CAM: especificación AI-Thinker (180 mA @5 V sin flash, 310 mA @5 V flash).
  * HC-SR04: hoja de datos (15 mA en funcionamiento, < 2 mA en reposo, 5 V). El de presencia se
    toma midiendo siempre (peor caso); el del nivel de la tolva mide una vez por minuto, así que
    domina su corriente de reposo (se usa 2 mA, el máximo de la hoja de datos).
  * Cable de la estación solar remota: caída = I x R; AWG 22 = 0,053 ohm/m por conductor.
  * MG995: hojas de datos de distribuidores (500-900 mA en movimiento a 6 V,
    2,5 A bloqueado a 6 V). Varía entre fabricantes/clones -> MEDIR.
  * Panel: 3 V x 100 mA = 0,3 W en condiciones estándar (1000 W/m2, 25 °C).
"""
import argparse


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--i-esp32", type=float, default=0.10, help="A promedio placa ESP32 @5 V (ESTIMADO)")
    ap.add_argument("--i-cam", type=float, default=0.18, help="A promedio ESP32-CAM @5 V (AI-Thinker)")
    ap.add_argument("--i-hc", type=float, default=0.015, help="A HC-SR04 de presencia @5 V (peor caso: midiendo siempre)")
    ap.add_argument("--i-hc-nivel", type=float, default=0.002, help="A HC-SR04 de la tolva @5 V (mide 1 vez/min)")
    ap.add_argument("--cable-panel-m", type=float, default=5.0, help="largo del cable a la estación solar (m)")
    ap.add_argument("--ohm-m", type=float, default=0.053, help="resistencia por metro de cada conductor (AWG 22)")
    ap.add_argument("--i-servo-mov", type=float, default=0.7, help="A MG995 en movimiento @6 V (típico)")
    ap.add_argument("--t-ciclo", type=float, default=4.0, help="s de servo energizado por ciclo de dosis")
    ap.add_argument("--ciclos-racion", type=int, default=3)
    ap.add_argument("--raciones-dia", type=int, default=6)
    ap.add_argument("--eficiencia-dcdc", type=float, default=0.85, help="convertidores buck (SUPUESTO)")
    ap.add_argument("--celda-mah", type=float, default=2500, help="capacidad REAL de cada 18650 (etiqueta fiable)")
    ap.add_argument("--paralelo", type=int, default=1, help="1 = 2S1P, 2 = 2S2P")
    ap.add_argument("--uso-bateria", type=float, default=0.80, help="fracción utilizable")
    ap.add_argument("--panel-w", type=float, default=0.30)
    ap.add_argument("--horas-sol", type=float, default=4.0, help="horas solares pico del lugar")
    ap.add_argument("--eficiencia-solar", type=float, default=0.60,
                    help="elevador + cargador + desajuste sin MPPT (SUPUESTO)")
    a = ap.parse_args()

    p_esp, p_cam, p_hc, p_hc2 = 5 * a.i_esp32, 5 * a.i_cam, 5 * a.i_hc, 5 * a.i_hc_nivel
    p_logica = p_esp + p_cam + p_hc + p_hc2
    e_logica_dia = p_logica * 24 / a.eficiencia_dcdc
    e_servo_dia = 6 * a.i_servo_mov * a.t_ciclo * a.ciclos_racion * a.raciones_dia / 3600 / a.eficiencia_dcdc
    e_dia = e_logica_dia + e_servo_dia
    p_media = e_dia / 24

    e_bat = 7.4 * a.celda_mah / 1000 * a.paralelo
    e_util = e_bat * a.uso_bateria
    e_panel = a.panel_w * a.horas_sol * a.eficiencia_solar
    e_panel_interior = a.panel_w * 0.005 * 8   # ~0,5 % de la irradiancia estándar, 8 h de luz artificial

    pico_5v = 0.25 + 0.31 + 2 * a.i_hc
    pico_6v = 2.5
    pico_bat = (5 * pico_5v + 6 * pico_6v) / a.eficiencia_dcdc / 6.4

    print("CONSUMO (régimen permanente, Wi-Fi siempre conectado)")
    print(f"  ESP32 DevKit ......... {p_esp:5.2f} W")
    print(f"  ESP32-CAM ............ {p_cam:5.2f} W")
    print(f"  HC-SR04 presencia .... {p_hc:5.3f} W")
    print(f"  HC-SR04 nivel tolva .. {p_hc2:5.3f} W")
    print(f"  Lógica total (5 V) ... {p_logica:5.2f} W  -> {e_logica_dia:5.1f} Wh/día con pérdidas DC-DC")
    print(f"  MG995 ................ {e_servo_dia:5.2f} Wh/día ({a.raciones_dia} raciones x {a.ciclos_racion} ciclos)")
    print(f"  TOTAL ................ {e_dia:5.1f} Wh/día  (potencia media {p_media:4.2f} W)")
    print("\nPICOS DE CORRIENTE")
    print(f"  Riel 5 V ............. {pico_5v:4.2f} A  (convertidor >= 2 A)")
    print(f"  Riel 6 V (bloqueo) ... {pico_6v:4.2f} A  (convertidor >= 3 A)")
    print(f"  Batería (peor caso) .. {pico_bat:4.2f} A a 6,4 V  (BMS >= 5 A, fusible 4 A lento)")
    print("\nBATERÍA")
    print(f"  2S{a.paralelo}P {a.celda_mah:.0f} mAh ...... {e_bat:5.1f} Wh nominal, {e_util:5.1f} Wh utilizables")
    print(f"  Autonomía ............ {e_util / p_media:5.1f} h sin sol")
    print("\nPANEL SOLAR")
    print(f"  Exterior ({a.horas_sol} HSP) ... {e_panel:5.2f} Wh/día = {100 * e_panel / e_dia:4.1f} % del consumo")
    print(f"  Interior (feria) ..... {e_panel_interior:5.3f} Wh/día = {100 * e_panel_interior / e_dia:5.2f} % del consumo")
    print(f"  Potencia instantánea máx. {a.panel_w:.2f} W vs. consumo medio {p_media:.2f} W "
          f"-> {'INSUFICIENTE' if a.panel_w < p_media else 'suficiente en pico'} incluso a pleno sol")
    i_panel = a.panel_w / 3.0
    caida = i_panel * 2 * a.cable_panel_m * a.ohm_m
    print(f"  Cable a la estación remota ({a.cable_panel_m:.0f} m, ida y vuelta): caída {caida:4.2f} V a "
          f"{i_panel * 1000:.0f} mA = {100 * caida / 3.0:3.1f} % de 3 V (despreciable)")
    necesario = e_dia / (a.horas_sol * 0.75)
    print(f"  Panel necesario para autonomía solar: ~{necesario:4.1f} W (con MPPT ~75 %) + batería para 2 días "
          f"(~{2 * e_dia:4.0f} Wh)")


if __name__ == "__main__":
    main()
