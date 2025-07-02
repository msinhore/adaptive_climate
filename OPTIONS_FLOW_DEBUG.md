# 🔧 Adaptive Climate - Options Flow Debug Guide

## ✅ Status da Configuração

A análise técnica mostra que **TODOS** os componentes necessários para o Options Flow estão configurados corretamente:

### 📋 Checklist Técnico
- ✅ `config_flow: true` no manifest.json
- ✅ `@staticmethod` e `@callback` decorators
- ✅ `async_get_options_flow()` método presente
- ✅ `OptionsFlowHandler` classe implementada
- ✅ `async_step_init()` método presente
- ✅ Update listener configurado no `__init__.py`
- ✅ Device registry configurado corretamente
- ✅ Domain inheritance correto

## 🎯 Possíveis Causas do Problema

1. **Cache do Home Assistant**: Integrações customizadas podem ficar em cache
2. **Restart necessário**: Mudanças em config_flow requerem restart completo
3. **Versão específica**: Home Assistant 2025.6.0+ pode ter mudanças sutis
4. **State da integração**: A integração precisa estar em estado "loaded"

## 🔧 Passos de Resolução

### Método 1: Restart Completo
1. Parar o Home Assistant completamente
2. Aguardar 10 segundos
3. Iniciar o Home Assistant
4. Verificar se o botão "Configurações" aparece

### Método 2: Recarregar a Integração
1. Ir em **Configurações > Dispositivos e Serviços**
2. Encontrar **Adaptive Climate Sala**
3. Clicar nos 3 pontos (...) ao lado
4. Selecionar **Recarregar**
5. Verificar se o botão aparece

### Método 3: Remover e Readicionar
1. **Fazer backup das configurações atuais**
2. Remover a integração Adaptive Climate
3. Restart do Home Assistant
4. Adicionar a integração novamente
5. Configurar as entidades

### Método 4: Verificar Logs
1. Ir em **Configurações > Logs**
2. Filtrar por "adaptive_climate"
3. Procurar por erros relacionados a "config_flow" ou "options"

## 📱 Como Deve Aparecer

Quando funcionando corretamente, você deve ver:

```
┌─────────────────────────────────────┐
│ 📱 Adaptive Climate Sala           │
│ ✏️ CONFIGURAR                       │  ← Este botão deve aparecer
│                                     │
│ Device info                         │
│ • ASHRAE Compliance: On             │
│ • Comfort Temperature: 25.0°C       │
│ ...                                 │
└─────────────────────────────────────┘
```

## 🐛 Se Ainda Não Funcionar

1. **Verificar versão do HA**: Confirme que está na 2025.6.0+
2. **Verificar integration_type**: Confirme se "service" é suportado
3. **Testar em modo debug**: Ativar logs debug para adaptive_climate
4. **Verificar outras integrações**: Confirme se outras integrações têm botão de configuração

## 📋 Comando de Verificação Rápida

Execute no terminal do Home Assistant (se acessível):

```bash
# Verificar se a integração está carregada
ha core info | grep adaptive_climate

# Verificar entradas de configuração
ha config entries
```

## 🎯 Resultado Esperado

Após seguir os passos, você deve conseguir:
1. ✅ Ver o botão "Configurações" no device
2. ✅ Acessar a interface unificada de configuração
3. ✅ Modificar parâmetros como toggles, sliders e dropdowns
4. ✅ Ver as mudanças aplicadas em tempo real

---

**📝 Nota**: Se nenhum dos métodos funcionar, pode ser uma limitação específica da versão 2025.6.0 ou do integration_type "service". Neste caso, podemos explorar alternativas como mudar para "integration" ou implementar uma abordagem diferente.
