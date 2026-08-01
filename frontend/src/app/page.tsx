"use client";

import { FormEvent, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_COMVOLY_API_URL ?? "http://localhost:8000";

type Message = {
  id: number;
  telegram_message_id?: number;
  sent_at: string;
  sender: string;
  text: string;
  community_title: string;
};

type Summary = {
  database_found: boolean;
  community_count: number;
  message_count: number;
  media_count: number;
  last_successful_sync: string | null;
  communities: { title: string; source_type: string }[];
};

type Answer = {
  answer: string;
  evidence_count: number;
  citations: Message[];
};

function formatDate(value: string | null) {
  if (!value) return "Not synced yet";
  return new Date(value).toLocaleString();
}

function EvidenceCard({ message }: { message: Message }) {
  return (
    <article id={`message-${message.id}`} className="rounded-2xl border border-white/10 bg-white/[0.05] p-5">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
        <span className="font-semibold text-[#f7c843]">{message.community_title}</span>
        <span>{formatDate(message.sent_at)}</span>
        <span>{message.telegram_message_id ? `Telegram message #${message.telegram_message_id}` : `Archive message M${message.id}`}</span>
      </div>
      <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-100">{message.text}</p>
    </article>
  );
}

export default function Home() {
  const [authState, setAuthState] = useState<"loading" | "authenticated" | "unauthenticated" | "setup" | "offline">("loading");
  const [password, setPassword] = useState("");
  const [loginError, setLoginError] = useState("");
  const [summary, setSummary] = useState<Summary | null>(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [askState, setAskState] = useState<"idle" | "loading" | "error">("idle");
  const [askError, setAskError] = useState("");
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Message[]>([]);
  const [searchedFor, setSearchedFor] = useState("");
  const [searchState, setSearchState] = useState<"idle" | "loading" | "error">("idle");

  useEffect(() => {
    fetch(`${API}/auth/session`, { credentials: "include" })
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.json() as Promise<{ authenticated: boolean; setup_required: boolean }>;
      })
      .then((session) => {
        if (session.setup_required) setAuthState("setup");
        else if (session.authenticated) setAuthState("authenticated");
        else setAuthState("unauthenticated");
      })
      .catch(() => setAuthState("offline"));
  }, []);

  useEffect(() => {
    if (authState !== "authenticated") return;
    fetch(`${API}/status`, { credentials: "include" })
      .then((response) => {
        if (!response.ok) throw new Error();
        return response.json() as Promise<Summary>;
      })
      .then(setSummary)
      .catch(() => setAuthState("unauthenticated"));
  }, [authState]);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoginError("");
    try {
      const response = await fetch(`${API}/auth/login`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });
      const data = (await response.json()) as { detail?: string };
      if (!response.ok) throw new Error(data.detail || "Sign-in failed.");
      setPassword("");
      setAuthState("authenticated");
    } catch (error) {
      setLoginError(error instanceof Error ? error.message : "Sign-in failed.");
    }
  }

  async function logout() {
    await fetch(`${API}/auth/logout`, { method: "POST", credentials: "include" });
    setSummary(null);
    setAnswer(null);
    setResults([]);
    setAuthState("unauthenticated");
  }

  async function ask(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = question.trim();
    if (!value) return;
    setAskState("loading");
    setAskError("");
    setAnswer(null);
    try {
      const response = await fetch(`${API}/ask`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: value }),
      });
      const data = (await response.json()) as Answer & { detail?: string };
      if (!response.ok) throw new Error(data.detail || "Comvoly could not answer that question.");
      setAnswer(data);
      setAskState("idle");
    } catch (error) {
      setAskError(error instanceof Error ? error.message : "Comvoly could not answer that question.");
      setAskState("error");
    }
  }

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;
    setSearchState("loading");
    setSearchedFor(value);
    try {
      const response = await fetch(`${API}/search?q=${encodeURIComponent(value)}`, { credentials: "include" });
      if (!response.ok) throw new Error();
      const data = (await response.json()) as { results: Message[] };
      setResults(data.results);
      setSearchState("idle");
    } catch {
      setResults([]);
      setSearchState("error");
    }
  }

  if (authState !== "authenticated") {
    return (
      <main className="grid min-h-screen place-items-center bg-[#07152d] px-6 text-white">
        <div className="fixed inset-0 bg-[radial-gradient(circle_at_70%_20%,rgba(31,109,232,0.28),transparent_30%),radial-gradient(circle_at_20%_80%,rgba(250,198,59,0.12),transparent_25%)]" />
        <section className="relative w-full max-w-md rounded-3xl border border-white/10 bg-slate-950/60 p-8 shadow-2xl shadow-black/30">
          <div className="flex items-center gap-3"><span className="grid h-11 w-11 place-items-center rounded-xl bg-[#f7c843] text-lg font-black text-[#07152d]">C</span><span className="text-xl font-semibold">Comvoly</span></div>
          <p className="mt-8 text-xs font-semibold uppercase tracking-[0.2em] text-[#f7c843]">Owner access</p>
          <h1 className="mt-3 text-3xl font-semibold">Your community archive is private.</h1>
          {authState === "loading" && <p className="mt-5 text-slate-300">Checking your session…</p>}
          {authState === "offline" && <p className="mt-5 rounded-xl border border-rose-300/20 bg-rose-300/10 p-4 text-rose-200">Comvoly cannot reach the backend. Start Comvoly and refresh this page.</p>}
          {authState === "setup" && <div className="mt-5 rounded-xl border border-amber-200/20 bg-amber-200/10 p-4 text-sm leading-6 text-amber-100"><strong>Owner sign-in needs configuring.</strong><br />Run <code className="text-[#f7c843]">python src\configure_owner.py</code> from the backend folder, then restart Comvoly.</div>}
          {authState === "unauthenticated" && <form onSubmit={login} className="mt-6"><label className="text-sm text-slate-300" htmlFor="password">Owner password</label><input id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required autoFocus className="mt-2 w-full rounded-xl border border-white/10 bg-[#020817] px-4 py-3 outline-none focus:border-[#f7c843]/60" />{loginError && <p className="mt-3 text-sm text-rose-300">{loginError}</p>}<button className="mt-5 w-full rounded-xl bg-[#f7c843] px-5 py-3 font-semibold text-[#07152d] hover:bg-[#ffda6a]">Sign in</button></form>}
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#07152d] text-white">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_82%_12%,rgba(31,109,232,0.3),transparent_28%),radial-gradient(circle_at_12%_88%,rgba(250,198,59,0.14),transparent_25%)]" />
      <div className="relative mx-auto min-h-screen max-w-6xl px-6 py-7 sm:px-10">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#f7c843] text-lg font-black text-[#07152d]">C</span>
            <span className="text-xl font-semibold tracking-tight">Comvoly</span>
          </div>
          <div className="flex items-center gap-3"><span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1.5 text-xs font-semibold text-emerald-200">Owner signed in</span><button onClick={logout} className="text-xs text-slate-400 hover:text-white">Sign out</button></div>
        </header>

        <section className="pb-10 pt-16 sm:pt-24">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#f7c843]">Community intelligence</p>
          <h1 className="mt-5 max-w-3xl text-5xl font-semibold leading-[1.04] tracking-tight sm:text-6xl">Ask what your community knows.</h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">Comvoly interprets your authorised archive and answers with evidence from the original conversation.</p>
        </section>

        <section className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Connected communities", summary?.community_count ?? "—", summary?.communities[0]?.title ?? "Telegram pilot"],
            ["Messages stored", summary?.message_count ?? "—", "Local archive"],
            ["Media references", summary?.media_count ?? "—", "Storage not enabled yet"],
            ["Last successful sync", summary?.last_successful_sync ? formatDate(summary.last_successful_sync) : "—", "Sync agent status"],
          ].map(([label, value, note]) => (
            <div key={label} className="rounded-2xl border border-white/10 bg-white/[0.05] p-5">
              <p className="text-xs text-slate-400">{label}</p><strong className="mt-3 block text-xl text-[#f7c843]">{value}</strong><p className="mt-2 text-xs text-slate-500">{note}</p>
            </div>
          ))}
        </section>

        <section className="mt-6 rounded-3xl border border-[#f7c843]/30 bg-slate-950/50 p-5 shadow-2xl shadow-black/20 sm:p-7">
          <h2 className="text-xl font-semibold">Ask Comvoly</h2>
          <p className="mt-2 text-sm text-slate-400">Answers should be checked against the cited community messages.</p>
          <form onSubmit={ask} className="mt-5 flex flex-col gap-3 sm:flex-row">
            <textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); event.currentTarget.form?.requestSubmit(); } }} maxLength={1000} required className="min-h-28 flex-1 resize-y rounded-2xl border border-white/10 bg-[#020817]/80 p-4 outline-none placeholder:text-slate-500 focus:border-[#f7c843]/60" placeholder="What has the community said about…?" />
            <button disabled={askState === "loading"} className="rounded-2xl bg-[#f7c843] px-6 py-4 font-semibold text-[#07152d] hover:bg-[#ffda6a] disabled:cursor-wait disabled:opacity-60">{askState === "loading" ? "Thinking…" : "Generate answer"}</button>
          </form>
          {askState === "error" && <p className="mt-4 rounded-xl border border-rose-300/20 bg-rose-300/10 p-4 text-sm text-rose-200">{askError}</p>}
          {answer && (
            <div className="mt-6 border-t border-white/10 pt-6">
              <h3 className="text-sm font-semibold uppercase tracking-wider text-[#f7c843]">Comvoly answer</h3>
              <p className="mt-4 whitespace-pre-wrap text-lg leading-8 text-slate-100">{answer.answer}</p>
              <h3 className="mt-8 font-semibold">Supporting community evidence</h3>
              <p className="mt-1 text-sm text-slate-400">{answer.citations.length} cited from {answer.evidence_count} archive messages reviewed</p>
              <div className="mt-4 space-y-3">{answer.citations.length ? answer.citations.map((item) => <EvidenceCard key={item.id} message={item} />) : <p className="rounded-xl bg-white/5 p-4 text-slate-300">No valid message citations were returned. Treat this answer as unsupported.</p>}</div>
            </div>
          )}
        </section>

        <section className="py-12">
          <h2 className="text-xl font-semibold">Search individual messages</h2>
          <form onSubmit={search} className="mt-4 flex gap-3 rounded-2xl border border-white/10 bg-slate-950/55 p-2">
            <input value={query} onChange={(event) => setQuery(event.target.value)} className="min-w-0 flex-1 bg-transparent px-4 py-3 outline-none placeholder:text-slate-500" placeholder="Search exact archive wording…" />
            <button disabled={searchState === "loading"} className="rounded-xl bg-white/10 px-5 py-3 text-sm font-semibold hover:bg-white/15">{searchState === "loading" ? "Searching…" : "Search"}</button>
          </form>
          {searchState === "error" && <p className="mt-4 text-sm text-rose-300">Comvoly cannot reach the backend service.</p>}
          {searchedFor && searchState !== "error" && <div className="mt-6"><div className="mb-4 flex justify-between"><h3 className="font-semibold">Results for “{searchedFor}”</h3><span className="text-sm text-slate-400">{results.length} found</span></div><div className="space-y-3">{results.length ? results.map((item) => <EvidenceCard key={item.id} message={item} />) : <p className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 text-slate-300">No imported messages contain that phrase.</p>}</div></div>}
        </section>

        <footer className="mb-8 rounded-2xl border border-amber-200/20 bg-amber-200/[0.06] p-5 text-sm leading-6 text-amber-100/80"><strong className="text-amber-200">Owner preview:</strong> this build now protects the local archive with an owner session. Multi-member community permissions are still required before a private pilot. Archive evidence is sent to the configured AI provider when you ask a question.</footer>
      </div>
    </main>
  );
}
