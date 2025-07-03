#!/usr/bin/env python3
"""Demonstração das traduções Yes/No para binary sensors."""

def show_translation_changes():
    """Mostra as mudanças nas traduções."""
    print("🌐 TRADUÇÕES ATUALIZADAS - BINARY SENSORS")
    print("=" * 50)
    
    print("\n📊 ASHRAE COMPLIANCE:")
    print("Antes: on/off")
    print("Agora: Yes/No (inglês) | Sim/Não (português)")
    
    print("\n🌬️  NATURAL VENTILATION OPTIMAL:")
    print("Antes: on/off") 
    print("Agora: Yes/No (inglês) | Sim/Não (português)")
    
    print("\n💡 VANTAGENS:")
    print("• Mais intuitivo: 'Yes' para compliance é mais claro que 'On'")
    print("• Semântica correta: responde perguntas sim/não")
    print("• Consistência linguística em português")
    
    print("\n🔄 COMO ATIVAR:")
    print("1. Reinicie o Home Assistant")
    print("2. As traduções serão aplicadas automaticamente")
    print("3. Verifique os estados dos binary sensors")
    
    print("\n📋 EXEMPLOS:")
    print("binary_sensor.adaptive_climate_sala_ashrae_compliance:")
    print("  State: Yes (se em compliance) / No (se fora)")
    print("  Português: Sim / Não")
    print()
    print("binary_sensor.adaptive_climate_sala_natural_ventilation_optimal:")
    print("  State: Yes (se ventilação recomendada) / No (se não recomendada)")
    print("  Português: Sim / Não")

if __name__ == "__main__":
    show_translation_changes()
