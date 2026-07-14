-- Cria o papel de runtime DML-only (argus_app) e concede privilégios mínimos.
-- Executar COMO O DONO (argus), uma vez por banco. Idempotente.
-- Uso: psql -U argus -d argus_db -v app_pwd="SENHA" -f scripts/create_app_role.sql
--   (a senha vem por variável psql, SEM aspas no valor — o script as adiciona via :'app_pwd')
--
-- NOTA: psql NÃO interpola variáveis (:'app_pwd') dentro de blocos $$...$$
-- (dollar-quoted). Por isso a criação condicional usa \gexec com SQL de nível
-- superior em vez de um bloco DO — caso contrário a senha não é substituída.

-- 1) Criar o papel se não existir (sem senha ainda). \gexec executa o texto
--    gerado pelo SELECT apenas quando o papel está ausente (idempotente).
SELECT 'CREATE ROLE argus_app LOGIN'
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'argus_app')
\gexec

-- 2) Definir/atualizar a senha (idempotente). :'app_pwd' vira string literal
--    escapada com segurança pelo psql (nível superior, fora de $$).
ALTER ROLE argus_app WITH LOGIN PASSWORD :'app_pwd';

-- 3) Conectar ao banco e usar o schema. CONNECT usa o nome do banco atual
--    (current_database(), via \gexec) em vez de "argus_db" fixo, para que o
--    mesmo script sirva o banco de testes do CI (argus_test) sem edição —
--    quem quer que rode este script já está conectado ao banco certo.
SELECT format('GRANT CONNECT ON DATABASE %I TO argus_app', current_database())
\gexec
GRANT USAGE ON SCHEMA public TO argus_app;

-- 4) DML nas tabelas EXISTENTES (F1)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO argus_app;

-- 5) USAGE nas sequences EXISTENTES — necessário p/ INSERT em colunas serial/identity (F3)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO argus_app;

-- 6) EXECUTE em funções existentes (F7 — pgvector/PostGIS/etc.)
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO argus_app;

-- 7) DEFAULT PRIVILEGES para o dono atual (current_user — "argus" em produção,
--    "test" no serviço Postgres do CI) — tabelas/sequences/funções FUTURAS
--    criadas por ele (F2). SEM ISSO, toda migration futura cria objetos
--    invisíveis ao argus_app. Dinâmico pelo mesmo motivo do passo 3: o script
--    roda também no CI, onde o dono não se chama "argus".
SELECT format(
  'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO argus_app',
  current_user
)
\gexec
SELECT format(
  'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO argus_app',
  current_user
)
\gexec
SELECT format(
  'ALTER DEFAULT PRIVILEGES FOR ROLE %I IN SCHEMA public GRANT EXECUTE ON FUNCTIONS TO argus_app',
  current_user
)
\gexec

-- 8) Garantir que argus_app NÃO tem CREATE no schema (revoga o default do public)
REVOKE CREATE ON SCHEMA public FROM argus_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;  -- endurece o schema p/ todos

-- 9) audit_logs é append-only por design (LGPD — trilha nunca é alterada nem
--    apagada pela aplicação). O GRANT DML do passo 4 inclui DELETE/UPDATE em
--    TODAS as tabelas; revoga especificamente aqui para que nem uma injeção
--    SQL nem um bug de código consigam apagar/alterar auditoria via argus_app.
--    INSERT/SELECT continuam liberados (é como a API grava e lê auditoria).
--
--    ATENÇÃO — este REVOKE não é retroativo a um DROP+CREATE futuro: o
--    DEFAULT PRIVILEGES do passo 7 concede SELECT/INSERT/UPDATE/DELETE a
--    QUALQUER tabela nova criada pelo dono (não sabe excluir audit_logs
--    especificamente — Postgres não tem "default privileges por tabela").
--    Se audit_logs for algum dia recriada (DROP TABLE + CREATE TABLE, ex.:
--    um rebuild de migration, ou testes que rodam Base.metadata.create_all),
--    ela renasce com DELETE/UPDATE liberados de novo — rode este script
--    (ou pelo menos este REVOKE) de novo depois. `alembic upgrade head` via
--    ALTER TABLE normal não aciona isso (só DROP+CREATE aciona).
REVOKE DELETE, UPDATE ON audit_logs FROM argus_app;
