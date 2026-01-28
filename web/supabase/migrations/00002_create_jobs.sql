-- Create job status enum
create type public.job_status as enum (
  'pending',
  'downloading',
  'analyzing',
  'completed',
  'failed'
);

-- Create jobs table
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

-- Indexes
create index jobs_user_id_idx on public.jobs(user_id);
create index jobs_status_idx on public.jobs(status);
create index jobs_geo_id_idx on public.jobs(geo_id);
create index jobs_created_at_idx on public.jobs(created_at desc);

-- Enable Row Level Security
alter table public.jobs enable row level security;

-- Users can read their own jobs
create policy "Users can read own jobs"
  on public.jobs
  for select
  using (auth.uid() = user_id);

-- Users can insert their own jobs
create policy "Users can create jobs"
  on public.jobs
  for insert
  with check (auth.uid() = user_id);

-- Service role can update any job (for backend processing)
create policy "Service can update jobs"
  on public.jobs
  for update
  using (true);
