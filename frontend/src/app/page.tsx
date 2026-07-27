"use client";

import { FormEvent, useState } from "react";

type SearchResult = {
  telegram_message_id: number;
  sent_at: string;
  text: string;
  community_title: string;
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searchedFor, setSearchedFor] = useState("");
  const [status, setStatus] = useState<"idle" | "searching" | "error">("idle");

  async function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();
    if (!trimmedQuery) return;

    setStatus("searching");
    setSearchedFor(trimmedQuery);
    try {
      const response = await fetch(
        `http://127.0.0.1:8000/search?q=${encodeURIComponent(trimmedQuery)}`,
      );
      if (!response.ok) throw new Error("The Comvoly search service is unavailable.");
      const data = (await response.json()) as { results: SearchResult[] };
      setResults(data.results);
      setStatus("idle");
    } catch {
      setResults([]);
      setStatus("error");
    }
  }

  return (
    <main className="min-h-screen bg-[#07152d] text-white">
      <div className="absolute inset-0 -z-0 bg-[radial-gradient(circle_at_82%_12%,rgba(31,109,232,0.3),transparent_28%),radial-gradient(circle_at_12%_88%,rgba(250,198,59,0.14),transparent_25%)]" />
      <div className="relative z-10 mx-auto min-h-screen max-w-5xl px-6 py-7 sm:px-10">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="grid h-10 w-10 place-items-center rounded-xl bg-[#f7c843] text-lg font-black text-[#07152d]">K</span>
            <span className="text-xl font-semibold tracking-tight">Comvoly</span>
          </div>
          <span className="rounded-full border border-emerald-300/20 bg-emerald-300/10 px-3 py-1.5 text-xs font-semibold text-emerald-200">
            Local prototype
          </span>
        </header>

        <section className="py-16 sm:py-24">
          <p className="text-sm font-semibold uppercase tracking-[0.22em] text-[#f7c843]">Community intelligence</p>
          <h1 className="mt-5 max-w-3xl text-5xl font-semibold leading-[1.04] tracking-tight sm:text-6xl">
            Find the knowledge buried in your community.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            Search the Telegram messages you have already imported into Comvoly. Every result remains linked to its original conversation data.
          </p>

          <form onSubmit={search} className="mt-10 flex max-w-3xl gap-3 rounded-2xl border border-white/10 bg-slate-950/55 p-2 shadow-xl shadow-black/20 backdrop-blur">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="min-w-0 flex-1 bg-transparent px-4 py-3 text-base outline-none placeholder:text-slate-500"
              placeholder="Search your imported messages…"
              aria-label="Search imported messages"
            />
            <button
              type="submit"
              disabled={status === "searching"}
              className="rounded-xl bg-[#f7c843] px-5 py-3 text-sm font-semibold text-[#07152d] transition hover:bg-[#ffda6a] disabled:cursor-wait disabled:opacity-70"
            >
              {status === "searching" ? "Searching…" : "Search"}
            </button>
          </form>

          {status === "error" && (
            <p className="mt-4 text-sm text-rose-300">
              Comvoly cannot reach the local search service. Start the backend search server, then try again.
            </p>
          )}
        </section>

        {searchedFor && status !== "error" && (
          <section className="pb-16">
            <div className="mb-5 flex items-baseline justify-between gap-4">
              <h2 className="text-xl font-semibold">Results for “{searchedFor}”</h2>
              <p className="text-sm text-slate-400">{results.length} found</p>
            </div>
            {results.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-6 text-slate-300">
                No imported messages contain that phrase yet. Try another word or import more messages.
              </div>
            ) : (
              <div className="space-y-3">
                {results.map((result) => (
                  <article key={result.telegram_message_id} className="rounded-2xl border border-white/10 bg-white/[0.05] p-5">
                    <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-slate-400">
                      <span className="font-semibold text-[#f7c843]">{result.community_title}</span>
                      <span>{new Date(result.sent_at).toLocaleString()}</span>
                      <span>Message #{result.telegram_message_id}</span>
                    </div>
                    <p className="mt-3 whitespace-pre-wrap leading-7 text-slate-100">{result.text}</p>
                  </article>
                ))}
              </div>
            )}
          </section>
        )}
      </div>
    </main>
  );
}
