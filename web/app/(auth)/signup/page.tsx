import { SignupForm } from "@/components/auth/signup-form";

export const metadata = {
  title: "Sign up - GEOlyze",
  description: "Create your GEOlyze account and start analyzing GEO datasets",
};

export default function SignupPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <SignupForm />
    </div>
  );
}
