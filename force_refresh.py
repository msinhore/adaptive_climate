#!/usr/bin/env python3
"""
Script para forçar refresh completo do componente adaptive_climate no Home Assistant.

Este script deve ser executado para garantir que todas as mudanças no config_flow.py
sejam detectadas pelo Home Assistant.
"""

import os
import shutil
import subprocess
from pathlib import Path

def main():
    print("🔄 Iniciando refresh completo do componente adaptive_climate...")
    
    # 1. Limpar cache Python local
    print("1. Limpando cache Python local...")
    for root, dirs, files in os.walk("."):
        for d in dirs:
            if d == "__pycache__":
                pycache_path = os.path.join(root, d)
                print(f"   Removendo: {pycache_path}")
                shutil.rmtree(pycache_path, ignore_errors=True)
        
        for f in files:
            if f.endswith(".pyc"):
                pyc_path = os.path.join(root, f)
                print(f"   Removendo: {pyc_path}")
                os.remove(pyc_path)
    
    # 2. Verificar sintaxe do config_flow.py
    print("2. Verificando sintaxe do config_flow.py...")
    result = subprocess.run([
        "python3", "-m", "py_compile", 
        "custom_components/adaptive_climate/config_flow.py"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("   ✅ Sintaxe OK")
    else:
        print(f"   ❌ Erro de sintaxe: {result.stderr}")
        return
    
    # 3. Verificar se async_get_options_flow está correto
    print("3. Verificando estrutura do OptionsFlow...")
    with open("custom_components/adaptive_climate/config_flow.py", "r") as f:
        content = f.read()
        
        checks = [
            ("async_get_options_flow method", "async_get_options_flow" in content),
            ("OptionsFlowHandler class", "class OptionsFlowHandler" in content),
            ("staticmethod decorator", "@staticmethod" in content),
            ("callback decorator", "@callback" in content),
            ("async_step_init method", "async def async_step_init" in content),
        ]
        
        for check_name, result in checks:
            status = "✅" if result else "❌"
            print(f"   {status} {check_name}")
    
    # 4. Criar um timestamp para forçar reload
    print("4. Criando timestamp para forçar reload...")
    timestamp_file = Path("custom_components/adaptive_climate/.force_reload")
    timestamp_file.write_text(f"Last refresh: {os.popen('date').read().strip()}")
    print(f"   ✅ Criado: {timestamp_file}")
    
    # 5. Instruções finais
    print("\n" + "="*60)
    print("🎯 PRÓXIMOS PASSOS:")
    print("1. Copie TODO o diretório custom_components/adaptive_climate para")
    print("   /root/config/custom_components/adaptive_climate no Home Assistant")
    print("2. Reinicie o Home Assistant COMPLETAMENTE")
    print("3. Vá em Configurações > Dispositivos & Serviços")
    print("4. Encontre a integração 'Adaptive Climate'")
    print("5. Clique nos 3 pontos > 'Configurar'")
    print("6. Procure por campos de debug como 'test_debug_field'")
    print("="*60)
    
    print("\n✅ Refresh completo finalizado!")

if __name__ == "__main__":
    main()
