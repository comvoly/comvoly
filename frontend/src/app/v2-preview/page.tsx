import { notFound } from "next/navigation";
import WorkspacePreview from "./workspace-preview";

export default function V2PreviewPage() {
  if (process.env.NEXT_PUBLIC_COMVOLY_V2_PREVIEW !== "true") notFound();
  return <WorkspacePreview />;
}
