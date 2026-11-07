from datetime import datetime
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Record(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class LessonOutline(Record):
    module: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=160)
    goal: str = Field(min_length=10, max_length=500)


class Outline(Record):
    title: str = Field(min_length=1, max_length=160)
    goal: str = Field(min_length=10, max_length=500)
    lessons: list[LessonOutline] = Field(min_length=2, max_length=12)

    @model_validator(mode="after")
    def unique_lessons(self) -> Self:
        if len({lesson.title.casefold() for lesson in self.lessons}) != len(self.lessons):
            raise ValueError("Lesson titles must be unique")
        if len({lesson.goal.casefold() for lesson in self.lessons}) != len(self.lessons):
            raise ValueError("Lesson goals must be unique")
        return self


class OutlineRequest(Record):
    goal: str = Field(min_length=10, max_length=500)
    lesson_count: int = Field(default=6, ge=2, le=12)


class Lesson(LessonOutline):
    id: UUID
    position: int
    state: Literal[
        "locked",
        "not_started",
        "queued",
        "researching",
        "indexing",
        "graph",
        "ready",
        "learning",
        "completed",
        "failed",
    ]
    topic_id: UUID | None = None
    subject: str | None = None
    step_vi: str = ""
    concepts: int = 0
    assessed: int = 0
    mastered: int = 0
    confirmed: bool = False
    material_goal: str | None = None


class Curriculum(Record):
    id: UUID
    title: str
    goal: str
    completed: int
    can_manage: bool
    lessons: list[Lesson]


class CurriculumSummary(Record):
    id: UUID
    title: str
    goal: str
    lesson_count: int


class StartLesson(Record):
    retry: bool = False


class LinkLesson(Record):
    topic_id: UUID


class LibraryLesson(Record):
    topic_id: UUID
    goal: str
    concepts: list[str]


class NewClass(Record):
    name: str = Field(min_length=1, max_length=120)
    curriculum_id: UUID


class ClassSummary(Record):
    id: UUID
    name: str
    curriculum_id: UUID
    curriculum_title: str
    role: Literal["teacher", "student"]


class ClassCreated(ClassSummary):
    invite_code: str
    teacher_key: str


class JoinClass(Record):
    invite_code: str = Field(pattern=r"^[A-Za-z0-9_-]{16}$")


class StudentProgress(Record):
    learner_id: UUID
    name: str
    completed: int
    lessons: int
    assessed_concepts: int
    mean_mastery: float | None
    attempts: int
    correct_rate: float | None
    last_active: datetime | None
    lesson_states: list[str]


class WeakConcept(Record):
    lesson: str
    name: str
    assessed: int
    weak: int
    unassessed: int
    mean_mastery: float | None


class Dashboard(ClassSummary):
    invite_code: str
    total_lessons: int
    students: list[StudentProgress]
    concepts: list[WeakConcept]
