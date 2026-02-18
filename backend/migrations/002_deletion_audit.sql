create table if not exists deletion_audit_events (
    id text primary key,
    entity_type text not null,
    entity_id text not null,
    actor text not null,
    request_id text,
    purge_storage boolean not null,
    result jsonb not null,
    created_at timestamptz not null
);

create index if not exists deletion_audit_events_entity_idx
    on deletion_audit_events (entity_type, entity_id, created_at desc);

