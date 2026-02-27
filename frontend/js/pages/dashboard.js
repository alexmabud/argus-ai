/**
 * Página de dashboard analítico — Argus AI.
 *
 * Cards de resumo operacional, mapa de calor (Leaflet),
 * gráfico de horários de pico (canvas), tabela de
 * pessoas mais abordadas e métricas RAG.
 */
function renderDashboard() {
  return `
    <div x-data="dashboardPage()" x-init="load()" class="space-y-5">
      <h2 class="text-lg font-bold text-slate-100">Dashboard</h2>

      <!-- Loading -->
      <div x-show="loading" class="flex justify-center py-12">
        <span class="spinner"></span>
      </div>

      <template x-if="!loading">
        <div class="space-y-5">
          <!-- Cards resumo -->
          <div class="grid grid-cols-2 gap-3">
            <div class="card text-center">
              <p class="text-2xl font-bold text-blue-400" x-text="resumo.total_abordagens || 0"></p>
              <p class="text-xs text-slate-400">Abordagens</p>
            </div>
            <div class="card text-center">
              <p class="text-2xl font-bold text-green-400" x-text="resumo.total_pessoas_distintas || 0"></p>
              <p class="text-xs text-slate-400">Pessoas distintas</p>
            </div>
            <div class="card text-center">
              <p class="text-2xl font-bold text-yellow-400" x-text="resumo.media_abordagens_dia || 0"></p>
              <p class="text-xs text-slate-400">Média/dia</p>
            </div>
            <div class="card text-center">
              <p class="text-2xl font-bold text-purple-400" x-text="resumo.periodo_dias || 30"></p>
              <p class="text-xs text-slate-400">Dias</p>
            </div>
          </div>

          <!-- Gráfico horários de pico -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Horários de Pico</h3>
            <div class="flex items-end gap-1 h-32">
              <template x-for="h in horariosCompletos" :key="h.hora">
                <div class="flex-1 flex flex-col items-center gap-1">
                  <div class="w-full rounded-t transition-all"
                       :style="'height: ' + (h.total > 0 ? Math.max(8, (h.total / maxHorario) * 100) : 2) + 'px'"
                       :class="h.total > 0 ? 'bg-blue-500' : 'bg-slate-700'">
                  </div>
                  <span class="text-[9px] text-slate-500" x-text="h.hora" x-show="h.hora % 3 === 0"></span>
                </div>
              </template>
            </div>
          </div>

          <!-- Pessoas mais abordadas -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-3">Pessoas Recorrentes</h3>
            <div x-show="pessoas.length === 0" class="text-xs text-slate-500 text-center py-4">
              Nenhum dado disponível.
            </div>
            <div class="space-y-2">
              <template x-for="(p, i) in pessoas" :key="p.id">
                <div class="flex items-center justify-between text-sm">
                  <div class="flex items-center gap-2">
                    <span class="text-xs text-slate-500 w-5" x-text="(i+1) + '.'"></span>
                    <div>
                      <p class="text-slate-200" x-text="p.nome"></p>
                      <p x-show="p.apelido" class="text-xs text-slate-500" x-text="p.apelido"></p>
                    </div>
                  </div>
                  <div class="text-right">
                    <p class="text-blue-400 font-medium" x-text="p.total_abordagens + 'x'"></p>
                    <p x-show="p.ultima_abordagem" class="text-[10px] text-slate-500"
                       x-text="new Date(p.ultima_abordagem).toLocaleDateString('pt-BR')"></p>
                  </div>
                </div>
              </template>
            </div>
          </div>

          <!-- Métricas RAG -->
          <div class="card">
            <h3 class="text-sm font-semibold text-slate-300 mb-2">Qualidade RAG</h3>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p class="text-slate-500">Ocorrências</p>
                <p class="text-slate-200 font-medium" x-text="rag.total_ocorrencias || 0"></p>
              </div>
              <div>
                <p class="text-slate-500">Indexadas</p>
                <p class="text-slate-200 font-medium" x-text="rag.ocorrencias_indexadas || 0"></p>
              </div>
            </div>
            <div class="mt-2 bg-slate-700 rounded-full h-2 overflow-hidden">
              <div class="bg-green-500 h-2 rounded-full transition-all"
                   :style="'width: ' + (rag.total_ocorrencias > 0 ? (rag.ocorrencias_indexadas / rag.total_ocorrencias * 100) : 0) + '%'">
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>
  `;
}

function dashboardPage() {
  return {
    loading: true,
    resumo: {},
    horarios: [],
    pessoas: [],
    rag: {},
    maxHorario: 1,

    get horariosCompletos() {
      const map = {};
      for (let h = 0; h < 24; h++) map[h] = { hora: h, total: 0 };
      for (const item of this.horarios) map[item.hora] = item;
      return Object.values(map);
    },

    async load() {
      try {
        const [resumo, horarios, pessoas, rag] = await Promise.all([
          api.get("/analytics/resumo").catch(() => ({})),
          api.get("/analytics/horarios-pico").catch(() => []),
          api.get("/analytics/pessoas-recorrentes?limit=10").catch(() => []),
          api.get("/analytics/rag-qualidade").catch(() => ({})),
        ]);
        this.resumo = resumo;
        this.horarios = horarios;
        this.pessoas = pessoas;
        this.rag = rag;
        this.maxHorario = Math.max(1, ...horarios.map((h) => h.total));
      } catch {
        showToast("Erro ao carregar dashboard", "error");
      } finally {
        this.loading = false;
      }
    },
  };
}
