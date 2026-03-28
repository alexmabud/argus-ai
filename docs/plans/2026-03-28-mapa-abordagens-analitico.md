# Mapa de Abordagens no Analítico — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Adicionar um mapa Leaflet na página analítica que exibe os pontos geográficos de todas as abordagens do dia selecionado no calendário.

**Architecture:** Novo endpoint dedicado `GET /analytics/abordagens-do-dia?data=YYYY-MM-DD` retorna `[{lat, lng, horario}]`. O frontend chama esse endpoint em paralelo com `pessoas-do-dia` via `Promise.all`. O mapa usa MarkerCluster + HeatLayer, o mesmo padrão já existente em `pessoa-detalhe.js`. Se não houver coordenadas, exibe mensagem de aviso no lugar do mapa.

**Tech Stack:** Python/FastAPI, SQLAlchemy async, Leaflet + MarkerCluster + Leaflet.heat, Alpine.js

---

### Task 1: Service — método `abordagens_do_dia`

**Files:**
- Modify: `app/services/analytics_service.py` (após o método `pessoas_do_dia`, ~linha 446)
- Test: `tests/unit/test_analytics_service.py`

**Step 1: Escrever o teste unitário falhando**

Adicionar ao final de `tests/unit/test_analytics_service.py`:

```python
class TestAbordacoesdoDia:
    """Testes para AnalyticsService.abordagens_do_dia()."""

    @pytest.fixture
    def service(self):
        """Cria instância de AnalyticsService com session mock."""
        db = AsyncMock()
        return AnalyticsService(db)

    async def test_retorna_pontos_com_coordenadas(self, service):
        """Deve retornar lista de pontos com lat, lng e horario."""
        mock_result = MagicMock()
        mock_result.all.return_value = [
            (-23.5505, -46.6333, datetime(2026, 3, 28, 14, 32, tzinfo=UTC)),
            (-23.5510, -46.6340, datetime(2026, 3, 28, 15, 10, tzinfo=UTC)),
        ]
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.abordagens_do_dia(guarnicao_id=1, data="2026-03-28")

        assert len(result) == 2
        assert result[0]["lat"] == -23.5505
        assert result[0]["lng"] == -46.6333
        assert result[0]["horario"] == "14:32"

    async def test_sem_abordagens_retorna_lista_vazia(self, service):
        """Deve retornar lista vazia quando não há abordagens com localização."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        service.db.execute = AsyncMock(return_value=mock_result)

        result = await service.abordagens_do_dia(guarnicao_id=1, data="2026-03-28")

        assert result == []
```

**Step 2: Rodar o teste para confirmar que falha**

```bash
pytest tests/unit/test_analytics_service.py::TestAbordacoesdoDia -v
```

Esperado: `FAILED` com `AttributeError: 'AnalyticsService' object has no attribute 'abordagens_do_dia'`

**Step 3: Implementar o método**

Adicionar em `app/services/analytics_service.py` após o método `pessoas_do_dia` (após a linha ~446):

```python
    async def abordagens_do_dia(self, guarnicao_id: int, data: str) -> list[dict]:
        """Retorna pontos geográficos das abordagens de um dia específico.

        Retorna apenas abordagens que possuem coordenadas GPS registradas.
        Usado para renderizar o mapa no dashboard analítico ao selecionar
        um dia no calendário.

        Args:
            guarnicao_id: ID da guarnição para filtro multi-tenant.
            data: Data no formato "YYYY-MM-DD" (ex: "2026-03-28").

        Returns:
            Lista de dicionários com lat (float), lng (float) e horario (str HH:MM).
        """
        data_obj = date.fromisoformat(data)

        query = (
            select(
                Abordagem.latitude,
                Abordagem.longitude,
                Abordagem.data_hora,
            )
            .where(
                Abordagem.guarnicao_id == guarnicao_id,
                Abordagem.ativo,
                func.date(Abordagem.data_hora) == data_obj,
                Abordagem.latitude.isnot(None),
                Abordagem.longitude.isnot(None),
            )
            .order_by(Abordagem.data_hora)
        )
        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "lat": float(row[0]),
                "lng": float(row[1]),
                "horario": row[2].strftime("%H:%M") if row[2] else "—",
            }
            for row in rows
        ]
```

**Step 4: Rodar os testes para confirmar que passam**

```bash
pytest tests/unit/test_analytics_service.py::TestAbordacoesdoDia -v
```

Esperado: `2 passed`

**Step 5: Commit**

```bash
git add app/services/analytics_service.py tests/unit/test_analytics_service.py
git commit -m "feat(analytics): método abordagens_do_dia retorna pontos geográficos por dia"
```

---

### Task 2: Router — endpoint `GET /analytics/abordagens-do-dia`

**Files:**
- Modify: `app/api/v1/analytics.py` (após o handler `pessoas_do_dia`, ~linha 174)
- Test: `tests/integration/test_api_analytics.py`

**Step 1: Verificar como os testes de integração de analytics são estruturados**

Ler `tests/integration/test_api_analytics.py` para entender fixtures disponíveis (client, token, guarnicao, abordagem com coordenadas).

**Step 2: Escrever o teste de integração falhando**

Adicionar ao final de `tests/integration/test_api_analytics.py`:

```python
class TestAbordagensDoDia:
    """Testes de integração para GET /analytics/abordagens-do-dia."""

    async def test_retorna_pontos_do_dia(self, client, token_headers, abordagem_com_localizacao):
        """Deve retornar pontos do dia com lat, lng e horario."""
        data = abordagem_com_localizacao.data_hora.date().isoformat()
        resp = await client.get(
            f"/api/v1/analytics/abordagens-do-dia?data={data}",
            headers=token_headers,
        )
        assert resp.status_code == 200
        pontos = resp.json()
        assert isinstance(pontos, list)
        assert len(pontos) >= 1
        assert "lat" in pontos[0]
        assert "lng" in pontos[0]
        assert "horario" in pontos[0]

    async def test_dia_sem_abordagens_retorna_lista_vazia(self, client, token_headers):
        """Deve retornar lista vazia para dia sem abordagens."""
        resp = await client.get(
            "/api/v1/analytics/abordagens-do-dia?data=2000-01-01",
            headers=token_headers,
        )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_requer_autenticacao(self, client):
        """Deve retornar 401 sem token."""
        resp = await client.get("/api/v1/analytics/abordagens-do-dia?data=2026-03-28")
        assert resp.status_code == 401
```

> **Nota:** Se não existir a fixture `abordagem_com_localizacao`, crie-a no arquivo de conftest do módulo de integração — uma abordagem com `latitude=-23.5505, longitude=-46.6333` associada à guarnição do usuário de teste.

**Step 3: Rodar para confirmar que falha**

```bash
pytest tests/integration/test_api_analytics.py::TestAbordagensDoDia -v
```

Esperado: `FAILED` com erro 404 (endpoint não existe ainda).

**Step 4: Implementar o handler**

Adicionar em `app/api/v1/analytics.py` após o handler `pessoas_do_dia` (~linha 174):

```python
@router.get("/abordagens-do-dia")
async def abordagens_do_dia(
    data: date = Query(...),
    db: AsyncSession = Depends(get_db),
    user: Usuario = Depends(get_current_user),
) -> list[dict]:
    """Retorna pontos geográficos das abordagens de um dia específico.

    Usado pelo mapa no dashboard analítico para exibir onde foram realizadas
    as abordagens do dia selecionado no calendário.

    Args:
        data: Data no formato YYYY-MM-DD.
        db: Sessão do banco de dados.
        user: Usuário autenticado.

    Returns:
        Lista com lat, lng e horario (HH:MM) de cada abordagem com localização.
    """
    service = AnalyticsService(db)
    return await service.abordagens_do_dia(user.guarnicao_id, str(data))
```

**Step 5: Rodar os testes para confirmar que passam**

```bash
pytest tests/integration/test_api_analytics.py::TestAbordagensDoDia -v
```

Esperado: `3 passed`

**Step 6: Commit**

```bash
git add app/api/v1/analytics.py tests/integration/test_api_analytics.py
git commit -m "feat(analytics): endpoint GET /abordagens-do-dia para mapa do analítico"
```

---

### Task 3: Frontend — estado e métodos no `dashboardPage()`

**Files:**
- Modify: `frontend/js/pages/dashboard.js`

O arquivo tem duas seções: HTML (função `dashboardPageTemplate()`) e JS (função `dashboardPage()`). As mudanças desta task são apenas na parte JS.

**Step 1: Adicionar estado novo**

Localizar o bloco de estado do calendário (~linha 301) em `dashboardPage()`:

```js
    diasComAbordagem: [],
    pessoasDoDia: [],
```

Substituir por:

```js
    diasComAbordagem: [],
    pessoasDoDia: [],

    // Mapa do dia
    pontosMapaDia: [],
    mapaAnaliticoInst: null,
    _mapaAnaliticoObserver: null,
    modoMapaAnalitico: 'marcadores',
    clusterAnalitico: null,
    heatAnalitico: null,
```

**Step 2: Atualizar `selecionarDia()` para carregar pontos em paralelo**

Localizar o método `selecionarDia` (~linha 374):

```js
    async selecionarDia(dia) {
      this.diaSelecionado = dia;
      this._mesSelec = this.mesCalendarioAtual;
      this._anoSelec = this.anoCalendarioAtual;
      const dataStr = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}-${String(dia).padStart(2,'0')}`;
      await this.carregarPessoasDoDia(dataStr);
    },
```

Substituir por:

```js
    async selecionarDia(dia) {
      this.diaSelecionado = dia;
      this._mesSelec = this.mesCalendarioAtual;
      this._anoSelec = this.anoCalendarioAtual;
      const dataStr = `${this.anoCalendarioAtual}-${String(this.mesCalendarioAtual).padStart(2,'0')}-${String(dia).padStart(2,'0')}`;
      this.destroyMapaAnalitico();
      await Promise.all([
        this.carregarPessoasDoDia(dataStr),
        this.carregarPontosMapaDia(dataStr),
      ]);
    },
```

**Step 3: Adicionar os novos métodos após `carregarPessoasDoDia`**

Localizar o final do método `carregarPessoasDoDia` (~linha 394) e adicionar após ele:

```js
    async carregarPontosMapaDia(data) {
      this.pontosMapaDia = await api.get(`/analytics/abordagens-do-dia?data=${data}`).catch(() => []);
      if (this.pontosMapaDia.length > 0) {
        await this.$nextTick();
        await this.setupMapaAnaliticoObserver();
      }
    },

    async setupMapaAnaliticoObserver() {
      if (this._mapaAnaliticoObserver) {
        this._mapaAnaliticoObserver.disconnect();
        this._mapaAnaliticoObserver = null;
      }
      await new Promise(r => setTimeout(r, 0));
      const div = document.getElementById('mapa-analitico-dia');
      if (!div) return;
      const observer = new IntersectionObserver((entries) => {
        if (entries[0].isIntersecting) {
          observer.disconnect();
          this.initMapaAnalitico();
        }
      }, { threshold: 0.1 });
      observer.observe(div);
      this._mapaAnaliticoObserver = observer;
    },

    initMapaAnalitico() {
      const div = document.getElementById('mapa-analitico-dia');
      if (!div || this.mapaAnaliticoInst) return;
      if (typeof L === 'undefined') return;

      this.mapaAnaliticoInst = L.map(div, { zoomControl: true });
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap',
        maxZoom: 19,
      }).addTo(this.mapaAnaliticoInst);

      const pontos = this.pontosMapaDia;

      this.clusterAnalitico = L.markerClusterGroup();
      pontos.forEach(p => {
        const marker = L.marker([p.lat, p.lng]);
        marker.bindPopup(`<span style="font-family:monospace;font-size:12px;">${p.horario}</span>`);
        this.clusterAnalitico.addLayer(marker);
      });

      const heatPontos = pontos.map(p => [p.lat, p.lng, 1]);
      this.heatAnalitico = L.heatLayer(heatPontos, { radius: 30, blur: 20, maxZoom: 17 });

      this.mapaAnaliticoInst.addLayer(this.clusterAnalitico);

      if (pontos.length === 1) {
        this.mapaAnaliticoInst.setView([pontos[0].lat, pontos[0].lng], 15);
      } else {
        const bounds = L.latLngBounds(pontos.map(p => [p.lat, p.lng]));
        this.mapaAnaliticoInst.fitBounds(bounds, { padding: [30, 30] });
      }

      requestAnimationFrame(() => {
        this.mapaAnaliticoInst && this.mapaAnaliticoInst.invalidateSize({ animate: false });
        setTimeout(() => this.mapaAnaliticoInst && this.mapaAnaliticoInst.invalidateSize({ animate: false }), 200);
        setTimeout(() => this.mapaAnaliticoInst && this.mapaAnaliticoInst.invalidateSize({ animate: false }), 500);
      });
    },

    toggleModoMapaAnalitico(modo) {
      if (!this.mapaAnaliticoInst || modo === this.modoMapaAnalitico) return;
      this.modoMapaAnalitico = modo;
      if (modo === 'marcadores') {
        this.mapaAnaliticoInst.removeLayer(this.heatAnalitico);
        this.mapaAnaliticoInst.addLayer(this.clusterAnalitico);
      } else {
        this.mapaAnaliticoInst.removeLayer(this.clusterAnalitico);
        this.mapaAnaliticoInst.addLayer(this.heatAnalitico);
      }
    },

    destroyMapaAnalitico() {
      if (this._mapaAnaliticoObserver) {
        this._mapaAnaliticoObserver.disconnect();
        this._mapaAnaliticoObserver = null;
      }
      if (this.mapaAnaliticoInst) {
        this.mapaAnaliticoInst.remove();
        this.mapaAnaliticoInst = null;
        this.clusterAnalitico = null;
        this.heatAnalitico = null;
      }
      this.pontosMapaDia = [];
      this.modoMapaAnalitico = 'marcadores';
    },
```

**Step 4: Chamar `destroyMapaAnalitico()` ao trocar de mês**

Localizar o método `mesMenos()` e `mesMais()` (que chamam `carregarDiasComAbordagem`). Adicionar `this.destroyMapaAnalitico()` antes de `this.diaSelecionado = null` em ambos. Exemplo para `mesMenos`:

```js
    async mesMenos() {
      this.destroyMapaAnalitico();   // <-- adicionar esta linha
      this.diaSelecionado = null;
      // ... resto do método inalterado
    },
```

Fazer o mesmo em `mesMais()`.

**Step 5: Commit**

```bash
git add frontend/js/pages/dashboard.js
git commit -m "feat(dashboard): estado e métodos para mapa de abordagens do dia"
```

---

### Task 4: Frontend — HTML do bloco de mapa

**Files:**
- Modify: `frontend/js/pages/dashboard.js` (função `dashboardPageTemplate()`, seção HTML)

**Step 1: Localizar o ponto de inserção**

No HTML da função `dashboardPageTemplate()`, localizar o fechamento do card "Pessoas Abordadas por Dia" (~linha 238):

```html
            </div>
          </div>

          <!-- Pessoas Recorrentes -->
```

**Step 2: Inserir o bloco do mapa entre o card de pessoas e o card de recorrentes**

```html
            </div>
          </div>

          <!-- Mapa de Abordagens do Dia -->
          <div x-show="diaSelecionado !== null && !loadingPessoas"
               class="glass-card"
               style="padding:16px;border-radius:4px;">
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
              <h3 style="font-family:var(--font-display);font-size:12px;font-weight:500;color:var(--color-text-muted);text-transform:uppercase;letter-spacing:0.08em;margin:0;">
                Localização das Abordagens
              </h3>
              <div x-show="pontosMapaDia.length > 0" style="display:flex;gap:0.25rem;">
                <button
                  @click="toggleModoMapaAnalitico('marcadores')"
                  style="font-size:0.75rem;padding:0.25rem 0.5rem;border-radius:4px;border:none;cursor:pointer;transition:all 0.2s;"
                  :style="modoMapaAnalitico === 'marcadores' ? 'background:#14B8A6;color:var(--color-bg);' : 'background:var(--color-surface);color:var(--color-text-muted);border:1px solid var(--color-border);'"
                >Marcadores</button>
                <button
                  @click="toggleModoMapaAnalitico('calor')"
                  style="font-size:0.75rem;padding:0.25rem 0.5rem;border-radius:4px;border:none;cursor:pointer;transition:all 0.2s;"
                  :style="modoMapaAnalitico === 'calor' ? 'background:#14B8A6;color:var(--color-bg);' : 'background:var(--color-surface);color:var(--color-text-muted);border:1px solid var(--color-border);'"
                >Calor</button>
              </div>
            </div>

            <!-- Sem localização -->
            <div x-show="pontosMapaDia.length === 0"
                 style="font-family:var(--font-data);font-size:11px;color:var(--color-text-dim);text-align:center;padding:16px 0;text-transform:uppercase;letter-spacing:0.08em;">
              Sem dados de localização para este dia.
            </div>

            <!-- Mapa -->
            <div x-show="pontosMapaDia.length > 0">
              <div id="mapa-analitico-dia"
                   style="width:100%;height:280px;border-radius:4px;background:var(--color-surface);z-index:1;"></div>
            </div>
          </div>

          <!-- Pessoas Recorrentes -->
```

**Step 3: Verificar visualmente no browser**

1. `make dev` (ou `docker compose up`)
2. Abrir o analítico
3. Clicar em um dia com abordagens que tenham GPS → mapa deve aparecer com marcadores
4. Clicar em um dia sem coordenadas → deve mostrar "Sem dados de localização para este dia."
5. Trocar de mês → mapa some sem erros no console
6. Alternar botões Marcadores / Calor → deve funcionar

**Step 4: Commit**

```bash
git add frontend/js/pages/dashboard.js
git commit -m "feat(dashboard): bloco HTML do mapa de abordagens do dia no analítico"
```

---

### Task 5: Lint + testes completos

**Step 1: Rodar lint**

```bash
make lint
```

Esperado: sem erros de ruff ou mypy nos arquivos alterados.

**Step 2: Rodar todos os testes**

```bash
make test
```

Esperado: todos passando.

**Step 3: Commit final (se necessário após correções de lint)**

```bash
git add -p
git commit -m "fix(analytics): ajustes de lint pós-implementação do mapa do analítico"
```
