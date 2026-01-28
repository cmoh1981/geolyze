-- Create subscriptions table for Paddle billing
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

-- Indexes
create index subscriptions_user_id_idx on public.subscriptions(user_id);
create index subscriptions_paddle_id_idx on public.subscriptions(paddle_subscription_id);
create index subscriptions_status_idx on public.subscriptions(status);

-- Enable Row Level Security
alter table public.subscriptions enable row level security;

-- Users can read their own subscriptions
create policy "Users can read own subscriptions"
  on public.subscriptions
  for select
  using (auth.uid() = user_id);

-- Only service role can manage subscriptions (webhook updates)
create policy "Service can manage subscriptions"
  on public.subscriptions
  for all
  using (true);

-- Updated at trigger
create or replace trigger subscriptions_updated_at
  before update on public.subscriptions
  for each row execute procedure public.update_updated_at();

-- Sync subscription plan to users table
create or replace function public.sync_subscription_plan()
returns trigger
language plpgsql
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
