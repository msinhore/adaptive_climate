#!/usr/bin/env python3
"""Script de diagnóstico para sensores binários Adaptive Climate."""

import json
import logging

def diagnose_binary_sensors():
    """Diagnóstico dos sensores binários."""
    print("🔍 DIAGNÓSTICO - SENSORES BINÁRIOS ADAPTIVE CLIMATE")
    print("=" * 60)
    
    print("\n📊 ASHRAE COMPLIANCE:")
    print("• ON quando: temperatura interna está dentro da faixa de conforto")
    print("• OFF quando: temperatura interna está fora da faixa de conforto")
    print("\nFaixa de conforto calculada baseada em:")
    print("  - Temperatura externa (média móvel)")
    print("  - Categoria de conforto (I/II/III)")
    print("  - Velocidade do ar (permite temperaturas mais altas)")
    print("  - Umidade (se habilitado)")
    
    print("\n🌬️  NATURAL VENTILATION OPTIMAL:")
    print("• ON quando TODAS estas condições são atendidas:")
    print("  1. Temperatura interna > temperatura máxima de conforto")
    print("  2. Temperatura externa < temperatura interna") 
    print("  3. Diferença de temperatura ≥ threshold (padrão: 2.0°C)")
    print("• OFF quando qualquer condição não for atendida")
    
    print("\n⚙️  CONFIGURAÇÕES ATUAIS (padrão):")
    print("• Categoria de conforto: II (±3°C)")
    print("• Velocidade do ar: 0.1 m/s")
    print("• Threshold ventilação natural: 2.0°C")
    print("• Temperatura mín. conforto: 18.0°C")
    print("• Temperatura máx. conforto: 28.0°C")
    
    print("\n🧮 EXEMPLO DE CÁLCULO:")
    print("Se temperatura externa = 25°C:")
    print("• Temperatura conforto adaptativo = 18.9 + (0.255 × 25) = 25.3°C")
    print("• Faixa conforto (Cat. II): 22.3°C - 28.3°C")
    print("• ASHRAE Compliance = ON se temp. interna entre 22.3°C e 28.3°C")
    print("\nSe temperatura interna = 28.4°C e externa = 25°C:")
    print("• Ventilação natural = OFF (diferença = 3.4°C, mas externa não é menor)")
    
    print("\n📋 PARA DIAGNOSTICAR SEUS VALORES:")
    print("1. Vá em Home Assistant > Desenvolvedor > Estados")
    print("2. Procure por suas entidades:")
    print("   - sensor.adaptive_climate_comfort_temperature_min")
    print("   - sensor.adaptive_climate_comfort_temperature_max") 
    print("   - sensor.adaptive_climate_indoor_temperature")
    print("   - sensor.adaptive_climate_outdoor_temperature")
    print("3. Compare os valores com as regras acima")
    
    print("\n🔧 POSSÍVEIS SOLUÇÕES:")
    print("• Para ASHRAE Compliance ON:")
    print("  - Ajuste o ar condicionado para temperatura dentro da faixa")
    print("  - Ou altere a categoria de conforto (III = mais tolerante)")
    print("  - Ou aumente velocidade do ar (permite temperaturas mais altas)")
    
    print("• Para Natural Ventilation ON:")
    print("  - Aguarde temperatura externa ficar menor que interna")
    print("  - Ou reduza o threshold de ventilação natural")
    print("  - Ou espere temperatura interna subir acima do máximo conforto")

if __name__ == "__main__":
    diagnose_binary_sensors()
