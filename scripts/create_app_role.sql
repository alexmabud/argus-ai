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

-- 3) Conectar ao banco e usar o schema
GRANT CONNECT ON DATABASE argus_db TO argus_app;
GRANT USAGE ON SCHEMA public TO argus_app;

-- 4) DML nas tabelas EXISTENTES (F1)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO argus_app;

-- 5) USAGE nas sequences EXISTENTES — necessário p/ INSERT em colunas serial/identity (F3)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO argus_app;

-- 6) EXECUTE em funções existentes (F7 — pgvector/PostGIS/etc.)
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO argus_app;

-- 7) DEFAULT PRIVILEGES — tabelas/sequences/funções FUTURAS criadas por argus (F2)
--    SEM ISSO, toda migration futura cria objetos invisíveis ao argus_app.
ALTER DEFAULT PRIVILEGES FOR ROLE argus IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO argus_app;
ALTER DEFAULT PRIVILEGES FOR ROLE argus IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO argus_app;
ALTER DEFAULT PRIVILEGES FOR ROLE argus IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO argus_app;

-- 8) Garantir que argus_app NÃO tem CREATE no schema (revoga o default do public)
REVOKE CREATE ON SCHEMA public FROM argus_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;  -- endurece o schema p/ todos
