create table if not exists public.products (
    product_id text primary key,
    source_url text not null,
    product_name text not null,
    brand_name text,
    price integer check (price is null or price >= 0),
    rating numeric(2, 1) check (rating is null or rating between 0 and 5),
    review_count integer check (review_count is null or review_count >= 0),
    description_summary text,
    description_raw text,
    main_image_url text,
    crawled_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.raw_reviews (
    id bigint generated always as identity primary key,
    product_id text not null references public.products(product_id) on delete cascade,
    source_review_id text not null,
    encrypted_user_id text,
    reviewer_nickname text,
    reviewed_at date,
    rating numeric(2, 1) check (rating is null or rating between 0 and 5),
    purchased_option text,
    reviewer_level integer,
    reviewer_gender text,
    reviewer_height_cm smallint check (
        reviewer_height_cm is null or reviewer_height_cm between 50 and 250
    ),
    reviewer_weight_kg smallint check (
        reviewer_weight_kg is null or reviewer_weight_kg between 10 and 300
    ),
    review_type text,
    review_text text,
    photo_urls text[] not null default '{}',
    like_count integer not null default 0 check (like_count >= 0),
    source_data jsonb not null default '{}'::jsonb,
    crawled_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint raw_reviews_product_review_unique unique (product_id, source_review_id)
);

create index if not exists raw_reviews_product_id_idx
    on public.raw_reviews(product_id);
create index if not exists raw_reviews_product_rating_idx
    on public.raw_reviews(product_id, rating);
create index if not exists raw_reviews_product_reviewed_at_idx
    on public.raw_reviews(product_id, reviewed_at desc);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists products_set_updated_at on public.products;
create trigger products_set_updated_at
before update on public.products
for each row execute function public.set_updated_at();

drop trigger if exists raw_reviews_set_updated_at on public.raw_reviews;
create trigger raw_reviews_set_updated_at
before update on public.raw_reviews
for each row execute function public.set_updated_at();

alter table public.products enable row level security;
alter table public.raw_reviews enable row level security;

revoke all on table public.products from anon, authenticated;
revoke all on table public.raw_reviews from anon, authenticated;
grant all on table public.products to service_role;
grant all on table public.raw_reviews to service_role;
grant usage, select on sequence public.raw_reviews_id_seq to service_role;

comment on table public.products is 'Musinsa product details collected by the Playwright crawler';
comment on table public.raw_reviews is 'Normalized crawler output retained before AI analysis';
