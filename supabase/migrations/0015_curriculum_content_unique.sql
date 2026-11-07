-- Reusing one topic twice must not count the same mastery as two different lessons.
create unique index school_lessons_topic_once_idx on school_lessons(curriculum_id,topic_id)
    where topic_id is not null;
