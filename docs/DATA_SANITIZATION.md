# Sanitização de Dados

## 🧹 Como Trabalhar com Dados no Portfólio

Este projeto **NUNCA** deve conter dados reais. Use sempre dados fictícios.

---

## ✅ Dados Seguros Para Demonstração

### Pessoas (USAR APENAS DADOS FICTÍCIOS)

```python
# ✅ CORRETO - Dados fictícios óbvios
{
    "nome": "João da Silva Demo",
    "cpf": "111.111.111-11",  # CPF inválido propositalmente
    "data_nascimento": "1990-01-01",
    "observacoes": "Pessoa fictícia para demonstração"
}

# ❌ ERRADO - NUNCA use dados reais
{
    "nome": "João Silva Santos",
    "cpf": "123.456.789-10",  # CPF real
    "data_nascimento": "1985-03-15"
}
```

### Endereços

```python
# ✅ Use endereços genéricos
"Rua Exemplo, 100 - Centro - São Paulo/SP"
"Avenida Demo, 500 - Bairro Teste - Rio de Janeiro/RJ"

# ❌ NUNCA use endereços reais de pessoas
```

### Placas de Veículos

```python
# ✅ Use placas fictícias
"ABC-1234"
"XYZ-9999"

# ❌ NUNCA use placas reais
```

---

## 🎭 Gerando Dados Fictícios

Use bibliotecas como `Faker` para gerar dados de demonstração:

```python
from faker import Faker

fake = Faker('pt_BR')

# Gerar dados fictícios
pessoa_demo = {
    "nome": fake.name(),
    "cpf": "000.000.000-00",  # CPF placeholder
    "data_nascimento": fake.date_of_birth(minimum_age=18, maximum_age=80),
    "endereco": "Rua Exemplo, 100 - Centro - Cidade Demo/XX"
}
```

---

## 🚫 O Que NUNCA Fazer

### ❌ NUNCA comite:
- CPFs reais
- RGs reais
- Endereços residenciais reais
- Placas de veículos reais
- Fotos de pessoas reais (sem consentimento explícito)
- Números de telefone reais
- Emails pessoais reais
- Boletins de ocorrência reais
- Qualquer dado que possa identificar uma pessoa real

### ❌ NUNCA use em produção:
- Este código sem auditoria de segurança
- Dados de demonstração em ambiente real
- Configurações de desenvolvimento em produção

---

## 📸 Fotos e Imagens

Para demonstração, use:

✅ **Permitido:**
- Fotos de bancos de imagens livres (Unsplash, Pexels)
- Avatares gerados (ThisPersonDoesNotExist.com)
- Ícones e ilustrações genéricas
- Screenshots com dados fictícios

❌ **PROIBIDO:**
- Fotos de pessoas reais sem consentimento
- Screenshots com dados reais
- Documentos oficiais (mesmo censurados)

---

## 🧪 Dados de Teste vs. Dados Reais

| Tipo | Teste/Demo | Produção Real |
|------|------------|---------------|
| **CPF** | 000.000.000-00, 111.111.111-11 | NUNCA comitar |
| **Nome** | João Demo, Maria Teste | NUNCA comitar |
| **Email** | teste@example.com | NUNCA comitar |
| **Telefone** | (11) 0000-0000 | NUNCA comitar |
| **Endereço** | Rua Exemplo, 100 | NUNCA comitar |
| **Placa** | ABC-0000 | NUNCA comitar |

---

## 🔍 Verificação Antes de Commit

Antes de fazer commit, pergunte-se:

1. ✅ Todos os dados são fictícios e óbvios?
2. ✅ Não há CPFs, RGs ou documentos reais?
3. ✅ Não há fotos de pessoas reais sem consentimento?
4. ✅ Não há endereços residenciais reais?
5. ✅ O `.env` não está no commit?
6. ✅ Não há chaves de API ou secrets?

Se respondeu **NÃO** para qualquer item acima, **NÃO FAÇA O COMMIT**.

---

## 📚 Referências

- [Faker Documentation](https://faker.readthedocs.io/)
- [LGPD - Proteção de Dados](http://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm)
- [OWASP Data Classification](https://owasp.org/www-community/vulnerabilities/Insufficient_Data_Protection)
