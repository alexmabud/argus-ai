# Criptografia de Disco via OCI Vault — Argus AI

Procedimento para habilitar criptografia de disco gerenciada pelo cliente
(customer-managed key) nos Block Volumes da Oracle Cloud Infrastructure.

---

## Visão Geral

A OCI criptografa volumes em repouso por padrão com chaves gerenciadas pela Oracle.
Para conformidade LGPD (controle exclusivo do cliente), recomenda-se usar
**OCI Vault** com uma MEK (Master Encryption Key) AES-256 própria.

Com customer-managed key:
- Revogar a MEK torna os dados inacessíveis mesmo com acesso físico ao storage
- Auditoria de todas as operações de decriptação via OCI Audit
- Rotação de chave sem downtime (OCI re-cifra o DEK transparentemente)

---

## Passos de Configuração no Console OCI

### 1. Criar Vault

1. Navegar para: **Identity & Security → Vault**
2. Clicar em **Create Vault**
   - Nome: `argus-vault`
   - Tipo: `Virtual Private Vault` (ou `Default Shared`) — Virtual é mais isolado
3. Aguardar status **Active**

### 2. Criar Master Encryption Key (MEK)

1. Dentro do Vault criado → **Create Key**
   - Nome: `argus-disk-key`
   - Algoritmo: `AES`
   - Tamanho: `256 bits`
   - Propósito: `Encrypt/Decrypt` (padrão)
2. Anotar o **OCID** da chave (formato: `ocid1.key.oc1...`)
   - **Guardar o OCID fora da VM** (cofre Cryptomator ou documentação segura)
3. Aguardar status **Enabled**

### 3. Atribuir a MEK ao Block Volume

**Para volume existente:**
1. Navegar para: **Block Storage → Block Volumes** → selecionar o volume da VM
2. Clicar em **Edit** (ou **Resources → Volume Keys**)
3. Selecionar **Customer Managed Key**
4. Escolher o Vault e a MEK criados
5. Clicar em **Save Changes**
6. Aguardar a re-cifragem automática (geralmente minutos, sem downtime)

**Para novo volume:**
- Selecionar a MEK durante a criação do volume

### 4. Verificar Atribuição

```bash
# Via CLI OCI (opcional, se instalada na VM)
oci bv volume get --volume-id <OCID_DO_VOLUME> \
  --query 'data.{status:"lifecycle-state", kms:"kms-key-id"}' \
  --output table
```

O campo `kms-key-id` deve mostrar o OCID da MEK.

---

## Rotação da MEK

A OCI suporta rotação de chave que cria uma nova versão sem precisar
re-cifrar manualmente os dados (o DEK — Data Encryption Key — é re-cifrado
automaticamente pela OCI).

1. No console OCI → Vault → selecionar a chave `argus-disk-key`
2. Clicar em **Rotate Key**
3. A nova versão fica ativa; versões anteriores ficam para decrypt de dados antigos
4. Anotar a nova versão no registro de rotação de segredos (`docs/secret-rotation.md`)

---

## Revogação de Acesso de Emergência

Para tornar dados **inacessíveis** em caso de comprometimento da VM:

1. No console OCI → Vault → Key `argus-disk-key`
2. Clicar em **Disable** ou **Delete** (disable é reversível; delete não é)
3. A VM não conseguirá mais decriptar o volume — shutdown imediato

⚠️ **Atenção:** esta ação torna os dados inacessíveis permanentemente se confirmado o delete.
Usar disable para situações reversíveis.

---

## Referências

- [OCI Vault — Documentação oficial](https://docs.oracle.com/en-us/iaas/Content/KeyManagement/home.htm)
- [Block Volume Encryption](https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/blockvolumeencryption.htm)
- `docs/secret-rotation.md` — rotação periódica de credenciais

---

*OCID da MEK e credenciais OCI: guardar no Cryptomator, nunca no repositório.*
