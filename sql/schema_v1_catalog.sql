-- IBIZA LIVE IA - Catalog schema v1
-- Review this file before applying in Supabase.

-- Extensions
create extension if not exists pgcrypto;

-- Generic trigger function to keep updated_at current.
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- =========================
-- 1) DISCOTECAS
-- =========================
create table if not exists public.discotecas (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  short_description text,
  full_description text,
  location_name text not null,
  address text,
  zone text,
  phone text,
  email text,
  website_url text,
  instagram_url text,
  image_url text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  active boolean not null default true,
  source text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_discotecas_active on public.discotecas (active);
create index if not exists idx_discotecas_zone on public.discotecas (zone);

drop trigger if exists trg_discotecas_updated_at on public.discotecas;
create trigger trg_discotecas_updated_at
before update on public.discotecas
for each row
execute function public.set_updated_at();

-- =========================
-- 2) EVENTOS
-- =========================
create table if not exists public.eventos (
  id uuid primary key default gen_random_uuid(),
  discoteca_id uuid not null references public.discotecas(id) on delete cascade,
  title text not null,
  slug text not null unique,
  subtitle text,
  description text,
  event_type text not null default 'club',
  start_at timestamptz not null,
  end_at timestamptz,
  door_open_at timestamptz,
  currency char(3) not null default 'EUR',
  price_from numeric(10,2),
  price_to numeric(10,2),
  tickets_url text,
  poster_url text,
  status text not null default 'scheduled',
  active boolean not null default true,
  source text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_eventos_status
    check (status in ('scheduled', 'cancelled', 'sold_out', 'completed')),
  constraint chk_eventos_event_type
    check (event_type in ('club', 'opening', 'closing', 'festival', 'special')),
  constraint chk_eventos_prices
    check (price_to is null or price_from is null or price_to >= price_from)
);

create index if not exists idx_eventos_discoteca_id on public.eventos (discoteca_id);
create index if not exists idx_eventos_start_at on public.eventos (start_at);
create index if not exists idx_eventos_status on public.eventos (status);
create index if not exists idx_eventos_active on public.eventos (active);

drop trigger if exists trg_eventos_updated_at on public.eventos;
create trigger trg_eventos_updated_at
before update on public.eventos
for each row
execute function public.set_updated_at();

-- =========================
-- 3) EVENTO DJS
-- =========================
create table if not exists public.evento_djs (
  id uuid primary key default gen_random_uuid(),
  evento_id uuid not null references public.eventos(id) on delete cascade,
  dj_name text not null,
  artist_slug text,
  set_order int not null default 1,
  is_headliner boolean not null default false,
  start_time timestamptz,
  end_time timestamptz,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_evento_djs_set_order check (set_order > 0),
  constraint uq_evento_dj_order unique (evento_id, set_order)
);

create index if not exists idx_evento_djs_evento_id on public.evento_djs (evento_id);
create index if not exists idx_evento_djs_dj_name on public.evento_djs (dj_name);

drop trigger if exists trg_evento_djs_updated_at on public.evento_djs;
create trigger trg_evento_djs_updated_at
before update on public.evento_djs
for each row
execute function public.set_updated_at();

-- =========================
-- 4) PLAYAS
-- =========================
create table if not exists public.playas (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  short_description text,
  full_description text,
  municipality text,
  zone text,
  image_url text,
  map_url text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  has_parking boolean,
  has_beach_clubs boolean,
  family_friendly boolean,
  best_time text,
  active boolean not null default true,
  source text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_playas_zone on public.playas (zone);
create index if not exists idx_playas_active on public.playas (active);

drop trigger if exists trg_playas_updated_at on public.playas;
create trigger trg_playas_updated_at
before update on public.playas
for each row
execute function public.set_updated_at();

-- =========================
-- 5) RESTAURANTES
-- =========================
create table if not exists public.restaurantes (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  short_description text,
  full_description text,
  cuisine_type text,
  price_level text,
  location_name text,
  address text,
  zone text,
  phone text,
  whatsapp text,
  email text,
  website_url text,
  instagram_url text,
  reservation_url text,
  image_url text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  active boolean not null default true,
  source text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_restaurantes_price_level
    check (price_level is null or price_level in ('$', '$$', '$$$', '$$$$'))
);

create index if not exists idx_restaurantes_zone on public.restaurantes (zone);
create index if not exists idx_restaurantes_cuisine on public.restaurantes (cuisine_type);
create index if not exists idx_restaurantes_active on public.restaurantes (active);

drop trigger if exists trg_restaurantes_updated_at on public.restaurantes;
create trigger trg_restaurantes_updated_at
before update on public.restaurantes
for each row
execute function public.set_updated_at();

-- =========================
-- 6) TRANSPORTES VIP
-- =========================
create table if not exists public.transportes_vip (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  slug text not null unique,
  short_description text,
  full_description text,
  service_type text not null default 'vip_transfer',
  phone text,
  whatsapp text,
  email text,
  website_url text,
  instagram_url text,
  base_location text,
  covers_island boolean not null default true,
  active boolean not null default true,
  source text,
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint chk_transportes_service_type
    check (service_type in ('vip_transfer', 'chauffeur', 'yacht_transfer', 'helicopter', 'taxi', 'vip_taxi'))
);

create index if not exists idx_transportes_service_type on public.transportes_vip (service_type);
create index if not exists idx_transportes_active on public.transportes_vip (active);

drop trigger if exists trg_transportes_vip_updated_at on public.transportes_vip;
create trigger trg_transportes_vip_updated_at
before update on public.transportes_vip
for each row
execute function public.set_updated_at();

-- =========================
-- ROW LEVEL SECURITY (RLS)
-- =========================
alter table public.discotecas enable row level security;
alter table public.eventos enable row level security;
alter table public.evento_djs enable row level security;
alter table public.playas enable row level security;
alter table public.restaurantes enable row level security;
alter table public.transportes_vip enable row level security;

-- Public read policies (catalog style content).
drop policy if exists discotecas_public_read on public.discotecas;
create policy discotecas_public_read
on public.discotecas
for select
to anon, authenticated
using (active = true);

drop policy if exists eventos_public_read on public.eventos;
create policy eventos_public_read
on public.eventos
for select
to anon, authenticated
using (active = true);

drop policy if exists evento_djs_public_read on public.evento_djs;
create policy evento_djs_public_read
on public.evento_djs
for select
to anon, authenticated
using (
  exists (
    select 1
    from public.eventos e
    where e.id = evento_djs.evento_id
      and e.active = true
  )
);

drop policy if exists playas_public_read on public.playas;
create policy playas_public_read
on public.playas
for select
to anon, authenticated
using (active = true);

drop policy if exists restaurantes_public_read on public.restaurantes;
create policy restaurantes_public_read
on public.restaurantes
for select
to anon, authenticated
using (active = true);

drop policy if exists transportes_vip_public_read on public.transportes_vip;
create policy transportes_vip_public_read
on public.transportes_vip
for select
to anon, authenticated
using (active = true);

-- Only service role can write catalog data.
drop policy if exists discotecas_service_write on public.discotecas;
create policy discotecas_service_write
on public.discotecas
for all
to service_role
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists eventos_service_write on public.eventos;
create policy eventos_service_write
on public.eventos
for all
to service_role
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists evento_djs_service_write on public.evento_djs;
create policy evento_djs_service_write
on public.evento_djs
for all
to service_role
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists playas_service_write on public.playas;
create policy playas_service_write
on public.playas
for all
to service_role
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists restaurantes_service_write on public.restaurantes;
create policy restaurantes_service_write
on public.restaurantes
for all
to service_role
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');

drop policy if exists transportes_vip_service_write on public.transportes_vip;
create policy transportes_vip_service_write
on public.transportes_vip
for all
to service_role
using (auth.role() = 'service_role')
with check (auth.role() = 'service_role');
