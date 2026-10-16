-- 0004: shared semantic_embeddings vector store and cosine similarity function (#63).
--
-- Backs nearest-neighbour retrieval with score thresholds and metadata filters (`sector`,
-- `jurisdiction`, `source_tier`) for FTA retrieval ranking, cross-run candidate dedupe, and
-- source discovery. Embeddings are generated server-side through `ModelGateway.embed()` in
-- `services/api/model_gateway.py`.
--
-- When the `vector` (pgvector) extension is available on the Postgres host, it is enabled and a
-- native `embedding_vec vector` column is kept in sync automatically for `<=>` cosine-distance
-- queries. On a stock Postgres instance without the C extension compiled (such as `postgres:16.2`
-- in CI), `cosine_similarity(double precision[], double precision[])` computes exact cosine
-- similarity in SQL over `embedding` so schema application, migrations, threshold filtering and
-- metadata filtering work identically everywhere.

do $$
begin
  if exists (select 1 from pg_available_extensions where name = 'vector') then
    create extension if not exists vector;
  end if;
end
$$;

create table if not exists semantic_embeddings (
  id              uuid primary key default gen_random_uuid(),
  corpus          text not null check (btrim(corpus) <> ''),
  record_id       text not null check (btrim(record_id) <> ''),
  title           text not null check (btrim(title) <> ''),
  sector          text,
  jurisdiction    text,
  source_tier     smallint check (source_tier is null or (source_tier between 1 and 5)),
  embedding_model text not null check (btrim(embedding_model) <> ''),
  dimensions      integer not null check (dimensions > 0),
  embedding       double precision[] not null
                    check (coalesce(array_length(embedding, 1), 0) = dimensions),
  content_sha256  text not null check (btrim(content_sha256) <> ''),
  created_at      timestamptz not null default now(),
  updated_at      timestamptz not null default now(),
  unique (corpus, record_id, embedding_model)
);

create index if not exists semantic_embeddings_lookup_idx
  on semantic_embeddings (corpus, embedding_model, sector, jurisdiction, source_tier);

create or replace function cosine_similarity(
  a double precision[],
  b double precision[]
) returns double precision
language sql
immutable
parallel safe
as $$
  select
    case
      when a is null or b is null then null
      when coalesce(array_length(a, 1), 0) = 0
        or coalesce(array_length(a, 1), 0) <> coalesce(array_length(b, 1), 0)
        then null
      else (
        select
          case
            when norm_a = 0.0 or norm_b = 0.0 then 0.0
            else dot / (sqrt(norm_a) * sqrt(norm_b))
          end
        from (
          select
            sum(x * y) as dot,
            sum(x * x) as norm_a,
            sum(y * y) as norm_b
          from unnest(a, b) as pair(x, y)
        ) as stats
      )
    end;
$$;

do $$
begin
  if exists (select 1 from pg_type where typname = 'vector') then
    alter table semantic_embeddings add column if not exists embedding_vec vector;
    create or replace function sync_semantic_embedding_vec() returns trigger
    language plpgsql as $fn$
    begin
      new.embedding_vec := (
        '[' || array_to_string(new.embedding, ',') || ']'
      )::vector;
      return new;
    end;
    $fn$;
    drop trigger if exists semantic_embeddings_sync_vec on semantic_embeddings;
    create trigger semantic_embeddings_sync_vec
      before insert or update on semantic_embeddings
      for each row execute function sync_semantic_embedding_vec();
  end if;
end
$$;
