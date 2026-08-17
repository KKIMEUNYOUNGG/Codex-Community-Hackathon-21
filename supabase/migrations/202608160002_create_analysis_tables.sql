-- Analysis persistence is intentionally separate from the crawler tables.
-- This migration depends on 202608160001_create_crawler_tables.sql.

create or replace function public.jsonb_object_has_keys(
    value jsonb,
    required_keys text[]
)
returns boolean
language sql
immutable
set search_path = ''
as $$
    select value is not null
        and pg_catalog.jsonb_typeof(value) = 'object'
        and value ?& required_keys;
$$;

create or replace function public.jsonb_array_has_object_keys(
    value jsonb,
    required_keys text[]
)
returns boolean
language plpgsql
immutable
set search_path = ''
as $$
declare
    item jsonb;
begin
    if value is null or pg_catalog.jsonb_typeof(value) <> 'array' then
        return false;
    end if;

    for item in
        select element
        from pg_catalog.jsonb_array_elements(value) as elements(element)
    loop
        if pg_catalog.jsonb_typeof(item) <> 'object'
            or not (item ?& required_keys) then
            return false;
        end if;
    end loop;

    return true;
end;
$$;

create table if not exists public.analysis_runs (
    id uuid primary key default gen_random_uuid(),
    product_id text not null references public.products(product_id) on delete cascade,
    analysis_version integer not null check (analysis_version > 0),
    idempotency_key text not null check (length(btrim(idempotency_key)) > 0),
    status text not null default 'queued' check (
        status in ('queued', 'running', 'completed', 'failed', 'cancelled')
    ),
    stage text not null default 'queued' check (
        stage in (
            'queued',
            'f03_aspect',
            'f04_persona_aspect',
            'f05_issues',
            'f06_strengths',
            'f07_priorities',
            'seller_actions',
            'completed'
        )
    ),
    source_hash text not null check (source_hash ~ '^[0-9a-f]{64}$'),
    artifact_schema_version text not null check (
        length(btrim(artifact_schema_version)) > 0
    ),
    taxonomy_version text not null check (length(btrim(taxonomy_version)) > 0),
    prompt_version text not null check (length(btrim(prompt_version)) > 0),
    model_name text not null check (length(btrim(model_name)) > 0),
    analysis_config jsonb not null default '{}'::jsonb check (
        pg_catalog.jsonb_typeof(analysis_config) = 'object'
    ),
    total_review_count integer not null default 0 check (total_review_count >= 0),
    source_review_count integer not null default 0 check (
        source_review_count >= total_review_count
    ),
    is_sample boolean not null default false,
    analyzed_review_count integer not null default 0 check (
        analyzed_review_count >= 0
        and analyzed_review_count <= total_review_count
    ),
    error_details jsonb check (
        error_details is null
        or public.jsonb_object_has_keys(
            error_details,
            array['code', 'message']::text[]
        )
    ),
    started_at timestamptz,
    finished_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint analysis_runs_product_version_unique
        unique (product_id, analysis_version),
    constraint analysis_runs_product_idempotency_unique
        unique (product_id, idempotency_key),
    constraint analysis_runs_timestamp_order check (
        finished_at is null
        or started_at is null
        or finished_at >= started_at
    ),
    constraint analysis_runs_completed_stage check (
        status <> 'completed' or stage = 'completed'
    ),
    constraint analysis_runs_completed_count check (
        status <> 'completed' or analyzed_review_count = total_review_count
    ),
    constraint analysis_runs_sample_scope check (
        is_sample = (total_review_count < source_review_count)
    ),
    constraint analysis_runs_terminal_timestamp check (
        status not in ('completed', 'failed', 'cancelled')
        or finished_at is not null
    )
);

create table if not exists public.review_analyses (
    id bigint generated always as identity primary key,
    analysis_run_id uuid not null
        references public.analysis_runs(id) on delete cascade,
    raw_review_id bigint not null
        references public.raw_reviews(id) on delete cascade,
    status text not null default 'completed' check (
        status in ('pending', 'completed', 'failed', 'skipped')
    ),
    input_hash text not null check (input_hash ~ '^[0-9a-f]{64}$'),
    persona jsonb not null check (
        public.jsonb_object_has_keys(
            persona,
            array['gender', 'height_cm', 'weight_kg', 'color', 'size']::text[]
        )
    ),
    aspects jsonb not null default '[]'::jsonb check (
        public.jsonb_array_has_object_keys(
            aspects,
            array[
                'category',
                'aspect',
                'sentiment',
                'opinion_code',
                'evidence',
                'evidence_start',
                'evidence_end',
                'opinion'
            ]::text[]
        )
    ),
    provider_response_id text,
    error_details jsonb check (
        error_details is null
        or public.jsonb_object_has_keys(
            error_details,
            array['code', 'message']::text[]
        )
    ),
    analyzed_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint review_analyses_run_review_unique
        unique (analysis_run_id, raw_review_id)
);

create table if not exists public.product_analyses (
    id uuid primary key default gen_random_uuid(),
    analysis_run_id uuid not null
        references public.analysis_runs(id) on delete cascade,
    product_id text not null
        references public.products(product_id) on delete cascade,
    analysis_data jsonb not null check (
        public.jsonb_object_has_keys(
            analysis_data,
            array[
                'schema_version',
                'product_id',
                'source_aspect_schema_version',
                'source_hash',
                'taxonomy_version',
                'prompt_version',
                'source_review_count',
                'selected_review_count',
                'is_sample',
                'analysis_config',
                'generated_at',
                'analyzed_review_count',
                'persona_aspect_summary',
                'persona_aspect',
                'issues',
                'strengths',
                'priorities'
            ]::text[]
        )
        and analysis_data ->> 'product_id' = product_id
        and pg_catalog.jsonb_typeof(analysis_data -> 'analyzed_review_count') = 'number'
        and pg_catalog.jsonb_typeof(analysis_data -> 'analysis_config') = 'object'
        and public.jsonb_array_has_object_keys(
            analysis_data -> 'persona_aspect_summary',
            array[
                'dimensions',
                'segment',
                'aspect',
                'mentioned_reviews',
                'positive_reviews',
                'negative_reviews',
                'evidence'
            ]::text[]
        )
        and public.jsonb_array_has_object_keys(
            analysis_data -> 'persona_aspect',
            array[
                'dimensions',
                'segment',
                'aspect',
                'opinion_code',
                'mentioned_reviews',
                'evidence'
            ]::text[]
        )
        and public.jsonb_array_has_object_keys(
            analysis_data -> 'issues',
            array[
                'issue_id',
                'title',
                'aspect',
                'opinion_code',
                'aspect_review_count',
                'review_ids',
                'evidence'
            ]::text[]
        )
        and public.jsonb_array_has_object_keys(
            analysis_data -> 'strengths',
            array[
                'strength_id',
                'title',
                'aspect',
                'opinion_code',
                'aspect_review_count',
                'score',
                'review_ids',
                'evidence'
            ]::text[]
        )
        and public.jsonb_array_has_object_keys(
            analysis_data -> 'priorities',
            array[
                'rank',
                'issue_id',
                'title',
                'score',
                'components',
                'review_ids',
                'evidence'
            ]::text[]
        )
    ),
    seller_actions jsonb not null default '[]'::jsonb check (
        public.jsonb_array_has_object_keys(
            seller_actions,
            array['category', 'content', 'evidence']::text[]
        )
    ),
    generated_at timestamptz not null default now(),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint product_analyses_run_unique unique (analysis_run_id)
);

create table if not exists public.chat_history (
    id uuid primary key default gen_random_uuid(),
    conversation_id uuid not null,
    message_key text not null check (length(btrim(message_key)) > 0),
    sequence_no integer not null check (sequence_no >= 0),
    product_id text not null
        references public.products(product_id) on delete cascade,
    analysis_run_id uuid
        references public.analysis_runs(id) on delete set null,
    role text not null check (role in ('system', 'user', 'assistant')),
    content text not null check (length(btrim(content)) > 0),
    filters jsonb not null default '{}'::jsonb check (
        pg_catalog.jsonb_typeof(filters) = 'object'
    ),
    evidence_refs jsonb not null default '[]'::jsonb check (
        public.jsonb_array_has_object_keys(
            evidence_refs,
            array['review_id', 'evidence']::text[]
        )
    ),
    unsupported_claims jsonb not null default '[]'::jsonb check (
        pg_catalog.jsonb_typeof(unsupported_claims) = 'array'
    ),
    model_name text,
    prompt_version text,
    token_usage jsonb check (
        token_usage is null
        or pg_catalog.jsonb_typeof(token_usage) = 'object'
    ),
    metadata jsonb not null default '{}'::jsonb check (
        pg_catalog.jsonb_typeof(metadata) = 'object'
    ),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint chat_history_conversation_sequence_unique
        unique (conversation_id, sequence_no),
    constraint chat_history_conversation_message_key_unique
        unique (conversation_id, message_key)
);

create index if not exists analysis_runs_product_status_idx
    on public.analysis_runs(product_id, status, created_at desc);
create index if not exists review_analyses_raw_review_id_idx
    on public.review_analyses(raw_review_id);
create index if not exists review_analyses_run_status_idx
    on public.review_analyses(analysis_run_id, status);
create index if not exists product_analyses_product_generated_idx
    on public.product_analyses(product_id, generated_at desc);
create index if not exists chat_history_product_created_idx
    on public.chat_history(product_id, created_at desc);
create index if not exists chat_history_conversation_idx
    on public.chat_history(conversation_id, sequence_no);

create or replace function public.validate_review_analysis_product()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
    run_product_id text;
    review_product_id text;
begin
    select run.product_id
    into run_product_id
    from public.analysis_runs as run
    where run.id = new.analysis_run_id;

    select review.product_id
    into review_product_id
    from public.raw_reviews as review
    where review.id = new.raw_review_id;

    if run_product_id is distinct from review_product_id then
        raise exception using
            errcode = '23514',
            message = 'review_analyses run and raw review must belong to the same product';
    end if;

    return new;
end;
$$;

create or replace function public.validate_product_analysis_run()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
    run_product_id text;
    run_source_hash text;
    run_artifact_schema_version text;
    run_taxonomy_version text;
    run_prompt_version text;
    run_analysis_config jsonb;
    run_total_review_count integer;
    run_source_review_count integer;
    run_is_sample boolean;
    run_analyzed_review_count integer;
begin
    select
        run.product_id,
        run.source_hash,
        run.artifact_schema_version,
        run.taxonomy_version,
        run.prompt_version,
        run.analysis_config,
        run.total_review_count,
        run.source_review_count,
        run.is_sample,
        run.analyzed_review_count
    into
        run_product_id,
        run_source_hash,
        run_artifact_schema_version,
        run_taxonomy_version,
        run_prompt_version,
        run_analysis_config,
        run_total_review_count,
        run_source_review_count,
        run_is_sample,
        run_analyzed_review_count
    from public.analysis_runs as run
    where run.id = new.analysis_run_id
    for no key update;

    if run_product_id is distinct from new.product_id then
        raise exception using
            errcode = '23514',
            message = 'product_analyses run and row must belong to the same product';
    end if;

    if new.analysis_data ->> 'source_hash' is distinct from run_source_hash
        or new.analysis_data ->> 'source_aspect_schema_version'
            is distinct from run_artifact_schema_version
        or new.analysis_data ->> 'taxonomy_version' is distinct from run_taxonomy_version
        or new.analysis_data ->> 'prompt_version' is distinct from run_prompt_version
        or new.analysis_data -> 'analysis_config' is distinct from run_analysis_config
        or (new.analysis_data ->> 'selected_review_count')::numeric
            is distinct from run_total_review_count::numeric
        or (new.analysis_data ->> 'source_review_count')::numeric
            is distinct from run_source_review_count::numeric
        or (new.analysis_data ->> 'is_sample')::boolean
            is distinct from run_is_sample
        or (new.analysis_data ->> 'analyzed_review_count')::numeric
            > run_analyzed_review_count::numeric then
        raise exception using
            errcode = '23514',
            message = 'product_analyses artifact metadata must be compatible with its analysis run';
    end if;

    return new;
end;
$$;

create or replace function public.validate_chat_analysis_run()
returns trigger
language plpgsql
set search_path = ''
as $$
declare
    run_product_id text;
begin
    if new.analysis_run_id is null then
        return new;
    end if;

    select run.product_id
    into run_product_id
    from public.analysis_runs as run
    where run.id = new.analysis_run_id;

    if run_product_id is distinct from new.product_id then
        raise exception using
            errcode = '23514',
            message = 'chat_history analysis run and row must belong to the same product';
    end if;

    return new;
end;
$$;

create or replace function public.reject_analysis_run_identity_change()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    if new.product_id is distinct from old.product_id
        or new.source_hash is distinct from old.source_hash
        or new.artifact_schema_version is distinct from old.artifact_schema_version
        or new.taxonomy_version is distinct from old.taxonomy_version
        or new.prompt_version is distinct from old.prompt_version
        or new.model_name is distinct from old.model_name
        or new.analysis_config is distinct from old.analysis_config
        or new.total_review_count is distinct from old.total_review_count
        or new.source_review_count is distinct from old.source_review_count
        or new.is_sample is distinct from old.is_sample
        or new.analysis_version is distinct from old.analysis_version
        or new.idempotency_key is distinct from old.idempotency_key then
        raise exception using
            errcode = '23514',
            message = 'analysis run identity fields are immutable after insert';
    end if;

    return new;
end;
$$;

create or replace function public.reject_finalized_analysis_count_change()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    if new.analyzed_review_count is distinct from old.analyzed_review_count
        and exists (
            select 1
            from public.product_analyses as product_analysis
            where product_analysis.analysis_run_id = old.id
        ) then
        raise exception using
            errcode = '23514',
            message = 'analyzed_review_count is immutable after product analysis creation';
    end if;

    return new;
end;
$$;

create or replace function public.reject_raw_review_product_change()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    if new.product_id is distinct from old.product_id then
        raise exception using
            errcode = '23514',
            message = 'raw review product_id is immutable after insert';
    end if;

    return new;
end;
$$;

drop trigger if exists review_analyses_validate_product
    on public.review_analyses;
create trigger review_analyses_validate_product
before insert or update of analysis_run_id, raw_review_id
on public.review_analyses
for each row execute function public.validate_review_analysis_product();

drop trigger if exists product_analyses_validate_run
    on public.product_analyses;
create trigger product_analyses_validate_run
before insert or update
on public.product_analyses
for each row execute function public.validate_product_analysis_run();

drop trigger if exists chat_history_validate_run
    on public.chat_history;
create trigger chat_history_validate_run
before insert or update of analysis_run_id, product_id
on public.chat_history
for each row execute function public.validate_chat_analysis_run();

drop trigger if exists analysis_runs_reject_identity_change
    on public.analysis_runs;
create trigger analysis_runs_reject_identity_change
before update of
    product_id,
    source_hash,
    artifact_schema_version,
    taxonomy_version,
    prompt_version,
    model_name,
    analysis_config,
    total_review_count,
    source_review_count,
    is_sample,
    analysis_version,
    idempotency_key
on public.analysis_runs
for each row execute function public.reject_analysis_run_identity_change();

drop trigger if exists analysis_runs_reject_finalized_count_change
    on public.analysis_runs;
create trigger analysis_runs_reject_finalized_count_change
before update of analyzed_review_count
on public.analysis_runs
for each row execute function public.reject_finalized_analysis_count_change();

drop trigger if exists raw_reviews_reject_product_change
    on public.raw_reviews;
create trigger raw_reviews_reject_product_change
before update of product_id
on public.raw_reviews
for each row execute function public.reject_raw_review_product_change();

drop trigger if exists analysis_runs_set_updated_at on public.analysis_runs;
create trigger analysis_runs_set_updated_at
before update on public.analysis_runs
for each row execute function public.set_updated_at();

drop trigger if exists review_analyses_set_updated_at on public.review_analyses;
create trigger review_analyses_set_updated_at
before update on public.review_analyses
for each row execute function public.set_updated_at();

drop trigger if exists product_analyses_set_updated_at on public.product_analyses;
create trigger product_analyses_set_updated_at
before update on public.product_analyses
for each row execute function public.set_updated_at();

drop trigger if exists chat_history_set_updated_at on public.chat_history;
create trigger chat_history_set_updated_at
before update on public.chat_history
for each row execute function public.set_updated_at();

alter table public.analysis_runs enable row level security;
alter table public.review_analyses enable row level security;
alter table public.product_analyses enable row level security;
alter table public.chat_history enable row level security;

revoke all on table public.analysis_runs from public, anon, authenticated;
revoke all on table public.review_analyses from public, anon, authenticated;
revoke all on table public.product_analyses from public, anon, authenticated;
revoke all on table public.chat_history from public, anon, authenticated;
revoke all on sequence public.review_analyses_id_seq from public, anon, authenticated;

grant all on table public.analysis_runs to service_role;
grant all on table public.review_analyses to service_role;
grant all on table public.product_analyses to service_role;
grant all on table public.chat_history to service_role;
grant usage, select on sequence public.review_analyses_id_seq to service_role;

revoke all on function public.jsonb_object_has_keys(jsonb, text[])
    from public, anon, authenticated;
revoke all on function public.jsonb_array_has_object_keys(jsonb, text[])
    from public, anon, authenticated;
revoke all on function public.validate_review_analysis_product()
    from public, anon, authenticated;
revoke all on function public.validate_product_analysis_run()
    from public, anon, authenticated;
revoke all on function public.validate_chat_analysis_run()
    from public, anon, authenticated;
revoke all on function public.reject_analysis_run_identity_change()
    from public, anon, authenticated;
revoke all on function public.reject_finalized_analysis_count_change()
    from public, anon, authenticated;
revoke all on function public.reject_raw_review_product_change()
    from public, anon, authenticated;

grant execute on function public.jsonb_object_has_keys(jsonb, text[])
    to service_role;
grant execute on function public.jsonb_array_has_object_keys(jsonb, text[])
    to service_role;
grant execute on function public.validate_review_analysis_product()
    to service_role;
grant execute on function public.validate_product_analysis_run()
    to service_role;
grant execute on function public.validate_chat_analysis_run()
    to service_role;
grant execute on function public.reject_analysis_run_identity_change()
    to service_role;
grant execute on function public.reject_finalized_analysis_count_change()
    to service_role;
grant execute on function public.reject_raw_review_product_change()
    to service_role;

comment on table public.analysis_runs is
    'Versioned, idempotent executions of the review-analysis pipeline';
comment on table public.review_analyses is
    'Per-review F03 persona, aspect, sentiment, and exact evidence output';
comment on table public.product_analyses is
    'Product-level F04-F07 insights plus later seller actions';
comment on table public.chat_history is
    'Seller chatbot messages and their review evidence references';
