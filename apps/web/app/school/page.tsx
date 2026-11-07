import type { Metadata } from "next";
import { getWebConfig } from "@/lib/config";
import { SchoolWorkspace } from "./school-workspace";
import "./school.css";

export const dynamic = "force-dynamic";
export const metadata: Metadata = {
  title: "NodeTrail · Khóa học và lớp học",
  referrer: "no-referrer",
};
export default function SchoolPage() {
  return <SchoolWorkspace config={getWebConfig()} />;
}
