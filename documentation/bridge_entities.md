# Bridge Entities para Adaptive Climate

## Visão Geral

As bridge entities são entidades UI auxiliares que fazem ponte entre o frontend e o sensor binário principal (`ashrae_compliance`). Elas permitem modificação dos atributos do sensor binário através da interface do usuário sem alterar diretamente o config_entry ou coordinator.config.

## Arquitetura

### Conceito Principal

- **Sensor Binário Principal**: `binary_sensor.adaptive_climate_ashrae_compliance`
- **Bridge Entities**: Entidades Number, Switch, Select e Sensor que refletem e modificam atributos específicos
- **Comunicação**: Todas as operações passam através de `hass.states.async_set`
- **Persistência**: Não há persistência direta - valores são mantidos apenas nos atributos do sensor binário

### Fluxo de Dados

```
UI (Frontend) ↔ Bridge Entity ↔ Binary Sensor Attributes ↔ Coordinator (Read-only)
```

1. **Leitura**: Bridge entities lêem valores dos atributos do sensor binário
2. **Escrita**: Bridge entities atualizam atributos via `hass.states.async_set`
3. **Sincronização**: Coordinator lê apenas do sensor binário para cálculos

## Entidades Implementadas

### Number Entities (5)
- `outdoor_temp`: Temperatura externa (-30°C a 50°C)
- `indoor_temp`: Temperatura interna (10°C a 35°C)
- `air_velocity`: Velocidade do ar (0.0 a 3.0 m/s)
- `metabolic_rate`: Taxa metabólica (0.8 a 4.0 met)
- `clothing_insulation`: Isolamento da roupa (0.0 a 3.0 clo)

### Switch Entities (2)
- `auto_update`: Atualização automática
- `use_feels_like`: Usar temperatura aparente

### Select Entities (1)
- `comfort_class`: Classe de conforto (class_1, class_2, class_3)

### Sensor Entities (3) - Somente Leitura
- `comfort_temperature`: Temperatura de conforto calculada
- `comfort_range_min`: Limite mínimo do range de conforto
- `comfort_range_max`: Limite máximo do range de conforto

## Implementação Técnica

### Estrutura de Arquivos

```
custom_components/adaptive_climate/
├── bridge_entity.py     # Classes base e configurações
├── number.py           # Bridge entities Number + entities existentes
├── switch.py           # Bridge entities Switch apenas
├── select.py           # Bridge entities Select apenas
├── sensor.py           # Bridge entities Sensor apenas
└── __init__.py         # Registro das plataformas
```

### Classes Principais

- `BaseBridgeEntity`: Classe base com funcionalidades comuns
- `NumberBridgeEntity`: Especialização para entidades numéricas
- `SwitchBridgeEntity`: Especialização para switches
- `SelectBridgeEntity`: Especialização para seleções
- `SensorBridgeEntity`: Especialização para sensores (read-only)

### Configuração das Entidades

A configuração está centralizada em `BRIDGE_ENTITY_CONFIG` no `bridge_entity.py`:

```python
BRIDGE_ENTITY_CONFIG = {
    "number": {
        "outdoor_temp": {
            "name": "Outdoor Temperature",
            "min_value": -30.0,
            "max_value": 50.0,
            "step": 0.1,
            "unit": "°C",
            "icon": "mdi:thermometer",
        },
        # ... mais configurações
    },
    # ... outras plataformas
}
```

## Unique IDs

As bridge entities usam IDs únicos no formato:
```
{config_entry.entry_id}_{attribute_name}_bridge
```

Exemplo: `abc123_outdoor_temp_bridge`

## Entity IDs

O sensor binário principal usa o formato:
```
binary_sensor.{device_name}_ashrae_compliance
```

Onde `device_name` vem de `config_entry.data.get('name', 'adaptive_climate')`.

## Atualização de Atributos

### Processo de Atualização

1. Bridge entity recebe novo valor via UI
2. Obtém estado atual do sensor binário
3. Cria nova cópia dos atributos com valor modificado
4. Chama `hass.states.async_set` com novos atributos
5. Agenda atualização da própria entity

### Exemplo de Código

```python
async def _update_binary_sensor_attribute(self, new_value: Any) -> None:
    """Update the binary sensor attribute with a new value."""
    state = self._get_binary_sensor_state()
    if not state:
        return

    # Atualizar atributos
    attributes = dict(state.attributes)
    attributes[self._attribute_name] = new_value

    # Aplicar mudança
    self.hass.states.async_set(
        self._binary_sensor_entity_id,
        state.state,
        attributes,
    )
    
    self.async_schedule_update_ha_state()
```

## Monitoramento de Mudanças

As bridge entities escutam mudanças no sensor binário via event bus:

```python
self.hass.bus.async_listen(
    "state_changed",
    self._handle_binary_sensor_change,
)
```

## Uso no Frontend

### Config Flow
As bridge entities podem ser usadas em config flows para permitir configuração via UI.

### Controles
Aparecem na aba "Controles" do Home Assistant para ajuste em tempo real.

### Dashboard
Podem ser adicionadas a dashboards para monitoramento e controle.

## Benefícios

1. **Separação de Responsabilidades**: UI separada da lógica de negócio
2. **Flexibilidade**: Fácil adição de novos parâmetros configuráveis
3. **Consistência**: Todas as mudanças passam pelo mesmo canal
4. **Simplicidade**: Coordinator não precisa gerenciar estado de UI
5. **Testabilidade**: Bridge entities podem ser testadas independentemente

## Considerações de Performance

- Uso mínimo de recursos (sem polling)
- Atualizações baseadas em eventos
- Estado mantido apenas no sensor binário principal
- Sem persistência adicional em disco

## Extensibilidade

Para adicionar novas bridge entities:

1. Adicionar configuração em `BRIDGE_ENTITY_CONFIG`
2. Garantir que o atributo existe no sensor binário
3. As entities são criadas automaticamente

## Testes

Execute os testes com:
```bash
python -m pytest tests/test_bridge_entity.py -v
```

Os testes cobrem:
- Configuração das entidades
- Criação de entidades por plataforma
- Funcionalidade básica de cada tipo de entity
- Leitura e escrita de valores
