# Design — Ícone PWA Argus AI

**Data:** 2026-03-22

## Problema

Os arquivos `frontend/icons/icon-192.png` e `frontend/icons/icon-512.png` são placeholders em branco (593 bytes e 2.2 KB respectivamente). Por isso, ao instalar o PWA pelo Chrome, nenhum ícone aparece na tela inicial.

## Solução

Gerar ícones reais a partir da imagem do olho cyberpunk (`1772505697458.png`) usando Python + Pillow, com fundo escuro `#050A0F` (cor base do app).

## Pipeline

1. Abrir `C:\Users\User\Downloads\Phone Link nome do arquivo 1772505697458.png`
2. Converter para RGBA
3. Substituir pixels próximos ao branco (R>200, G>200, B>200) por `#050A0F`
4. Crop quadrado centralizado
5. Redimensionar para 512x512 com `LANCZOS` → salvar como `frontend/icons/icon-512.png`
6. Redimensionar para 192x192 com `LANCZOS` → salvar como `frontend/icons/icon-192.png`

## Arquivos Afetados

- `frontend/icons/icon-192.png` — substituído pelo ícone real
- `frontend/icons/icon-512.png` — substituído pelo ícone real

## Sem alterações necessárias

- `frontend/manifest.json` — já configurado corretamente
- `frontend/index.html` — já referencia os ícones corretamente
