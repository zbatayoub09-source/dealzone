-- DealZone Publisher initial database schema for Supabase/Postgres.
-- Apply only in your own Supabase project's SQL editor after reviewing.
create extension if not exists pgcrypto;

create table if not exists public.publisher_profiles (
  user_id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now()
);

create table if not exists public.publisher_destinations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  platform text not null check (platform in ('blogger','facebook','instagram')),
  external_account_id text not null,
  account_label text,
  status text not null default 'connected' check (status in ('connected','needs_reauth','disabled')),
  created_at timestamptz not null default now(),
  unique (user_id, platform, external_account_id),
  unique (id, user_id)
);

create table if not exists public.publisher_jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  destination_id uuid not null,
  source_filename text,
  status text not null default 'queued' check (status in ('queued','running','paused','completed','failed','cancelled')),
  max_posts_per_run integer not null default 10 check (max_posts_per_run between 1 and 300),
  interval_seconds integer not null default 300 check (interval_seconds between 60 and 86400),
  resume_enabled boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (destination_id, user_id) references public.publisher_destinations(id, user_id) on delete cascade
);

create table if not exists public.publisher_queue (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  job_id uuid not null references public.publisher_jobs(id) on delete cascade,
  destination_id uuid not null,
  product_key text not null,
  product_data jsonb not null default '{}'::jsonb,
  status text not null default 'pending' check (status in ('pending','processing','published','failed','uncertain','skipped')),
  attempts integer not null default 0 check (attempts >= 0),
  next_attempt_at timestamptz not null default now(),
  platform_post_id text,
  last_error_code text,
  last_error_message text,
  locked_at timestamptz,
  published_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  foreign key (destination_id, user_id) references public.publisher_destinations(id, user_id) on delete cascade,
  unique (user_id, destination_id, product_key)
);

create index if not exists publisher_queue_due_idx
  on public.publisher_queue(status, next_attempt_at, created_at);
create index if not exists publisher_queue_user_idx
  on public.publisher_queue(user_id, created_at desc);
create index if not exists publisher_jobs_user_idx
  on public.publisher_jobs(user_id, created_at desc);

alter table public.publisher_profiles enable row level security;
alter table public.publisher_destinations enable row level security;
alter table public.publisher_jobs enable row level security;
alter table public.publisher_queue enable row level security;

create policy "profile owner can read own profile" on public.publisher_profiles
  for select to authenticated using (auth.uid() = user_id);
create policy "profile owner can insert own profile" on public.publisher_profiles
  for insert to authenticated with check (auth.uid() = user_id);
create policy "profile owner can update own profile" on public.publisher_profiles
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

create policy "owner reads own destinations" on public.publisher_destinations
  for select to authenticated using (auth.uid() = user_id);
create policy "owner reads own jobs" on public.publisher_jobs
  for select to authenticated using (auth.uid() = user_id);
create policy "owner reads own queue" on public.publisher_queue
  for select to authenticated using (auth.uid() = user_id);

-- Intentionally no client INSERT/UPDATE/DELETE policies for destinations, jobs, or queue.
-- Only authenticated Edge Functions using the service role should mutate publishing state.
-- Never put the Supabase service-role key in GitHub Pages or any public client code.
