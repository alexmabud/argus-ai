# Agrupamento Veículos + Fotos e Label Abordagem Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Agrupar as seções "Veículos" e "Fotos de Veículos" em um container pai unificado "Veículos Vinculados ao Abordado", e adicionar label de veículo no histórico de abordagens.

**Architecture:** Todas as mudanças ficam em `frontend/js/pages/pessoa-detalhe.js`. O container pai agrupa visualmente veículos (com cores cíclicas PALETTE existente) e fotos de veículos (seção unificada, sem per-vehicle — `FotoRead` não tem `veiculo_id`). O label no histórico é uma mudança de template simples. Nenhuma mudança de backend.

**Tech Stack:** Alpine.js, Tailwind CSS, HTML template strings em JS.

**Limitação de dados:** `FotoRead` não possui `veiculo_id`, apenas `abordagem_id`. Portanto fotos não podem ser coloridas por veículo específico — ficam num grid unificado dentro do container pai. Para coloração per-veículo seria necessária mudança de backend (fora de escopo).

---

### Task 1: Criar container pai "Veículos Vinculados ao Abordado"

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Contexto:** Atualmente existem dois cards de seção separados:
- `<div x-show="veiculos.length > 0" class="card space-y-2 border-l-4 border-l-green-600">` — Veículos
- `<div x-show="fotosVeiculos.length > 0" class="card space-y-2 border-l-4 border-l-teal-500">` — Fotos de Veículos

O objetivo é envolvê-los num container pai. O container PAI usa `border-l-4 border-l-emerald-500` (cor de seção do grupo). Os dois cards internos perdem a borda de seção própria (serão estilizados como sub-seções dentro do pai).

**Step 1: Leia o arquivo atual completo**

```bash
# Localize as linhas exatas dos dois cards antes de editar
# Seção Veículos: x-show="veiculos.length > 0"
# Seção Fotos de Veículos: x-show="fotosVeiculos.length > 0"
```

**Step 2: Envolva os dois cards em um container pai**

Substitua as duas seções separadas por esta estrutura unificada:

```html
          <!-- Veículos Vinculados ao Abordado (container pai) -->
          <div x-show="veiculos.length > 0 || fotosVeiculos.length > 0" class="card space-y-3 border-l-4 border-l-emerald-500">
            <h3 class="text-sm font-semibold text-slate-300">Veículos Vinculados ao Abordado</h3>

            <!-- Lista de veículos -->
            <div x-show="veiculos.length > 0" class="space-y-2">
              <template x-for="(v, idx) in veiculos" :key="v.id">
                <div class="flex items-center border border-slate-700/40 border-l-4 rounded-lg p-3" :class="PALETTE[idx % PALETTE.length]">
                  <div class="flex items-start justify-between gap-2 w-full">
                    <div>
                      <span class="font-mono font-bold text-slate-100 tracking-wider" x-text="formatPlaca(v.placa)"></span>
                      <p x-show="v.modelo || v.cor || v.ano" class="text-xs text-slate-400"
                         x-text="[v.modelo, v.cor, v.ano].filter(Boolean).join(' · ')"></p>
                    </div>
                    <span x-show="v.criado_em" class="text-xs text-slate-500 shrink-0"
                          x-text="'Cadastrado em ' + new Date(v.criado_em).toLocaleDateString('pt-BR')"></span>
                  </div>
                </div>
              </template>
            </div>

            <!-- Fotos de veículos -->
            <div x-show="fotosVeiculos.length > 0" class="space-y-2">
              <p class="text-xs font-semibold text-slate-500">
                Fotos de Veículos Vinculados ao Abordado (<span x-text="fotosVeiculos.length"></span>)
              </p>
              <div class="grid grid-cols-3 gap-2">
                <template x-for="foto in fotosVeiculos" :key="foto.id">
                  <div>
                    <div class="relative">
                      <img :src="foto.arquivo_url" class="w-full h-28 object-cover rounded-lg" loading="lazy"
                           @click="fotoAmpliada = foto.arquivo_url">
                      <span class="absolute bottom-1 left-1 bg-black/60 text-[10px] text-slate-300 px-1 rounded"
                            x-text="foto.tipo || 'foto'"></span>
                    </div>
                    <p class="text-xs text-slate-400 text-center mt-1"
                       x-show="foto.criado_em"
                       x-text="foto.criado_em ? new Date(foto.criado_em).toLocaleDateString('pt-BR') : ''"></p>
                  </div>
                </template>
              </div>
            </div>
          </div>
```

**Atenção:** Remova os dois cards originais (`<!-- Veículos vinculados -->` e `<!-- Fotos de veículos -->`) e substitua pelo bloco acima. Não altere nenhum outro card.

**Step 3: Self-review**
- [ ] Os dois cards originais (veículos e fotos de veículos) foram removidos
- [ ] Existe um único container pai com `border-l-4 border-l-emerald-500`
- [ ] `x-show` do pai usa `veiculos.length > 0 || fotosVeiculos.length > 0`
- [ ] Título do pai: "Veículos Vinculados ao Abordado"
- [ ] Sub-título das fotos: "Fotos de Veículos Vinculados ao Abordado (N)"
- [ ] Veículos mantêm cores cíclicas com PALETTE[idx % PALETTE.length]
- [ ] Fotos mantêm grid 3 colunas, modal de ampliação, data abaixo
- [ ] Nenhum outro card foi alterado (Endereços, Abordagens, Relacionamentos, Fotos de pessoa)

**Step 4: Commit**

```bash
cd c:/projetos/argus_ai
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): agrupar veículos e fotos em container pai 'Veículos Vinculados ao Abordado'"
```

---

### Task 2: Label "Veículo Vinculado à Abordagem:" no histórico

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js`

**Contexto:** No histórico de abordagens, cada card de abordagem tem uma seção que lista os veículos daquela abordagem. Atualmente o template é:

```html
<!-- Veículos nesta abordagem (um por linha, sem dono) -->
<div x-show="ab.veiculos?.length > 0" class="space-y-0.5">
  <template x-for="av in ab.veiculos" :key="av.id">
    <div class="text-xs text-slate-400"
         x-text="[formatPlaca(av.placa), av.modelo, av.cor, av.ano].filter(Boolean).join(' · ')"></div>
  </template>
</div>
```

Queremos adicionar um label antes de cada veículo: "Veículo Vinculado à Abordagem: AAA-1111 · Gol · Branco · 2020"

**Step 1: Leia o arquivo atual**

**Step 2: Substitua o template de veículos no histórico**

Localize a seção `<!-- Veículos nesta abordagem (um por linha, sem dono) -->` e substitua o `<div>` interno do `x-for` por:

```html
<div x-show="ab.veiculos?.length > 0" class="space-y-1">
  <template x-for="av in ab.veiculos" :key="av.id">
    <div class="text-xs text-slate-400">
      <span class="text-slate-500 font-medium">Veículo Vinculado à Abordagem:</span>
      <span class="ml-1" x-text="[formatPlaca(av.placa), av.modelo, av.cor, av.ano].filter(Boolean).join(' · ')"></span>
    </div>
  </template>
</div>
```

**Step 3: Self-review**
- [ ] O label "Veículo Vinculado à Abordagem:" aparece antes de cada veículo
- [ ] O label usa `text-slate-500 font-medium` (diferente do valor)
- [ ] O valor do veículo usa `x-text` com `formatPlaca` + modelo + cor + ano
- [ ] `space-y-0.5` foi atualizado para `space-y-1` (mais espaço com o label)
- [ ] Nenhuma outra linha do card de abordagem foi alterada

**Step 4: Commit**

```bash
cd c:/projetos/argus_ai
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): adicionar label 'Veículo Vinculado à Abordagem:' no histórico de abordagens"
```

---

### Task 3: Revisão visual final

**Step 1: Verificar container pai de veículos**

Confirmar que:
- Com 0 veículos e 0 fotos → container pai não aparece
- Com 1+ veículo e 0 fotos → aparece só a lista de veículos
- Com 0 veículos e 1+ fotos → aparece só o grid de fotos
- Com 1+ veículos e 1+ fotos → ambos aparecem dentro do pai
- Cada veículo tem cor diferente (cíclica)
- Título do pai: "Veículos Vinculados ao Abordado"
- Sub-título das fotos: "Fotos de Veículos Vinculados ao Abordado (N)"

**Step 2: Verificar label no histórico**

Abrir uma pessoa com abordagem que tenha veículo vinculado. Confirmar que o card da abordagem exibe:
```
Veículo Vinculado à Abordagem: AAA-1111 · Gol · Branco · 2020
```

**Step 3: Commit final se houver ajustes**

```bash
cd c:/projetos/argus_ai
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "fix(frontend): ajustes visuais pós-revisão agrupamento veículos"
```
