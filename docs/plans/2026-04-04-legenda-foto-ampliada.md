# Legenda com Dados Pessoais na Foto Ampliada — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Exibir nome, dados pessoais e último endereço do abordado abaixo da foto ampliada, para que screenshots capturem foto e dados juntos.

**Architecture:** Modificar o modal de `fotoAmpliada` em `pessoa-detalhe.js` para envolver a imagem em um container flex-column com um bloco de legenda abaixo. O Alpine já tem `pessoa` no escopo com todos os dados necessários. Métodos `formatarNascimento` e `formatEndereco` já existem no componente.

**Tech Stack:** Alpine.js (x-show, x-text, @click.stop), HTML/CSS inline, JavaScript vanilla.

---

### Task 1: Substituir modal de foto ampliada por layout com legenda

**Files:**
- Modify: `frontend/js/pages/pessoa-detalhe.js:139-143`

**Step 1: Localizar o modal atual**

Abra `frontend/js/pages/pessoa-detalhe.js` e localize o bloco do modal de foto ampliada (em torno das linhas 139-143). O trecho é:

```html
          <!-- Foto ampliada (modal) -->
          <div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
               style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 50; display: flex; align-items: center; justify-content: center; padding: 1rem;">
            <img :src="fotoAmpliada" style="max-width: 100%; max-height: 100%; border-radius: 4px;">
          </div>
```

**Step 2: Substituir o modal pelo novo layout com legenda**

Substituir o bloco inteiro pelo seguinte:

```html
          <!-- Foto ampliada (modal) -->
          <div x-show="fotoAmpliada" x-cloak @click="fotoAmpliada = null"
               style="position: fixed; inset: 0; background: rgba(5,10,15,0.85); z-index: 50; display: flex; align-items: center; justify-content: center; padding: 1rem;">
            <div @click.stop style="display: flex; flex-direction: column; max-width: min(90vw, 480px); width: 100%;">
              <img :src="fotoAmpliada" @click="fotoAmpliada = null"
                   style="width: 100%; border-radius: 4px 4px 0 0; display: block; cursor: pointer; object-fit: contain; max-height: 70vh;">
              <div style="background: rgba(5,10,15,0.95); border-radius: 0 0 4px 4px; padding: 0.75rem;">
                <p style="font-family: var(--font-display); font-weight: 700; color: var(--color-text); text-transform: uppercase; margin: 0 0 0.375rem 0; font-size: 1rem;" x-text="pessoa?.nome"></p>
                <p x-show="pessoa?.apelido"
                   style="font-size: 0.8rem; color: var(--color-secondary); font-family: var(--font-data); margin: 0 0 0.2rem 0;"
                   x-text="'Vulgo: ' + pessoa?.apelido"></p>
                <p x-show="pessoa?.data_nascimento"
                   style="font-size: 0.8rem; color: var(--color-text-muted); font-family: var(--font-data); margin: 0 0 0.2rem 0;"
                   x-text="'Nasc: ' + formatarNascimento(pessoa?.data_nascimento, '')"></p>
                <p x-show="pessoa?.cpf || pessoa?.cpf_masked"
                   style="font-size: 0.8rem; color: var(--color-text-muted); font-family: var(--font-data); margin: 0 0 0.2rem 0;"
                   x-text="'CPF: ' + (pessoa?.cpf || pessoa?.cpf_masked)"></p>
                <p x-show="pessoa?.enderecos?.length > 0"
                   style="font-size: 0.8rem; color: var(--color-text-muted); font-family: var(--font-data); margin: 0;"
                   x-text="'End: ' + formatEndereco(pessoa?.enderecos?.[0])"></p>
              </div>
            </div>
          </div>
```

**Notas importantes:**
- `@click.stop` no container interno impede que cliques na legenda fechem o modal
- `@click="fotoAmpliada = null"` na `<img>` mantém o comportamento de fechar ao clicar na foto
- `max-height: 70vh` na imagem garante que a legenda fique visível mesmo em fotos muito altas
- `object-fit: contain` preserva proporção sem cortar a imagem

**Step 3: Verificar no browser**

1. Abra a ficha de qualquer pessoa com foto cadastrada
2. Clique em uma foto — deve abrir o modal com foto + legenda abaixo
3. Confira que a legenda exibe: nome, vulgo (se houver), nascimento+idade, CPF, endereço atual
4. Clique na foto → modal deve fechar
5. Clique na legenda → modal NÃO deve fechar
6. Clique fora do container (no overlay escuro) → modal deve fechar
7. Repita o teste abrindo a foto pelo modal "Ver mais" (todas as fotos)
8. Teste com pessoa sem CPF → linha CPF não aparece
9. Teste com pessoa sem endereço → linha End não aparece

**Step 4: Commit**

```bash
git add frontend/js/pages/pessoa-detalhe.js
git commit -m "feat(frontend): exibir legenda com dados pessoais abaixo da foto ampliada"
```

---

## Checklist de validação final

- [ ] Foto ampliada exibe nome, vulgo (se tiver), nascimento+idade, CPF, endereço
- [ ] Clique na foto fecha o modal
- [ ] Clique na legenda NÃO fecha o modal
- [ ] Clique no overlay escuro fecha o modal
- [ ] Funciona ao abrir foto pela grid principal
- [ ] Funciona ao abrir foto pelo modal "todas as fotos"
- [ ] Campos opcionais (vulgo, CPF, endereço) são omitidos quando ausentes
- [ ] Layout não quebra em telas pequenas (mobile)
- [ ] Foto não fica cortada (object-fit: contain)
