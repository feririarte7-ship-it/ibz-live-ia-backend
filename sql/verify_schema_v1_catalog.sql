-- IBIZA LIVE IA - Verify schema v1 was applied correctly

-- 1) Tables exist
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in (
    'discotecas',
    'eventos',
    'evento_djs',
    'playas',
    'restaurantes',
    'transportes_vip'
  )
order by table_name;

-- 2) RLS enabled on all catalog tables
select c.relname as table_name, c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in (
    'discotecas',
    'eventos',
    'evento_djs',
    'playas',
    'restaurantes',
    'transportes_vip'
  )
order by c.relname;

-- 3) Policy names present
select tablename, policyname, roles, cmd
from pg_policies
where schemaname = 'public'
  and tablename in (
    'discotecas',
    'eventos',
    'evento_djs',
    'playas',
    'restaurantes',
    'transportes_vip'
  )
order by tablename, policyname;

-- 4) Event-DJ relationship checks
select
  tc.table_name,
  kcu.column_name,
  ccu.table_name as foreign_table_name,
  ccu.column_name as foreign_column_name
from information_schema.table_constraints as tc
join information_schema.key_column_usage as kcu
  on tc.constraint_name = kcu.constraint_name
 and tc.table_schema = kcu.table_schema
join information_schema.constraint_column_usage as ccu
  on ccu.constraint_name = tc.constraint_name
 and ccu.table_schema = tc.table_schema
where tc.constraint_type = 'FOREIGN KEY'
  and tc.table_schema = 'public'
  and tc.table_name = 'evento_djs'
order by tc.table_name, kcu.column_name;

-- 5) Allowed values check for transportes service_type
select pg_get_constraintdef(oid) as check_definition
from pg_constraint
where conname = 'chk_transportes_service_type';
