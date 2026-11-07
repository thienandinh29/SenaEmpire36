-- Curriculum planning is separate from verified lesson content and the research worker.
create table school_curricula (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references learners(id),
    title text not null,
    goal text not null,
    created_at timestamptz not null default now()
);
create table school_lessons (
    id uuid primary key default gen_random_uuid(),
    curriculum_id uuid not null references school_curricula(id) on delete cascade,
    position integer not null check (position between 1 and 12),
    module text not null,
    title text not null,
    goal text not null,
    topic_id uuid references topic_jobs(id),
    unique(curriculum_id,position)
);
create table school_classes (
    id uuid primary key default gen_random_uuid(),
    owner_id uuid not null references learners(id),
    curriculum_id uuid not null references school_curricula(id),
    name text not null,
    invite_code text not null unique,
    teacher_key_hash text not null,
    created_at timestamptz not null default now()
);
create table school_members (
    class_id uuid not null references school_classes(id) on delete cascade,
    learner_id uuid not null references learners(id),
    joined_at timestamptz not null default now(),
    primary key(class_id,learner_id)
);
create index school_curricula_owner_idx on school_curricula(owner_id);
create index school_classes_owner_idx on school_classes(owner_id);
create index school_members_learner_idx on school_members(learner_id);
alter table school_curricula enable row level security;
alter table school_lessons enable row level security;
alter table school_classes enable row level security;
alter table school_members enable row level security;
