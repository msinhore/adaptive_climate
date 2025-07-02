# Como Encontrar o Config Entry ID

## Método 1: Via Developer Tools
1. Vá para **Developer Tools** > **States**
2. Procure por entidades que começam com `sensor.adaptive_climate_`
3. Clique em uma delas e veja os atributos
4. O `config_entry_id` aparecerá nos device info

## Método 2: Via Template no Developer Tools
Cole este template no **Developer Tools** > **Template**:

```yaml
{% for entry_id, entry in states.integration_entries.items() %}
  {% if entry.domain == "adaptive_climate" %}
    Config Entry ID: {{ entry_id }}
    Name: {{ entry.title }}
  {% endif %}
{% endfor %}
```

## Método 3: Via Logs
1. Ative o log DEBUG para adaptive_climate no configuration.yaml:
```yaml
logger:
  default: info
  logs:
    custom_components.adaptive_climate: debug
```
2. Reinicie o HA
3. Procure no log por "Setting up Adaptive Climate" - o ID aparecerá

## Método 4: Nos Arquivos do HA
O ID está em `.storage/core.config_entries` (não recomendado editar)
