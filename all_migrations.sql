-- Migration 1: Users table
create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null,
  name text,
  plan text not null default 'free' check (plan in ('free', 'pro', 'enterprise')),
  paddle_customer_id text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.users enable row level security;

create policy "Users can read own data"
  on public.users for select using (auth.uid() = id);

create policy "Users can update own data"
  on public.users for update using (auth.uid() = id);

create or replace function public.handle_new_user()
returns trigger language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.users (id, email, name)
  values (new.id, new.email, coalesce(new.raw_user_meta_data ->> 'name', ''));
  return new;
end;
$$;

create or replace trigger on_auth_user_created
  after insert on auth.users
  for each row execute procedure public.handle_new_user();

create or replace function public.update_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create or replace trigger users_updated_at
  before update on public.users
  for each row execute procedure public.update_updated_at();

-- Migration 2: Jobs table
create type public.job_status as enum ('pending', 'downloading', 'analyzing', 'completed', 'failed');

create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  geo_id text not null,
  status public.job_status not null default 'pending',
  result_data jsonb,
  metadata jsonb,
  error text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create index jobs_user_id_idx on public.jobs(user_id);
create index jobs_status_idx on public.jobs(status);
create index jobs_geo_id_idx on public.jobs(geo_id);
create index jobs_created_at_idx on public.jobs(created_at desc);

alter table public.jobs enable row level security;

create policy "Users can read own jobs"
  on public.jobs for select using (auth.uid() = user_id);

create policy "Users can create jobs"
  on public.jobs for insert with check (auth.uid() = user_id);

create policy "Service can update jobs"
  on public.jobs for update using (true);

-- Migration 3: Subscriptions table
create table if not exists public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  paddle_subscription_id text unique not null,
  plan text not null default 'pro' check (plan in ('pro', 'enterprise')),
  status text not null default 'active' check (
    status in ('active', 'past_due', 'paused', 'canceled', 'trialing')
  ),
  current_period_end timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index subscriptions_user_id_idx on public.subscriptions(user_id);
create index subscriptions_paddle_id_idx on public.subscriptions(paddle_subscription_id);
create index subscriptions_status_idx on public.subscriptions(status);

alter table public.subscriptions enable row level security;

create policy "Users can read own subscriptions"
  on public.subscriptions for select using (auth.uid() = user_id);

create policy "Service can manage subscriptions"
  on public.subscriptions for all using (true);

create or replace trigger subscriptions_updated_at
  before update on public.subscriptions
  for each row execute procedure public.update_updated_at();

create or replace function public.sync_subscription_plan()
returns trigger language plpgsql
security definer set search_path = ''
as $$
begin
  if new.status = 'active' or new.status = 'trialing' then
    update public.users set plan = new.plan where id = new.user_id;
  elsif new.status = 'canceled' then
    update public.users set plan = 'free' where id = new.user_id;
  end if;
  return new;
end;
$$;

create or replace trigger on_subscription_change
  after insert or update on public.subscriptions
  for each row execute procedure public.sync_subscription_plan();
