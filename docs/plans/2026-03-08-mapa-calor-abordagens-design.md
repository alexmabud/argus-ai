# Design: Mapa de Calor de Abordagens por Indivíduo

**Data:** 2026-03-08
**Status:** Aprovado
**Escopo:** Frontend only — sem mudanças no backend

---

## Contexto

Na tela de detalhe de um indivíduo (`pessoa-detalhe`), exibir um mapa interativo com todos os locais onde aquela pessoa foi abordada. O mapa aparece abaixo do "Histórico de Abordagens" e é atualizado automaticamente a cada nova abordagem registrada.

## Infraestrutura existente (sem alterações)

- Model `Abordagem` já possui `latitude` (float), `longitude` (float) e `localizacao` (PostGIS Geography POINT)
- Endpoint `GET /pessoas/{pessoa_id}/abordagens` já retorna lat/lon por abordagem
- Frontend usa Alpine.js + Tailwind, sem build step
- Projeto já usa OpenStreetMap via Nominatim para geocodificação reversa

## Decisões de design

| Decisão | Escolha | Motivo |
|---------|---------|--------|
| Biblioteca de mapas | Leaflet.js via CDN | Open source, leve, offline-friendly, sem API key |
| Clustering | leaflet.markercluster | Agrupa pins próximos, evita poluição visual |
| Heatmap | leaflet-heat | Gradiente de densidade, mesmo conjunto de pontos |
| Carregamento | Lazy via IntersectionObserver | PWA mobile-first — não bloqueia carregamento da página |
| Tiles | OpenStreetMap (gratuito) | Consistente com Nominatim já usado no projeto |
| Backend | Sem mudanças | Endpoint existente já fornece os dados necessários |

## Componente visual

```
┌─────────────────────────────────────┐
│ 📍 Mapa de Abordagens               │
│  [toggle: Marcadores | Calor]       │
├─────────────────────────────────────┤
│                                     │
│   [mapa Leaflet 350px altura]       │
│   - tiles OpenStreetMap             │
│   - marcadores agrupados (cluster)  │
│   - layer de calor sobreposta       │
│                                     │
└─────────────────────────────────────┘
```

## Comportamento

- **Lazy init:** `IntersectionObserver` inicializa o mapa só quando o card entra na viewport; `observer.disconnect()` após primeira inicialização
- **Toggle:** Alpine.js controla `modoMapa: 'marcadores' | 'calor'` via `map.addLayer()` / `map.removeLayer()`
- **Popup ao clicar:** data/hora + endereço da abordagem (sem link)
- **Fit automático:** `map.fitBounds()` centraliza no conjunto de pontos da pessoa
- **Sem coordenadas:** abordagens sem lat/lon são ignoradas silenciosamente; se nenhuma tiver coordenadas, o card não é renderizado
- **Atualização:** página já recarrega dados após nova abordagem — mapa reinicializa com pontos atualizados

## Fluxo de dados

```
pessoa-detalhe.js
  └── carrega abordagens via GET /pessoas/{id}/abordagens (já existente)
        └── filtra: abordagens com latitude && longitude
              └── Leaflet:
                    ├── MarkerClusterGroup (marcadores clicáveis)
                    └── HeatLayer (gradiente de densidade)
```

## Arquivos modificados

| Arquivo | Mudança |
|---------|---------|
| `frontend/index.html` | +3 tags `<script>` CDN: leaflet, markercluster, leaflet-heat |
| `frontend/js/pages/pessoa-detalhe.js` | Novo card "Mapa de Abordagens" com lógica lazy-load |

**Nenhum arquivo novo criado. Nenhuma mudança no backend.**

## Bibliotecas CDN

```html
<!-- Leaflet CSS -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<!-- Leaflet JS -->
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<!-- MarkerCluster -->
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<!-- Leaflet Heat -->
<script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
```
