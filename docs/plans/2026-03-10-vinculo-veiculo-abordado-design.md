# Design: Vínculo veículo→abordado obrigatório + UX melhorada

**Data:** 2026-03-10
**Escopo:** `frontend/js/pages/abordagem-nova.js`, `frontend/js/components/autocomplete.js`

## Problema

Na tela de nova abordagem, ao adicionar um veículo e um abordado, o formulário permite registrar a abordagem sem vincular o veículo a nenhuma pessoa. O vínculo é obrigatório por regra de negócio: veículo só pode ser adicionado se há um abordado, portanto todo veículo deve ter um dono identificado.

Além disso, a seção de vínculo atual é visualmente discreta (texto pequeno, botões minúsculos com só o primeiro nome) e a placa não garante exibição no formato `ABC-1234`.

## Solução escolhida — Opção A

### 1. Seção de vínculo redesenhada

Substituir o bloco atual (linhas 247–266 de `abordagem-nova.js`) por um card visual por veículo com:

- **Placa** em `font-mono font-bold text-base` no formato `ABC-1234`
- **Modelo/cor** abaixo em `text-xs text-slate-400`
- **Label** "Quem estava no veículo?" (mais claro que "Vincular veículo ao abordado")
- **Botões de abordado** maiores (`px-3 py-2`), com nome completo (sem truncar)
- **Borda do card** dinâmica:
  - `border-yellow-500/60` + fundo `bg-yellow-900/10` quando sem vínculo
  - `border-green-500/60` + fundo `bg-green-900/10` quando vinculado
- **Ícone de check** (✓) no canto superior direito quando vinculado

### 2. Validação no submit()

Antes de enviar o request, verificar que todo veículo em `veiculosSelecionados` possui `veiculoPorPessoa[v.id]` preenchido (valor não-nulo/undefined).

Se falhar:
- Exibir mensagem em `this.erro`: `"Vincule o veículo [PLACA] a um dos abordados antes de registrar."`
- Scroll automático até o card do veículo sem vínculo (via `scrollIntoView`)
- Bloquear envio com `return`

### 3. Formato da placa

- `autocomplete.js` → `getLabel()` para tipo `veiculo`: aplicar `formatarPlaca(item.placa)` antes de exibir
- `abordagem-nova.js` → seção de vínculo: usar `formatarPlaca(v.placa)` na exibição da placa

## Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `frontend/js/pages/abordagem-nova.js` | Redesign HTML da seção de vínculo + validação no `submit()` |
| `frontend/js/components/autocomplete.js` | `getLabel()` formata placa de veículo |

## Não está no escopo

- Backend (nenhuma mudança de API)
- Outros formulários fora de `abordagem-nova.js`
- Modo offline (a validação ocorre antes do envio, portanto se aplica a ambos)
