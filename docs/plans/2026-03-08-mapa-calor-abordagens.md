# Mapa de Calor de Abordagens por Indivíduo — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Exibir um mapa interativo com marcadores agrupados e camada de calor para todos os locais onde um indivíduo foi abordado, aparecendo abaixo do "Histórico de Abordagens" na tela de detalhe da pessoa.

**Architecture:** Frontend-only. O endpoint `GET /pessoas/{id}/abordagens` já retorna `latitude` e `longitude` por abordagem. Leaflet.js carregado via CDN renderiza o mapa; `IntersectionObserver` garante inicialização lazy (só quando o card entra na viewport). Marcadores agrupados via `leaflet.markercluster`, camada de calor via `leaflet-heat`.

**Tech Stack:** Leaflet.js 1.9.4, leaflet.markercluster 1.5.3, leaflet-heat 0.2.0 (todos CDN). Alpine.js (já existente). OpenStreetMap tiles (gratuito, sem API key).

---

## Arquivos envolvidos

- Modify: `frontend/index.html` — adicionar CDN scripts/links do Leaflet
- Modify: `frontend/js/pages/pessoa-detalhe.js` — card do mapa + lógica JS

---

### Task 1: Adicionar CDN do Leaflet ao `index.html`

**Files:**
- Modify: `frontend/index.html`

**Contexto:** O arquivo tem 60+ linhas. A `<head>` termina na linha 41. O Alpine.js está na linha 29. Adicionar CSS do Leaflet no `<head>` (antes de fechar `</head>`) e JS do Leaflet + plugins logo antes de `</body>`.

**Step 1: Abrir o arquivo e localizar os pontos de inserção**

Leia `frontend/index.html`. Localize:
- A tag `</head>` (fim do head — onde o CSS vai)
- A tag `</body>` (fim do body — onde os scripts JS vão)

**Step 2: Inserir CSS do Leaflet no `<head>`**

Adicione ANTES de `</head>`:

```html
  <!-- Leaflet CSS -->
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css" />
```

**Step 3: Inserir JS do Leaflet antes de `</body>`**

Adicione ANTES de `</body>`:

```html
  <!-- Leaflet JS + plugins -->
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
  <script src="https://unpkg.com/leaflet.heat@0.2.0/dist/leaflet-heat.js"></script>
```

**Step 4: Verificação manual**

Abra o app no browser. Abra o DevTools (F12) → Console. Verifique que não há erros de "L is not defined" ou "Failed to load resource". Acesse uma pessoa qualquer — a página deve carregar normalmente.

**Step 5: Commit**

```bash
git add frontend/index.html
git commit -m "feat(frontend): adicionar Leaflet.js + plugins via CDN"
```

---

### Task 2: Adicionar card HTML do mapa em `renderPessoaDetalhe`

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js` (linhas 183–222 são o "Histórico de Abordagens")

**Contexto:** A função `renderPessoaDetalhe` retorna uma string HTML. O card "Histórico de Abordagens" termina na linha 222 com `</div>`. O card do mapa deve ser inserido APÓS esse fechamento, antes da linha 223 (`</div>` do container pai).

**Step 1: Localizar ponto de inserção**

No arquivo `frontend/js/pages/pessoa-detalhe.js`, encontre este trecho (linha ~222):

```html
          </div>
        </div>
      </template>
```

O primeiro `</div>` fecha o card "Histórico de Abordagens". O segundo fecha o `div.space-y-4` pai. Inserir o novo card ENTRE eles.

**Step 2: Inserir o card do mapa**

Adicione após o fechamento do card "Histórico de Abordagens" e ANTES do `</div>` que fecha `div.space-y-4`:

```html
          <!-- Mapa de Abordagens -->
          <div x-show="pontosComLocalizacao.length > 0" class="card space-y-2 border-l-4 border-l-teal-500">
            <div class="flex items-center justify-between">
              <h3 class="text-sm font-semibold text-slate-300">
                Mapa de Abordagens (<span x-text="pontosComLocalizacao.length"></span>)
              </h3>
              <div class="flex gap-1">
                <button
                  @click="toggleModoMapa('marcadores')"
                  class="text-xs px-2 py-1 rounded transition-colors"
                  :class="modoMapa === 'marcadores' ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'"
                >
                  Marcadores
                </button>
                <button
                  @click="toggleModoMapa('calor')"
                  class="text-xs px-2 py-1 rounded transition-colors"
                  :class="modoMapa === 'calor' ? 'bg-teal-600 text-white' : 'bg-slate-700 text-slate-400 hover:text-white'"
                >
                  Calor
                </button>
              </div>
            </div>
            <div
              :id="'mapa-pessoa-' + ${pessoaId}"
              style="height: 350px; border-radius: 8px; z-index: 1;"
              class="w-full bg-slate-800"
            ></div>
          </div>
```

**Atenção:** A string `:id="'mapa-pessoa-' + ${pessoaId}"` usa template literal do JS que envolve o HTML — isso é correto pois `renderPessoaDetalhe` retorna uma template string (backtick). Verifique que o interpolation fica assim no contexto:

```javascript
// Correto — dentro de template literal JS com backticks:
`:id="'mapa-pessoa-' + ${pessoaId}"`
// O ${pessoaId} é resolvido pelo JS quando renderPessoaDetalhe(appState) é chamada
// e retorna um atributo Alpine como: :id="'mapa-pessoa-' + 123"
```

**Step 3: Verificação visual**

No browser, acesse uma pessoa COM abordagens que tenham lat/lon. O card "Mapa de Abordagens" deve aparecer abaixo do histórico com dois botões (Marcadores / Calor) e um div escuro de 350px. O mapa ainda não funciona (sem lógica JS ainda).

Para uma pessoa SEM abordagens com coordenadas, o card não deve aparecer (`x-show="pontosComLocalizacao.length > 0"`).

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): adicionar card HTML do mapa de abordagens"
```

---

### Task 3: Adicionar estado e lógica do mapa em `pessoaDetalhePage`

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js` (função `pessoaDetalhePage`, linhas 232–316)

**Contexto:** `pessoaDetalhePage(pessoaId)` retorna um objeto Alpine.js com estado e métodos. Precisamos adicionar:
1. Novas propriedades de estado ao objeto retornado
2. Dois novos métodos: `initMapa()` e `toggleModoMapa()`
3. Chamada ao IntersectionObserver após `carregarAbordagens()` completar

**Step 1: Adicionar propriedades de estado**

No objeto retornado por `pessoaDetalhePage`, após a linha `erro: null,`, adicione:

```javascript
    mapaInst: null,
    clusterLayer: null,
    heatLayer: null,
    modoMapa: 'marcadores',
    pontosComLocalizacao: [],
```

**Step 2: Adicionar método `initMapa()`**

Adicione após o método `carregarAbordagens()` (antes de `formatEndereco`):

```javascript
    initMapa() {
      const divId = `mapa-pessoa-${pessoaId}`;
      const div = document.getElementById(divId);
      if (!div || this.mapaInst) return;

      // Inicializa mapa centrado nos pontos
      this.mapaInst = L.map(div, { zoomControl: true });

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
      }).addTo(this.mapaInst);

      const pontos = this.pontosComLocalizacao;

      // Camada de marcadores agrupados
      this.clusterLayer = L.markerClusterGroup();
      for (const p of pontos) {
        const marker = L.marker([p.lat, p.lng]);
        marker.bindPopup(`
          <b>${p.dataHora}</b><br>
          ${p.endereco || 'Endereço não informado'}
        `);
        this.clusterLayer.addLayer(marker);
      }

      // Camada de calor
      const heatPontos = pontos.map(p => [p.lat, p.lng, 1]);
      this.heatLayer = L.heatLayer(heatPontos, {
        radius: 30,
        blur: 20,
        maxZoom: 17,
        gradient: { 0.4: 'blue', 0.6: 'cyan', 0.7: 'lime', 0.8: 'yellow', 1.0: 'red' },
      });

      // Modo inicial: marcadores
      this.mapaInst.addLayer(this.clusterLayer);

      // Ajusta zoom para cobrir todos os pontos
      if (pontos.length === 1) {
        this.mapaInst.setView([pontos[0].lat, pontos[0].lng], 15);
      } else {
        const bounds = L.latLngBounds(pontos.map(p => [p.lat, p.lng]));
        this.mapaInst.fitBounds(bounds, { padding: [30, 30] });
      }
    },

    toggleModoMapa(modo) {
      if (!this.mapaInst || modo === this.modoMapa) return;
      this.modoMapa = modo;
      if (modo === 'marcadores') {
        this.mapaInst.removeLayer(this.heatLayer);
        this.mapaInst.addLayer(this.clusterLayer);
      } else {
        this.mapaInst.removeLayer(this.clusterLayer);
        this.mapaInst.addLayer(this.heatLayer);
      }
    },
```

**Step 3: Atualizar `carregarAbordagens()` para extrair pontos e iniciar observer**

Ao final de `carregarAbordagens()`, após a linha `this.veiculos = Object.values(veiculosMap);`, adicione:

```javascript
        // Extrair pontos com coordenadas para o mapa
        this.pontosComLocalizacao = abordagens
          .filter(ab => ab.latitude != null && ab.longitude != null)
          .map(ab => ({
            lat: ab.latitude,
            lng: ab.longitude,
            dataHora: ab.data_hora
              ? new Date(ab.data_hora).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
              : (ab.criado_em ? new Date(ab.criado_em).toLocaleString('pt-BR', { dateStyle: 'short', timeStyle: 'short' }) : '—'),
            endereco: ab.endereco_texto || '',
          }));

        // Inicializar mapa lazy via IntersectionObserver
        if (this.pontosComLocalizacao.length > 0) {
          await this.$nextTick();
          const divId = `mapa-pessoa-${pessoaId}`;
          const div = document.getElementById(divId);
          if (div) {
            const observer = new IntersectionObserver((entries) => {
              if (entries[0].isIntersecting) {
                observer.disconnect();
                this.initMapa();
              }
            }, { threshold: 0.1 });
            observer.observe(div);
          }
        }
```

**Atenção:** O `carregarAbordagens()` já é um método `async`. O `await this.$nextTick()` é necessário para que o Alpine.js atualize o DOM (renderize o card do mapa) antes de tentar obter o `div` via `getElementById`.

**Step 4: Verificação manual completa**

1. Acesse o app e abra uma pessoa com abordagens que tenham coordenadas GPS
2. Role a página até o final — ao card "Mapa de Abordagens" entrar na tela, o mapa deve carregar
3. Verifique que os marcadores aparecem agrupados (cluster) no modo padrão
4. Clique em um marcador isolado — deve abrir popup com data/hora e endereço
5. Clique no botão "Calor" — marcadores somem, gradiente de calor aparece
6. Clique em "Marcadores" — volta ao modo com pins
7. Acesse uma pessoa sem coordenadas — o card "Mapa de Abordagens" NÃO deve aparecer

**Step 5: Verificar no DevTools**

Abra F12 → Console. Não deve haver erros. Verifique:
- `L` está definido (Leaflet carregou)
- `L.markerClusterGroup` está definido (plugin cluster carregou)
- `L.heatLayer` está definido (plugin heat carregou)

**Step 6: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): implementar mapa de calor lazy-loaded no detalhe da pessoa"
```

---

## Notas de implementação

### Sobre `data_hora` vs `criado_em`

O schema `AbordagemRead` pode retornar `data_hora` (timestamp da abordagem) ou `criado_em` (timestamp de cadastro). Inspecione a resposta real de `GET /pessoas/{id}/abordagens` no DevTools (Network tab) para confirmar qual campo usar no popup. O código usa `ab.data_hora` com fallback para `ab.criado_em`.

### Sobre `z-index` do Leaflet

O CSS do Leaflet usa `z-index` alto internamente. O container do mapa tem `z-index: 1` para isolar do restante da página. Se o mapa aparecer sobre o header fixo (`z-50`), adicione `isolation: isolate` no card pai.

### Sobre modo offline

O PWA tem service worker que bloqueia recursos externos. Os tiles do OSM são carregados de `tile.openstreetmap.org` e falharão offline. O mapa mostrará tiles cinzas, mas os markers/heat ainda funcionarão. Isso é comportamento aceitável (tiles são visuais, não funcionais).
