# Design: Avatares na Busca + Câmera/Upload de Foto

**Data:** 2026-03-15
**Status:** Aprovado

## Contexto

Duas melhorias de UX no frontend do Argus AI:

1. **Avatares nos resultados de busca** — exibir foto pequena ao lado do nome nas listagens de pessoas, endereços e veículos, facilitando identificação visual rápida (mesmo padrão já usado no dashboard).
2. **Câmera e Upload diferenciados por contexto** — separar os fluxos de captura de foto de acordo com o contexto operacional: campo (câmera) vs. escritório/qualquer momento (upload ou os dois).

---

## Feature 1: Avatares nos resultados de busca

### Problema atual

A busca por texto de pessoas, endereços e veículos exibe apenas texto (nome, CPF, apelido, vínculos). A busca facial já mostra avatar `w-10 h-10`. O dashboard já usa avatar `w-8 h-8`. Os resultados de texto ficam sem identificação visual.

### Solução

Adicionar avatar `w-8 h-8 rounded-full object-cover flex-shrink-0` à esquerda de cada card de resultado nas três seções de busca.

### Busca por pessoa (texto) e busca por endereço

**Layout do card:**
```
[avatar 8x8]  [ nome ]              >
              [ CPF / apelido ]
```

- `foto_principal_url` já está disponível no response da API (usado na busca facial)
- Fallback: `div bg-slate-700 rounded-full` com ícone SVG de silhueta

### Busca por veículo

**Layout do card:**
```
[avatar pessoa 8x8]  [ nome / placa / modelo / vínculos ]  [thumb veículo 8x8]  >
```

- Avatar da pessoa vinculada à esquerda (`foto_principal_url`)
- Thumbnail do veículo à direita (`foto_veiculo_url` ou similar)
- Fallback pessoa: silhueta SVG em `bg-slate-700`
- Fallback veículo: ícone SVG de carro em `bg-slate-700 rounded`

### Dados necessários da API

Verificar se o endpoint de busca por texto (`/api/v1/consulta/pessoas`) já retorna `foto_principal_url`. Se não retornar, adicionar ao schema de resposta. O endpoint de busca por veículo deve retornar `foto_principal_url` da pessoa e URL da foto do veículo.

---

## Feature 2: Câmera / Upload diferenciados por contexto

### Princípio

| Contexto | Justificativa | Comportamento |
|---|---|---|
| Registro de abordagem | Campo, presença física, deve finalizar no local | Câmera only |
| Cadastro de pessoa via consulta | Qualquer momento, pode ter foto pronta | Upload only |
| Detalhes de pessoa — adicionar foto | Pode ser campo ou escritório | Câmera + Upload |

### Implementação por arquivo

#### `abordagem-nova.js` — sem alteração

Mantém comportamento atual:
```html
<input type="file" accept="image/*" capture="environment" class="hidden">
```

#### `consulta.js` — form "Nova Pessoa": upload only

Remove atributo `capture`. Adiciona mini-preview após seleção:
```html
<input type="file" accept="image/*" class="hidden" @change="onFotoSelected($event)">
<!-- mini-preview -->
<img x-show="fotoPreviewUrl" :src="fotoPreviewUrl"
     class="w-12 h-12 rounded object-cover mt-1">
```

#### `pessoa-detalhe.js` — adicionar foto: dois botões

```html
<div class="flex gap-2">
  <label class="cursor-pointer text-xs px-2 py-1 rounded bg-slate-700 text-blue-400">
    📷 Câmera
    <input type="file" accept="image/*" capture="environment" class="hidden"
           @change="onNovaFotoSelected($event)">
  </label>
  <label class="cursor-pointer text-xs px-2 py-1 rounded bg-slate-700 text-blue-400">
    📁 Galeria
    <input type="file" accept="image/*" class="hidden"
           @change="onNovaFotoSelected($event)">
  </label>
</div>
<!-- mini-preview após seleção -->
<img x-show="novaFotoPreviewUrl" :src="novaFotoPreviewUrl"
     class="w-12 h-12 rounded object-cover mt-1">
```

Ambos os inputs alimentam a mesma variável de estado e preview.

---

## Arquivos a modificar

| Arquivo | Mudança |
|---|---|
| `frontend/js/pages/consulta.js` | Avatares nos 3 tipos de resultado de busca; upload only no form Nova Pessoa |
| `frontend/js/pages/pessoa-detalhe.js` | Dois botões (câmera + upload) na seção de adicionar foto |
| `frontend/js/pages/abordagem-nova.js` | Sem alteração de comportamento |
| Backend: schema de resposta busca texto | Garantir `foto_principal_url` no payload |
| Backend: schema busca por veículo | Garantir `foto_principal_url` (pessoa) e foto do veículo |

---

## O que não muda

- Abordagem nova: fluxo de câmera permanece idêntico
- Busca facial: já tem avatar, não muda
- Dashboard: já tem avatar, não muda
- Tamanho e estilo dos cards: só adiciona avatar, não reorganiza layout
