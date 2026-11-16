import type { Metadata } from "next";

import { LoginForm } from "@/components/auth/login-form";

export const metadata: Metadata = {
  title: "Reviewer sign in",
};

export default function LoginPage() {
  return <LoginForm />;
}
