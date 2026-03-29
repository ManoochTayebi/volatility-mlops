create table if not exists public.daily_stock_prices (
    datetime date not null,
    symbol text not null,
    open numeric not null,
    high numeric not null,
    low numeric not null,
    close numeric not null,
    volume numeric,
    inserted_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    primary key (symbol, datetime)
);

create index if not exists idx_daily_stock_prices_datetime
    on public.daily_stock_prices (datetime);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists trg_daily_stock_prices_updated_at on public.daily_stock_prices;

create trigger trg_daily_stock_prices_updated_at
before update on public.daily_stock_prices
for each row execute procedure public.set_updated_at();
