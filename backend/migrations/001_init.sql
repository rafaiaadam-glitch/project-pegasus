create table if not exists courses (
    id text primary key,
    title text not null,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create table if not exists lectures (
    id text primary key,
    course_id text not null,
    preset_id text not null,
    title text not null,
    status text not null,
    audio_path text,
    transcript_path text,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create table if not exists jobs (
    id text primary key,
    lecture_id text,
    job_type text not null,
    status text not null,
    result jsonb,
    error text,
    created_at timestamptz not null,
    updated_at timestamptz not null
);

create table if not exists artifacts (
    id text primary key,
    lecture_id text not null,
    course_id text not null,
    preset_id text not null,
    artifact_type text not null,
    storage_path text not null,
    summary_overview text,
    summary_section_count integer,
    created_at timestamptz not null
);

create table if not exists threads (
    id text primary key,
    course_id text not null,
    title text not null,
    summary text not null,
    status text not null,
    complexity_level integer not null,
    lecture_refs jsonb not null,
    created_at timestamptz not null
);

create table if not exists exports (
    id text primary key,
    lecture_id text not null,
    export_type text not null,
    storage_path text not null,
    metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null
);

create index if not exists jobs_lecture_id_idx on jobs (lecture_id);
create index if not exists artifacts_lecture_id_idx on artifacts (lecture_id);
create index if not exists threads_course_id_idx on threads (course_id);
create index if not exists exports_lecture_id_idx on exports (lecture_id);
