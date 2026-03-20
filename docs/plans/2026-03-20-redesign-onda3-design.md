# Redesign Onda 3 — Abordagem Nova + Ocorrencia Upload + Pessoa Detalhe + Perfil + Admin

**Data:** 2026-03-20
**Escopo:** Paginas de formulario, detalhe e administracao

## 1. Pagina de Nova Abordagem (abordagem-nova.js)

- Header "NOVA ABORDAGEM" em font-display uppercase + subtitulo "REGISTRO OPERACIONAL" em font-data dim
- Secoes em glass-card com spacing interno 16px
- Labels em login-field-label (uppercase dim)
- Dropdowns de autocomplete com fundo --color-surface e borda --color-border
- Tags selecionadas: pessoa em ciano translucido, veiculo em verde translucido
- Formularios inline (cadastro pessoa/veiculo) com estilo glass-card
- Links "+ Cadastrar" em --color-primary (ciano)
- Cards de vinculo veiculo-pessoa com bordas semanticas (verde=vinculado, amarelo=pendente)
- Botao de voz com estados (gravando=vermelho, parado=surface)
- Modal de sucesso com glass-card, icone check em --color-success
- Toda logica Alpine.js (abordagemForm) preservada integralmente

## 2. Pagina de Upload de Ocorrencia (ocorrencia-upload.js)

- Header "UPLOAD DE OCORRENCIA" em font-display + "DOCUMENTOS OPERACIONAIS" em font-data
- Formulario em glass-card
- Labels em login-field-label
- Botao enviar em btn btn-primary
- Lista de ocorrencias em cards com glass-card hover
- Status badges com cores semanticas

## 3. Pagina de Detalhe de Pessoa (pessoa-detalhe.js)

- Header: nome em font-display uppercase, vulgo em cor laranja (--color-secondary)
- Botao voltar com icone ciano
- Cards de secao em glass-card com border-left em cores do tema:
  - Dados pessoais: ciano (--color-primary)
  - Fotos: verde (--color-success)
  - Enderecos: ciano
  - Veiculos: verde
  - Vinculos: laranja (--color-secondary)
  - Historico: roxo (#A78BFA)
  - Mapa: teal (#14B8A6)
- PALETTE atualizada de classes Tailwind para inline styles com var()
- Avatares com border-radius 4px (nao circular)
- Grid de fotos com border-radius 4px
- Modais (foto ampliada, preview pessoa, cadastro vinculo) com glass-card e overlay rgba(5,10,15,0.85)
- Placas em font-data bold com letter-spacing
- Badges de frequencia em ciano
- Toda logica Alpine.js (pessoaDetalhePage) preservada integralmente

## 4. Pagina de Perfil (perfil.js)

- Avatar com border-radius 4px e borda ciano
- Campos de formulario com login-field-label
- Botao salvar em btn btn-primary
- Secao de senha com glass-card
- Botao sair com estilo danger (vermelho)
- Versao e info em font-data dim

## 5. Pagina de Admin Usuarios (admin-usuarios.js)

- Header "ADMIN // USUARIOS" em font-display
- Tabela/lista de usuarios em glass-card
- Badges de role com cores semanticas
- Botoes de acao com icones em ciano
- Modal de edicao com glass-card overlay
- Formulario com login-field-label

## Regra Geral

- Toda logica JavaScript (funcoes Alpine.js) preservada byte-a-byte
- Apenas templates HTML reescritos com design system CSS variables
- Classes Tailwind substituidas por inline styles + classes utilitarias do design system
