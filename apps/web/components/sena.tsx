"use client";
import { studio as t } from "@/messages/studio";
export type SenaMood = "hello" | "focus" | "happy" | "oops" | "think" | "sleep";
const moods: SenaMood[] = ["hello", "focus", "happy", "oops", "think", "sleep"];
export function Sena({
  size = 120,
  mood = "hello",
}: {
  size?: number;
  mood?: SenaMood;
}) {
  const sleeping = mood === "sleep";
  return (
    <svg
      className={`sena-character sena-${mood}`}
      width={size}
      height={size}
      viewBox="0 0 240 250"
      role="img"
      aria-label={t.states[moods.indexOf(mood)]}
    >
      <path
        d="M169 205c72 1 51-88 24-62-11 13 11 23 16 10"
        fill="none"
        stroke="#95603d"
        strokeWidth="13"
        strokeLinecap="round"
      />
      <ellipse cx="120" cy="235" rx="61" ry="9" fill="#3928a8" opacity=".07" />
      <circle cx="47" cy="105" r="27" fill="#95603d" />
      <circle cx="47" cy="105" r="17" fill="#e7bb94" />
      <circle cx="193" cy="105" r="27" fill="#95603d" />
      <circle cx="193" cy="105" r="17" fill="#e7bb94" />
      <path d="M68 195q5-38 27-40h50q28 7 29 74H69Z" fill="#f2ebd9" />
      <path
        d="m99 160 21 16 22-16"
        fill="none"
        stroke="#d4c2a4"
        strokeWidth="3"
      />
      <text
        x="107"
        y="202"
        fill="#b59c7c"
        fontSize="16"
        fontFamily="Georgia"
        fontWeight="bold"
      >
        NT
      </text>
      <path
        d="m83 216 5-5 5 5-5 5Zm59-29 5-5 5 5-5 5Zm0 35 5-5 5 5-5 5Z"
        fill="#d4c0a1"
      />
      <ellipse cx="120" cy="101" rx="75" ry="70" fill="#95603d" />
      <path
        d="M58 95q11-45 62-26 53-20 64 26 12 60-64 64-76-5-62-64Z"
        fill="#f3d5a9"
      />
      <path
        d="M45 83Q40 8 120 10q78 1 76 74l-17-12-13 5-14-10-14 7-18-8-16 9-14-8-16 10-15-4Z"
        fill="#2f2421"
      />
      {[65, 84, 103, 123, 143, 163, 180].map((x, i) => (
        <path
          key={x}
          d={`M${x} ${48 - Math.sin(i / 2) * 20}l5 24`}
          stroke="#493632"
          strokeWidth="3"
          strokeLinecap="round"
        />
      ))}
      <path
        d="M83 91q11-8 23-1m28 0q11-8 23 1"
        stroke="#392b24"
        strokeWidth="4"
        fill="none"
        strokeLinecap="round"
      />
      {sleeping ? (
        <path
          d="M83 111q10 9 21 0m31 0q10 9 21 0"
          stroke="#392b24"
          strokeWidth="4"
          fill="none"
        />
      ) : (
        <>
          {[94, 145].map((x) => (
            <g key={x}>
              <ellipse cx={x} cy="111" rx="12" ry="16" fill="white" />
              <ellipse cx={x + 1} cy="113" rx="8" ry="11" fill="#2d292b" />
              <circle cx={x - 1} cy="108" r="3.5" fill="white" />
            </g>
          ))}
        </>
      )}
      <ellipse cx="77" cy="134" rx="11" ry="7" fill="#e9a68c" opacity=".7" />
      <ellipse cx="164" cy="134" rx="11" ry="7" fill="#e9a68c" opacity=".7" />
      <circle cx="115" cy="137" r="2.5" fill="#63422b" />
      <circle cx="125" cy="137" r="2.5" fill="#63422b" />
      {mood === "oops" || sleeping ? (
        <ellipse cx="120" cy="150" rx="6" ry="8" fill="#79462d" />
      ) : (
        <>
          <path d="M103 151q17 24 35-1Z" fill="#773b2d" />
          <path d="M110 159q10-7 21 0l-11 7Z" fill="#ec9c8b" />
        </>
      )}
      <path
        d="M54 116q-3 43 44 59m88-59q3 43-44 59"
        stroke="white"
        strokeWidth="2"
        fill="none"
      />
      <circle cx="49" cy="116" r="6" fill="white" />
      <circle cx="191" cy="116" r="6" fill="white" />
      <circle cx="198" cy="129" r="4" fill="#d5d5dd" />
      <rect
        x="149"
        y="192"
        width="26"
        height="34"
        rx="3"
        transform="rotate(-12 149 192)"
        fill="#5140d7"
      />
      <path d="m155 194 5 28" stroke="#a79cf3" strokeWidth="2" />
      <circle cx="166" cy="216" r="11" fill="#95603d" />
      {mood === "focus" ? (
        <path
          d="M89 203q17-19 29-50"
          stroke="#95603d"
          strokeWidth="14"
          strokeLinecap="round"
        />
      ) : mood === "think" || mood === "oops" ? (
        <path
          d="M86 205q-4-35 25-48"
          stroke="#95603d"
          strokeWidth="15"
          strokeLinecap="round"
        />
      ) : (
        <path
          d="M86 199q-37-15-39-48"
          stroke="#95603d"
          strokeWidth="16"
          strokeLinecap="round"
        />
      )}
      {mood === "happy" && (
        <path
          d="M23 149q-17-14-20-2-2 12 20 21 23-16 15-24-8-7-15 5"
          fill="#d98096"
        />
      )}
      {mood === "think" && (
        <text x="195" y="47" fontSize="32" fill="#5140d7" fontWeight="bold">
          ?
        </text>
      )}
      {sleeping && (
        <text x="195" y="52" fontSize="24" fill="#5140d7">
          z Z
        </text>
      )}
    </svg>
  );
}
