"use client";
import { useState } from "react";
import { ArrowLeft, Copy, RefreshCw, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { percent, type Dashboard } from "@/lib/school";
import { school as t } from "@/messages/school";

export function ClassDashboard({
  data,
  teacherLink,
  busy,
  refresh,
  back,
}: {
  data: Dashboard;
  teacherLink: string;
  busy: boolean;
  refresh: () => void;
  back: () => void;
}) {
  const [filter, setFilter] = useState("");
  const [copied, setCopied] = useState("");
  async function copy(value: string) {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(value);
    } catch {
      setCopied("");
    }
  }
  const students = data.students.filter((student) =>
    student.name
      .toLocaleLowerCase("vi")
      .includes(filter.toLocaleLowerCase("vi")),
  );
  const complete = data.students.reduce(
    (sum, student) => sum + student.completed,
    0,
  );
  const total = data.students.length * data.total_lessons;
  return (
    <>
      <div className="school-actions school-between">
        <Button variant="ghost" onClick={back}>
          <ArrowLeft size={16} aria-hidden="true" />
          {t.back}
        </Button>
        <Button variant="secondary" disabled={busy} onClick={refresh}>
          <RefreshCw size={16} aria-hidden="true" />
          {t.refresh}
        </Button>
      </div>
      <div className="school-section-heading">
        <div>
          <span className="school-eyebrow">
            {t.teacher} · {data.curriculum_title}
          </span>
          <h1>{data.name}</h1>
          <p>{t.classProgress}</p>
        </div>
        <Users size={32} aria-hidden="true" />
      </div>
      <div className="school-stats">
        <div>
          <span>{t.studentCount}</span>
          <strong>{data.students.length}</strong>
        </div>
        <div>
          <span>{t.progress}</span>
          <strong>
            {complete} / {total}
          </strong>
        </div>
        <div>
          <span>{t.classProgress}</span>
          <strong>{total ? percent(complete / total) : "—"}</strong>
        </div>
      </div>
      <section className="school-panel school-share">
        <div>
          <label htmlFor="school-invite-display">{t.invite}</label>
          <div className="school-inline">
            <input
              id="school-invite-display"
              readOnly
              value={data.invite_code}
            />
            <Button variant="secondary" onClick={() => copy(data.invite_code)}>
              <Copy size={16} aria-hidden="true" />
              {copied === data.invite_code ? t.copied : t.copy}
            </Button>
          </div>
        </div>
        {teacherLink && (
          <div>
            <label htmlFor="school-teacher-link">{t.teacherLink}</label>
            <div className="school-inline">
              <input id="school-teacher-link" readOnly value={teacherLink} />
              <Button variant="secondary" onClick={() => copy(teacherLink)}>
                <Copy size={16} aria-hidden="true" />
                {copied === teacherLink ? t.copied : t.copy}
              </Button>
            </div>
            <p className="school-muted">{t.teacherSecret}</p>
          </div>
        )}
      </section>
      <section className="school-panel">
        <div className="school-section-heading">
          <div>
            <h2>{t.weak}</h2>
            <p>{t.weakHint}</p>
          </div>
        </div>
        {!data.concepts.length ? (
          <p className="school-empty">{t.noContent}</p>
        ) : (
          <div className="school-weak-grid">
            {data.concepts.map((concept, i) => (
              <div className="school-weak-card" key={`${concept.lesson}-${i}`}>
                <small>{concept.lesson}</small>
                <h3>{concept.name}</h3>
                <div className="school-inline school-between">
                  <strong>
                    {concept.weak} {t.weakStudents}
                  </strong>
                  <span>{percent(concept.mean_mastery)}</span>
                </div>
                <p>
                  {concept.assessed} {t.assessed} · {concept.unassessed}{" "}
                  {t.notAssessed.toLocaleLowerCase("vi")}
                </p>
              </div>
            ))}
          </div>
        )}
      </section>
      <section className="school-panel">
        <div className="school-section-heading">
          <h2>{t.roster}</h2>
          <label className="school-search">
            <span className="school-sr-only">{t.filter}</span>
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder={t.filter}
            />
          </label>
        </div>
        {!data.students.length ? (
          <p className="school-empty">{t.noStudents}</p>
        ) : (
          <div
            className="school-table-wrap"
            tabIndex={0}
            role="region"
            aria-label={t.roster}
          >
            <table>
              <thead>
                <tr>
                  <th>{t.student}</th>
                  <th>{t.completion}</th>
                  <th>{t.mastery}</th>
                  <th>{t.attempts}</th>
                  <th>{t.accuracy}</th>
                  <th>{t.lessonProgress}</th>
                </tr>
              </thead>
              <tbody>
                {students.map((student) => (
                  <tr key={student.learner_id}>
                    <th scope="row">{student.name}</th>
                    <td>
                      {student.completed}/{student.lessons}
                    </td>
                    <td>
                      {percent(student.mean_mastery)}
                      <small>
                        {student.assessed_concepts} {t.assessed}
                      </small>
                    </td>
                    <td>{student.attempts}</td>
                    <td>{percent(student.correct_rate)}</td>
                    <td>
                      <div className="school-mini-lessons">
                        {student.lesson_states.map((state, index) => (
                          <span
                            className={`school-mini-lesson ${state}`}
                            key={index}
                            title={`${t.lesson} ${index + 1}: ${t.states[state]}`}
                            aria-label={`${t.lesson} ${index + 1}: ${t.states[state]}`}
                          >
                            {index + 1}
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
