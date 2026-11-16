import type { Metadata } from "next";

import { ChatShell } from "@/components/chat/chat-shell";

export const metadata: Metadata = {
  title: "Student evaluation",
};

export default function EvaluatePage() {
  return <ChatShell />;
}
