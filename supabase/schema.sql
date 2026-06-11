-- Run this in your Supabase SQL editor to set up the alerts table

create table if not exists alerts (
  id          bigserial primary key,
  alert_date  timestamptz not null,
  title       text        not null,
  settlement  text        not null,
  category    smallint    not null,
  unique (alert_date, title, settlement, category)
);

-- Index for date-range queries (used by frontend pagination)
create index if not exists alerts_alert_date_idx on alerts (alert_date desc);

-- Index for settlement filtering
create index if not exists alerts_settlement_idx on alerts (settlement);

-- Allow anonymous read access (the site is public)
alter table alerts enable row level security;

create policy "Public read access"
  on alerts for select
  using (true);
