# Compressao de Imagem no Frontend

**Data:** 2026-03-24
**Status:** Aprovado

## Problema

Fotos de celulares modernos (12-48 MP) facilmente excedem o limite de 10 MB do servidor, causando erro HTTP 413 no `/api/v1/fotos/upload`.

## Solucao

Comprimir imagens no frontend antes do upload, automaticamente no `api.uploadFile()`.

## Especificacao

- **Utility:** `frontend/js/utils/image-compress.js` com funcao `compressImage(file)`
- **Integracao:** Dentro de `api.uploadFile()` em `frontend/js/api.js`
- **Max dimensao:** 1920px no lado maior, mantendo proporcao
- **Formato:** JPEG 85% qualidade
- **Comportamento:**
  - Se arquivo for imagem (`image/*`), comprimir antes do envio
  - Se imagem menor que 1920px, nao redimensiona (so recomprime JPEG)
  - Fallback: se compressao falhar, envia original
- **Limites servidor mantidos:** 10 MB em todas as camadas (defesa em profundidade)

## Pontos de upload afetados

Todos, via integracao centralizada no `api.uploadFile()`:

1. `frontend/js/pages/abordagem-nova.js` — fotos de pessoas e veiculos
2. `frontend/js/pages/pessoa-detalhe.js` — foto na ficha
3. `frontend/js/pages/consulta.js` — busca por rosto
4. `frontend/js/components/ocr-placa.js` — OCR de placa
