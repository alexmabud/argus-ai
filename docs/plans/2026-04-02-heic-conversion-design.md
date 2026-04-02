# Design: Conversão automática HEIC → JPEG

**Data:** 2026-04-02  
**Motivação:** Fotos de iPhone enviadas no formato HEIC devem ser aceitas e salvas como JPEG transparentemente.

## Abordagem escolhida

`pillow-heif` — plugin que registra suporte HEIC/HEIF no Pillow. Conversão simples, bem mantida, sem dependências nativas complexas.

## Componentes alterados

| Arquivo | Mudança |
|---------|---------|
| `requirements.txt` | Adicionar `pillow-heif` |
| `app/core/upload_validation.py` | Nova função `converter_heic_para_jpeg` + magic bytes HEIC em `validar_magic_bytes_imagem` |
| `app/api/v1/fotos.py` | Aceitar `image/heic` e `image/heif` em `ALLOWED_IMAGE_MIMES`, chamar conversão |

## Fluxo

```
cliente envia HEIC
  → validação content_type aceita image/heic / image/heif
  → ler_upload_com_limite (limite 10 MB, sem alteração)
  → validar_magic_bytes_imagem (aceita magic bytes ftyp)
  → converter_heic_para_jpeg → bytes JPEG
  → upload segue com content_type="image/jpeg", filename com extensão .jpg
```

## Magic bytes HEIC

Container ISO Base Media File Format:
- Bytes 4–7: `ftyp`
- Bytes 8–11: marca (`heic`, `heix`, `hevc`, `mif1`, `msf1`)

Validação: checar `file_bytes[4:8] == b"ftyp"`.

## Conversão

```python
def converter_heic_para_jpeg(file_bytes: bytes) -> bytes:
    pillow_heif.register_heif_opener()
    img = Image.open(BytesIO(file_bytes)).convert("RGB")
    out = BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()
```

## O que não muda

- Limite de 10 MB (aplicado antes da conversão)
- Nenhuma mudança no frontend
- Sem feedback visual ao usuário
