# Design: Compressão de Vídeo + Download de Mídias

**Data:** 2026-04-07  
**Status:** Aprovado  
**Escopo:** Compressão assíncrona de vídeos no upload e endpoint de download forçado de mídias/PDFs

---

## Contexto

Em produção, o storage de arquivos (fotos, vídeos, PDFs) usa MinIO rodando na Oracle VM com volume
montado em `/mnt/fotos` (~90 GB alocados). Vídeos gravados em celular (1080p/4K) são enviados
sem compressão, consumindo esse espaço rapidamente. O limite atual é 200 MB por arquivo.

Adicionalmente, não existe botão de download explícito — o usuário só consegue visualizar arquivos
no browser, sem forçar o download local.

---

## Decisões de Design

### 1. Compressão de Vídeo — Opção escolhida: arq worker + ffmpeg no Docker

**Rejeitadas:**
- ffmpeg.wasm no browser: pesado (~30 MB download), lento em celulares básicos
- Limite de tamanho sem compressão: péssima UX, pode perder evidências

**Escolhida: compressão server-side assíncrona**

Fluxo:
```
Upload → FastAPI salva original no MinIO → enfileira job arq →
worker baixa bytes → ffmpeg comprime → substitui no MinIO → limpa temp
```

O vídeo original fica disponível imediatamente no MinIO enquanto o worker processa.
Quando a compressão termina, o arquivo comprimido substitui o original.

**Parâmetros ffmpeg:**
- Codec vídeo: H.264 (`libx264`), preset `fast`, CRF 28
- Resolução: máximo 720p (reduz se vier acima — celular grava em 1080p/4K desnecessariamente)
- Codec áudio: AAC 128 kbps
- Estimativa de redução: 60-80% (ex: 100 MB → 15-25 MB)

**Instalação ffmpeg:** via `apt-get install -y ffmpeg` no `Dockerfile` — não afeta o SO da VM,
fica dentro do container. Acréscimo de ~70 MB na imagem Docker.

### 2. Download forçado de mídias/PDFs

**Problema:** URLs do MinIO são servidas via proxy nginx em `/storage/...`. O browser abre
o arquivo em vez de baixar.

**Solução:** Novo endpoint autenticado `GET /fotos/{foto_id}/download` que:
1. Busca `Foto` no banco validando tenant (guarnição do usuário)
2. Faz download dos bytes do MinIO via `StorageService.download()`
3. Retorna `StreamingResponse` com `Content-Disposition: attachment; filename="..."`

O frontend adiciona botão "Baixar" apontando para esse endpoint em:
- Tela de detalhe de abordagem (`abordagem-detalhe.js`)
- Tela de ocorrências (`ocorrencias.js`)

---

## Componentes Afetados

| Componente | Mudança |
|---|---|
| `Dockerfile` | `apt-get install -y ffmpeg` |
| `app/models/foto.py` | Novo campo `compressao_status: str` (pending/done/error/na) |
| `app/tasks/video_processor.py` | Nova task arq `comprimir_video` |
| `app/api/v1/fotos.py` | Endpoint `/midias` enfileira task; novo endpoint `/{foto_id}/download` |
| `app/services/foto_service.py` | Método `atualizar_apos_compressao()` |
| `frontend/js/pages/abordagem-detalhe.js` | Botão "Baixar" por mídia |
| `frontend/js/pages/ocorrencias.js` | Botão "Baixar" no PDF da ocorrência |

---

## Migration Alembic

Novo campo na tabela `fotos`:
```sql
ALTER TABLE fotos ADD COLUMN compressao_status VARCHAR(10) DEFAULT 'na';
```

Valores: `na` (não é vídeo), `pending` (aguardando), `done` (comprimido), `error` (falhou).

---

## Segurança

- Download autenticado: requer JWT válido + mesmo `guarnicao_id` da foto
- Soft delete respeitado: fotos deletadas não são acessíveis
- Filename sanitizado antes de retornar no `Content-Disposition`

---

## Critérios de Sucesso

- Vídeo de 100 MB reduzido para menos de 30 MB após compressão
- Download inicia imediatamente ao clicar no botão (não abre no browser)
- Upload não bloqueia: usuário vê a mídia disponível antes da compressão terminar
- Worker falha gracefully: se ffmpeg falhar, `compressao_status=error` e original é mantido
