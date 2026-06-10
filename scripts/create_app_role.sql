-- Cria o papel de runtime DML-only (argus_app) e concede privilégios mínimos.
-- Executar COMO O DONO (argus), uma vez por banco. Idempotente.
-- Uso: psql -U argus -d argus_db -v app_pwd="'SENHA'" -f scripts/create_app_role.sql
--   (a senha vem por variável psql para não ficar hardcoded)

-- 1) Criar o papel se não existir
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'argus_app') THEN
    EXECUTE format('CREATE ROLE argus_app LOGIN PASSWORD %L', :'app_pwd');
  ELSE
    EXECUTE format('ALTER ROLE argus_app WITH LOGIN PASSWORD %L', :'app_pwd');
  END IF;
END
$$;

-- 2) Conectar ao banco e usar o schema
GRANT CONNECT ON DATABASE argus_db TO argus_app;
GRANT USAGE ON SCHEMA public TO argus_app;

-- 3) DML nas tabelas EXISTENTES (F1)
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO argus_app;

-- 4) USAGE nas sequences EXISTENTES — necessário p/ INSERT em colunas serial/identity (F3)
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO argus_app;

-- 5) EXECUTE em funções existentes (F7 — pgvector/PostGIS/etc.)
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO argus_app;

-- 6) DEFAULT PRIVILEGES — tabelas/sequences/funções FUTURAS criadas por argus (F2)
--    SEM ISSO, toda migration futura cria objetos invisíveis ao argus_app.
ALTER DEFAULT PRIVILEGES FOR ROLE argus IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO argus_app;
ALTER DEFAULT PRIVILEGES FOR ROLE argus IN SCHEMA public
  GRANT USAGE, SELECT ON SEQUENCES TO argus_app;
ALTER DEFAULT PRIVILEGES FOR ROLE argus IN SCHEMA public
  GRANT EXECUTE ON FUNCTIONS TO argus_app;

-- 7) Garantir que argus_app NÃO tem CREATE no schema (revoga o default do public)
REVOKE CREATE ON SCHEMA public FROM argus_app;
REVOKE CREATE ON SCHEMA public FROM PUBLIC;  -- endurece o schema p/ todos
