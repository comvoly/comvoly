"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { AuthSession, getIdentityToken, getSession, signIn, signOut, signUp } from "@/lib/neon-auth";

type ComvolySession = {
  account_id: string;
  workspaces: Array<{ id: string; name: string; handle: string; lifecycle: string; role: string }>;
};

const AUTH_URL = process.env.NEXT_PUBLIC_NEON_AUTH_URL;
const API_URL = process.env.NEXT_PUBLIC_COMVOLY_API_URL || "https://api.comvoly.com";

export default function AccountPage() {
  if (!AUTH_URL) return <Unavailable />;
  return <ConfiguredAccount authUrl={AUTH_URL} />;
}

function ConfiguredAccount({ authUrl }: { authUrl: string }) {
  const [authSession, setAuthSession] = useState<AuthSession>(null);
  const [checking, setChecking] = useState(true);
  const [mode, setMode] = useState<"sign-in" | "sign-up">("sign-in");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const [comvoly, setComvoly] = useState<ComvolySession | null>(null);

  useEffect(() => {
    let cancelled = false;
    getSession(authUrl).then((session) => {
      if (!cancelled) setAuthSession(session);
    }).catch(() => undefined).finally(() => !cancelled && setChecking(false));
    return () => { cancelled = true; };
  }, [authUrl]);

  useEffect(() => {
    if (!authSession?.user) return;
    let cancelled = false;
    getIdentityToken(authUrl).then(async (token) => {
      if (!token) throw new Error("No verified identity token was returned.");
      const response = await fetch(`${API_URL}/v2/session`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail || "Comvoly could not open your account.");
      if (!cancelled) setComvoly(body);
    }).catch((error: Error) => !cancelled && setMessage(error.message));
    return () => { cancelled = true; };
  }, [authUrl, authSession?.user]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    try {
      await (mode === "sign-up"
        ? signUp(authUrl, { email, password, name: name || email.split("@")[0] })
        : signIn(authUrl, { email, password }));
      setAuthSession(await getSession(authUrl));
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Authentication failed.");
    }
  }

  if (checking) return <Shell><p className="text-slate-300">Checking your account…</p></Shell>;
  if (authSession?.user) {
    return <Shell>
      <div className="flex flex-wrap items-start justify-between gap-5">
        <div><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#ffcf4a]">Your Comvoly account</p>
          <h1 className="mt-3 text-3xl font-semibold">Welcome, {authSession.user.name}</h1>
          <p className="mt-3 text-slate-400">One account. Every community you are authorised to join.</p></div>
        <button onClick={async () => { await signOut(authUrl); setAuthSession(null); setComvoly(null); }} className="rounded-xl border border-white/15 px-4 py-2 text-sm">Sign out</button>
      </div>
      {message && <Notice>{message}</Notice>}
      {!comvoly && !message && <p className="mt-8 text-slate-300">Loading your communities…</p>}
      {comvoly && comvoly.workspaces.length === 0 && <div className="mt-8 rounded-3xl border border-white/10 bg-white/[.035] p-7">
        <h2 className="text-xl font-semibold">You haven&apos;t joined a community yet</h2>
        <p className="mt-3 max-w-2xl leading-7 text-slate-400">Your account is ready, but it has no access to community knowledge. Follow an owner invitation or ask a community owner to approve you.</p>
      </div>}
      {comvoly && comvoly.workspaces.length > 0 && <div className="mt-8 grid gap-4 sm:grid-cols-2">{comvoly.workspaces.map((workspace) => <article key={workspace.id} className="rounded-3xl border border-white/10 bg-white/[.035] p-6"><p className="text-xs uppercase tracking-widest text-[#ffcf4a]">{workspace.role}</p><h2 className="mt-2 text-xl font-semibold">{workspace.name}</h2><p className="mt-2 text-sm text-slate-400">{workspace.lifecycle}</p></article>)}</div>}
    </Shell>;
  }

  return <Shell>
    <p className="text-xs font-semibold uppercase tracking-[.18em] text-[#ffcf4a]">Comvoly account</p>
    <h1 className="mt-3 text-4xl font-semibold tracking-tight">{mode === "sign-up" ? "Create your account" : "Welcome back"}</h1>
    <p className="mt-3 max-w-xl leading-7 text-slate-400">Signing up creates an identity only. Community knowledge remains private until an owner invites or approves you.</p>
    <form onSubmit={submit} className="mt-8 max-w-md space-y-4">
      {mode === "sign-up" && <Field label="Name" value={name} setValue={setName} autoComplete="name" />}
      <Field label="Email" value={email} setValue={setEmail} type="email" autoComplete="email" />
      <Field label="Password" value={password} setValue={setPassword} type="password" autoComplete={mode === "sign-up" ? "new-password" : "current-password"} />
      {message && <Notice>{message}</Notice>}
      <button className="w-full rounded-xl bg-[#ffcf4a] px-5 py-3 font-bold text-[#07152b]">{mode === "sign-up" ? "Create account" : "Sign in"}</button>
    </form>
    <button onClick={() => { setMode(mode === "sign-in" ? "sign-up" : "sign-in"); setMessage(""); }} className="mt-5 text-sm text-slate-300 underline underline-offset-4">{mode === "sign-in" ? "New to Comvoly? Create an account" : "Already have an account? Sign in"}</button>
  </Shell>;
}

function Shell({ children }: { children: React.ReactNode }) {
  return <main className="min-h-screen bg-[#07152d] px-5 py-12 text-white sm:px-8"><div className="mx-auto max-w-4xl"><Link href="/" className="text-2xl font-black tracking-tight">COMVOLY<span className="text-[#ffcf4a]">.</span></Link><section className="mt-12 rounded-[2rem] border border-white/10 bg-[#091a36] p-6 shadow-2xl sm:p-10">{children}</section></div></main>;
}

function Field({ label, value, setValue, type = "text", autoComplete }: { label: string; value: string; setValue: (value: string) => void; type?: string; autoComplete: string }) {
  return <label className="block text-sm text-slate-300">{label}<input required type={type} autoComplete={autoComplete} value={value} onChange={(event) => setValue(event.target.value)} className="mt-2 w-full rounded-xl border border-white/15 bg-[#061124] px-4 py-3 text-white outline-none focus:border-[#ffcf4a]" /></label>;
}

function Notice({ children }: { children: React.ReactNode }) {
  return <p className="mt-5 rounded-xl border border-amber-300/20 bg-amber-300/10 p-4 text-sm text-amber-100">{children}</p>;
}

function Unavailable() {
  return <Shell><h1 className="text-3xl font-semibold">Development sign-in is not configured</h1><p className="mt-4 leading-7 text-slate-400">No authentication endpoint is included in this build. Production access remains unchanged.</p></Shell>;
}
