"use client";

import Link from "next/link";
import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { api, ComvolySession, WorkspaceDetail, WorkspaceSummary } from "@/lib/comvoly-api";
import { AuthSession, getIdentityToken, getSession, signIn, signOut, signUp } from "@/lib/neon-auth";

const AUTH_URL = process.env.NEXT_PUBLIC_NEON_AUTH_URL;
const API_URL = process.env.NEXT_PUBLIC_COMVOLY_API_URL || "https://api.comvoly.com";

type TelegramPreview = {
  parser_version: string; external_community_id: string; community_name: string; export_type: string;
  message_count: number; service_event_count: number; participant_count: number; media_count: number;
  history_start: string | null; history_end: string | null; warnings: string[];
};

type TelegramLiveStatus = {
  source_id: string; state: string; configured: boolean; bot_username?: string;
  membership_status?: string; receives_messages?: boolean; last_received_at?: string | null;
  install_url?: string; webhook_url?: string;
};

type IntelligenceAnswer = {
  question: string; answer: string; evidence_count: number; mode: string;
  citations: Array<{ content_id: string; source_name: string; provider: string;
    external_item_id: string; author: string; source_created_at: string; excerpt: string }>;
};

export default function AccountPage() {
  if (!AUTH_URL) return <Shell><h1 className="text-3xl font-semibold">Development sign-in is not configured</h1><p className="mt-4 text-slate-400">Production access remains unchanged.</p></Shell>;
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
  const [token, setToken] = useState("");
  const [session, setSession] = useState<ComvolySession | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<WorkspaceDetail | null>(null);

  const refreshSession = useCallback(async () => {
    const identityToken = await getIdentityToken(authUrl);
    const body = await api<ComvolySession>(API_URL, identityToken, "/v2/session");
    setToken(identityToken);
    setSession(body);
    setSelectedId((current) => current || body.workspaces[0]?.id || "");
  }, [authUrl]);

  useEffect(() => {
    let cancelled = false;
    getSession(authUrl).then((value) => { if (!cancelled) setAuthSession(value); })
      .catch(() => undefined).finally(() => !cancelled && setChecking(false));
    return () => { cancelled = true; };
  }, [authUrl]);

  useEffect(() => {
    if (!authSession?.user) return;
    const timer = window.setTimeout(() => {
      refreshSession().catch((error: Error) => setMessage(error.message));
    }, 0);
    return () => window.clearTimeout(timer);
  }, [authSession?.user, refreshSession]);

  useEffect(() => {
    if (!selectedId || !token) return;
    api<WorkspaceDetail>(API_URL, token, `/v2/workspaces/${selectedId}`)
      .then(setDetail).catch((error: Error) => setMessage(error.message));
  }, [selectedId, token]);

  useEffect(() => {
    if (!token || typeof window === "undefined") return;
    const invite = new URLSearchParams(window.location.search).get("invite");
    if (!invite) return;
    api<{ workspace_id: string }>(API_URL, token, "/v2/invitations/accept", {
      method: "POST", body: JSON.stringify({ token: invite }),
    }).then(async ({ workspace_id }) => {
      await refreshSession(); setSelectedId(workspace_id); setMessage("Invitation accepted. Welcome to the community.");
      window.history.replaceState({}, "", "/account");
    }).catch((error: Error) => setMessage(error.message));
  }, [token, refreshSession]);

  async function submit(event: FormEvent) {
    event.preventDefault(); setMessage("");
    try {
      await (mode === "sign-up" ? signUp(authUrl, { email, password, name: name || email.split("@")[0] }) : signIn(authUrl, { email, password }));
      setAuthSession(await getSession(authUrl));
    } catch (error) { setMessage(error instanceof Error ? error.message : "Authentication failed."); }
  }

  if (checking) return <Shell><p className="text-slate-300">Checking your account…</p></Shell>;
  if (!authSession?.user) return <Shell>
    <Eyebrow>Comvoly account</Eyebrow>
    <h1 className="mt-3 text-4xl font-semibold">{mode === "sign-up" ? "Create your account" : "Welcome back"}</h1>
    <p className="mt-3 max-w-xl leading-7 text-slate-400">One sign-in for every community you own or join. Knowledge remains private until an owner invites or approves you.</p>
    <form onSubmit={submit} className="mt-8 max-w-md space-y-4">
      {mode === "sign-up" && <Field label="Name" value={name} setValue={setName} autoComplete="name" />}
      <Field label="Email" value={email} setValue={setEmail} type="email" autoComplete="email" />
      <Field label="Password" value={password} setValue={setPassword} type="password" autoComplete={mode === "sign-up" ? "new-password" : "current-password"} />
      {message && <Notice>{message}</Notice>}
      <Primary>{mode === "sign-up" ? "Create account" : "Sign in"}</Primary>
    </form>
    <button onClick={() => { setMode(mode === "sign-in" ? "sign-up" : "sign-in"); setMessage(""); }} className="mt-5 text-sm text-slate-300 underline underline-offset-4">{mode === "sign-in" ? "New to Comvoly? Create an account" : "Already have an account? Sign in"}</button>
  </Shell>;

  return <Shell wide>
    <header className="flex flex-wrap items-start justify-between gap-5">
      <div><Eyebrow>Your Comvoly account</Eyebrow><h1 className="mt-3 text-3xl font-semibold">Welcome, {authSession.user.name}</h1><p className="mt-2 text-slate-400">One account. Every authorised community.</p></div>
      <button onClick={async () => { await signOut(authUrl); setAuthSession(null); setSession(null); }} className="rounded-xl border border-white/15 px-4 py-2 text-sm">Sign out</button>
    </header>
    {message && <Notice>{message}</Notice>}
    {!session && !message && <p className="mt-8 text-slate-300">Loading your communities…</p>}
    {session && <AccountHome session={session} selectedId={selectedId} select={setSelectedId} detail={detail} token={token}
      refresh={async () => { await refreshSession(); if (selectedId) setDetail(await api<WorkspaceDetail>(API_URL, token, `/v2/workspaces/${selectedId}`)); }} setMessage={setMessage} />}
  </Shell>;
}

function AccountHome({ session, selectedId, select, detail, token, refresh, setMessage }: {
  session: ComvolySession; selectedId: string; select: (id: string) => void; detail: WorkspaceDetail | null;
  token: string; refresh: () => Promise<void>; setMessage: (value: string) => void;
}) {
  const [showCreate, setShowCreate] = useState(false);
  return <div className="mt-9 grid gap-6 lg:grid-cols-[17rem_1fr]">
    <aside className="rounded-3xl border border-white/10 bg-white/[.025] p-4">
      <div className="flex items-center justify-between px-2"><h2 className="font-semibold">Communities</h2><button onClick={() => setShowCreate(!showCreate)} className="rounded-lg bg-[#ffcf4a] px-3 py-1.5 text-sm font-bold text-[#07152b]">New</button></div>
      {showCreate && <CreateWorkspace token={token} onCreated={async (id) => { await refresh(); select(id); setShowCreate(false); }} />}
      <div className="mt-4 space-y-2">{session.workspaces.map((workspace) => <WorkspaceButton key={workspace.id} workspace={workspace} selected={selectedId === workspace.id} onClick={() => select(workspace.id)} />)}</div>
      {!session.workspaces.length && <p className="mt-5 px-2 text-sm leading-6 text-slate-400">No communities yet. Create one as an owner or follow an invitation from another owner.</p>}
    </aside>
    <section>{selectedId ? (detail ? <WorkspacePanel detail={detail} token={token} refresh={refresh} setMessage={setMessage} /> : <p className="text-slate-300">Opening community…</p>) : <EmptyState />}</section>
  </div>;
}

function CreateWorkspace({ token, onCreated }: { token: string; onCreated: (id: string) => Promise<void> }) {
  const [name, setName] = useState(""); const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  const handle = useMemo(() => name.toLowerCase().trim().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 48), [name]);
  return <form className="mt-4 rounded-2xl border border-white/10 bg-[#061124] p-3" onSubmit={async (event) => { event.preventDefault(); setBusy(true); setError(""); try { const result = await api<{ workspace_id: string }>(API_URL, token, "/v2/workspaces", { method: "POST", body: JSON.stringify({ name, handle }) }); await onCreated(result.workspace_id); } catch (e) { setError(e instanceof Error ? e.message : "Could not create community."); } finally { setBusy(false); } }}>
    <label className="text-xs text-slate-400">Community name<input required value={name} onChange={(e) => setName(e.target.value)} className="mt-2 w-full rounded-lg border border-white/15 bg-[#07152d] px-3 py-2 text-sm text-white" /></label>
    <p className="mt-2 truncate text-xs text-slate-500">comvoly / {handle || "community"}</p>{error && <p className="mt-2 text-xs text-rose-300">{error}</p>}
    <button disabled={busy} className="mt-3 w-full rounded-lg border border-[#ffcf4a]/40 px-3 py-2 text-xs font-semibold text-[#ffcf4a]">{busy ? "Creating…" : "Create workspace"}</button>
  </form>;
}

function WorkspacePanel({ detail, token, refresh, setMessage }: { detail: WorkspaceDetail; token: string; refresh: () => Promise<void>; setMessage: (value: string) => void }) {
  const ownerTools = detail.capabilities.includes("manage_sources");
  const completed = detail.setup_steps.filter((step) => step.state === "completed").length;
  return <div className="space-y-6">
    <div className="rounded-3xl border border-white/10 bg-white/[.035] p-6"><Eyebrow>{detail.role}</Eyebrow><h2 className="mt-2 text-3xl font-semibold">{detail.workspace.name}</h2><p className="mt-2 text-slate-400">{detail.workspace.lifecycle === "setup" ? "Setting up community intelligence" : detail.workspace.lifecycle}</p></div>
    {ownerTools && <div className="rounded-3xl border border-[#ffcf4a]/20 bg-[#ffcf4a]/[.04] p-6"><div className="flex items-center justify-between gap-4"><div><h3 className="text-lg font-semibold">Owner setup</h3><p className="mt-1 text-sm text-slate-400">{completed} of {detail.setup_steps.length} steps complete</p></div><span className="text-2xl font-bold text-[#ffcf4a]">{detail.setup_steps.length ? Math.round(completed / detail.setup_steps.length * 100) : 0}%</span></div><div className="mt-5 space-y-2">{detail.setup_steps.map((step) => <SetupStep key={step.step_key} step={step} workspaceId={detail.workspace.id} token={token} refresh={refresh} />)}</div></div>}
    <WorkspaceIntelligencePanel detail={detail} token={token} />
    <Sources detail={detail} token={token} refresh={refresh} />
    {detail.capabilities.includes("invite_members") && <Invite workspaceId={detail.workspace.id} token={token} setMessage={setMessage} refresh={refresh} />}
  </div>;
}

const stepLabels: Record<string, string> = { community_details: "Confirm community details", connect_source: "Plan a platform connection", import_history: "Import historical knowledge", review_knowledge: "Review imported knowledge", invite_members: "Invite your first member" };
function SetupStep({ step, workspaceId, token, refresh }: { step: WorkspaceDetail["setup_steps"][number]; workspaceId: string; token: string; refresh: () => Promise<void> }) {
  return <div className="flex items-center justify-between gap-3 rounded-xl bg-white/[.035] px-4 py-3"><div><p className="text-sm font-medium">{stepLabels[step.step_key] || step.step_key}</p><p className="mt-1 text-xs capitalize text-slate-500">{step.state.replace("_", " ")}</p></div>{step.state !== "completed" && <button onClick={async () => { await api(API_URL, token, `/v2/workspaces/${workspaceId}/setup/${step.step_key}`, { method: "POST", body: JSON.stringify({ state: "completed" }) }); await refresh(); }} className="text-xs font-semibold text-[#ffcf4a]">Mark done</button>}</div>;
}

function Sources({ detail, token, refresh }: { detail: WorkspaceDetail; token: string; refresh: () => Promise<void> }) {
  const [provider, setProvider] = useState("telegram"); const [displayName, setDisplayName] = useState(""); const canManage = detail.capabilities.includes("manage_sources");
  return <div className="rounded-3xl border border-white/10 bg-white/[.035] p-6"><h3 className="text-lg font-semibold">Connected knowledge sources</h3><p className="mt-2 text-sm leading-6 text-slate-400">Plan platform connections here. Telegram Desktop history can now be imported below; ongoing platform connections remain disabled until their credentials and permissions are approved.</p>
    <div className="mt-5 space-y-3">{detail.sources.map((source) => <div key={source.id} className="flex items-center justify-between rounded-xl border border-white/10 px-4 py-3"><div><p className="font-medium">{source.display_name}</p><p className="mt-1 text-xs capitalize text-slate-500">{source.provider} · {source.state}</p></div><span className={`rounded-full px-3 py-1 text-xs ${source.state === "connected" ? "bg-emerald-400/10 text-emerald-200" : "bg-slate-700"}`}>{source.state === "connected" ? "Connected" : "Not connected"}</span></div>)}{!detail.sources.length && <p className="text-sm text-slate-500">No sources planned yet.</p>}</div>
    {canManage && <form className="mt-5 grid gap-3 sm:grid-cols-[9rem_1fr_auto]" onSubmit={async (event) => { event.preventDefault(); await api(API_URL, token, `/v2/workspaces/${detail.workspace.id}/sources`, { method: "POST", body: JSON.stringify({ provider, display_name: displayName }) }); setDisplayName(""); await refresh(); }}><select value={provider} onChange={(e) => setProvider(e.target.value)} className="rounded-xl border border-white/15 bg-[#061124] px-3 py-2 text-sm"><option value="telegram">Telegram</option><option value="discord">Discord</option><option value="skool">Skool</option></select><input required placeholder="Community or server name" value={displayName} onChange={(e) => setDisplayName(e.target.value)} className="rounded-xl border border-white/15 bg-[#061124] px-3 py-2 text-sm" /><button className="rounded-xl bg-white/10 px-4 py-2 text-sm font-semibold">Plan source</button></form>}
    {canManage && <TelegramHistoryImport detail={detail} token={token} refresh={refresh} />}
    <div className="mt-6 border-t border-white/10 pt-5"><h4 className="font-medium">Import history</h4>{detail.imports.length ? detail.imports.map((job) => <div key={job.id} className="mt-3 rounded-xl bg-[#061124] p-3 text-sm text-slate-300"><div className="flex justify-between gap-3"><span className="capitalize">{job.stage.replace("_", " ")}</span><span>{job.progress_current}/{job.progress_total ?? "?"}</span></div>{job.warning_count + job.failure_count > 0 && <p className="mt-2 text-xs text-amber-200">{job.warning_count} warnings · {job.failure_count} failures</p>}</div>) : <p className="mt-2 text-sm text-slate-500">No historical imports yet.</p>}</div>
  </div>;
}

function TelegramHistoryImport({ detail, token, refresh }: { detail: WorkspaceDetail; token: string; refresh: () => Promise<void> }) {
  const [document, setDocument] = useState<Record<string, unknown> | null>(null);
  const [preview, setPreview] = useState<TelegramPreview | null>(null);
  const [fileName, setFileName] = useState("");
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");
  const telegramSource = detail.sources.find((source) => source.provider === "telegram");

  async function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setError(""); setPreview(null); setDocument(null); setFileName(file.name);
    if (file.size > 25 * 1024 * 1024) { setError("This browser pilot accepts result.json files up to 25 MB."); return; }
    try {
      const parsed = JSON.parse(await file.text()) as Record<string, unknown>;
      const result = await api<TelegramPreview>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/preview`, {
        method: "POST", body: JSON.stringify({ export: parsed }),
      });
      setDocument(parsed); setPreview(result);
    } catch (e) { setError(e instanceof Error ? e.message : "That Telegram export could not be read."); }
  }

  async function importHistory() {
    if (!document || !preview || !Array.isArray(document.messages)) return;
    setBusy(true); setError(""); setProgress(0);
    try {
      const started = await api<{ job_id: string; source_id: string }>(API_URL, token,
        `/v2/workspaces/${detail.workspace.id}/telegram/imports`, {
          method: "POST", body: JSON.stringify({ summary: preview, source_id: telegramSource?.id,
            idempotency_key: `browser-${crypto.randomUUID()}` }),
        });
      const chunks: unknown[][] = [];
      for (let index = 0; index < document.messages.length; index += 200) chunks.push(document.messages.slice(index, index + 200));
      for (let index = 0; index < chunks.length; index += 1) {
        const result = await api<{ progress_current: number }>(API_URL, token,
          `/v2/workspaces/${detail.workspace.id}/telegram/imports/${started.job_id}/chunks`, {
            method: "POST", body: JSON.stringify({ chunk_index: index, messages: chunks[index] }),
          });
        setProgress(result.progress_current);
      }
      await api(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/imports/${started.job_id}/complete`, { method: "POST", body: "{}" });
      setProgress(preview.message_count); await refresh();
    } catch (e) { setError(e instanceof Error ? e.message : "The import stopped safely and can be retried."); }
    finally { setBusy(false); }
  }

  return <div className="mt-7 border-t border-white/10 pt-6">
    <Eyebrow>Telegram history</Eyebrow><h4 className="mt-2 text-lg font-semibold">Import the knowledge from before the bot joins</h4>
    <p className="mt-2 text-sm leading-6 text-slate-400">In Telegram Desktop, export the intended group as machine-readable JSON and select its <code className="text-slate-300">result.json</code>. Comvoly inventories it before storing messages. Media files are counted but are not uploaded in this milestone.</p>
    <label className="mt-4 block cursor-pointer rounded-2xl border border-dashed border-white/20 bg-[#061124] p-5 text-center text-sm hover:border-[#ffcf4a]/60"><span className="font-semibold text-[#ffcf4a]">Choose Telegram result.json</span><input type="file" accept="application/json,.json" onChange={chooseFile} className="sr-only" /></label>
    {fileName && <p className="mt-2 text-xs text-slate-500">Selected: {fileName}</p>}{error && <p className="mt-3 rounded-xl bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
    {preview && <div className="mt-5 rounded-2xl border border-white/10 bg-[#061124] p-5"><div className="flex flex-wrap items-start justify-between gap-3"><div><p className="font-semibold">{preview.community_name}</p><p className="mt-1 text-xs text-slate-500">{preview.export_type} · {preview.parser_version}</p></div><span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs text-emerald-200">Preview ready</span></div><div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4"><Metric label="Messages" value={preview.message_count} /><Metric label="People" value={preview.participant_count} /><Metric label="Media refs" value={preview.media_count} /><Metric label="Service events" value={preview.service_event_count} /></div><p className="mt-4 text-xs text-slate-500">{formatDate(preview.history_start)} – {formatDate(preview.history_end)}</p>{preview.warnings.map((warning) => <p key={warning} className="mt-2 text-xs text-amber-200">{warning}</p>)}<button disabled={busy} onClick={importHistory} className="mt-5 w-full rounded-xl bg-[#ffcf4a] px-4 py-3 font-bold text-[#07152b]">{busy ? `Importing ${progress}/${preview.message_count}…` : progress === preview.message_count && progress > 0 ? "Imported — ready for review" : `Import ${preview.message_count} messages`}</button></div>}
    <TelegramLiveSetup detail={detail} token={token} sourceId={telegramSource?.id || ""} />
  </div>;
}

function TelegramLiveSetup({ detail, token, sourceId }: { detail: WorkspaceDetail; token: string; sourceId: string }) {
  const [status, setStatus] = useState<TelegramLiveStatus | null>(null);
  const [error, setError] = useState(""); const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    if (!sourceId) { setStatus(null); return; }
    try { setStatus(await api<TelegramLiveStatus>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/live/status/${sourceId}`)); }
    catch (e) { setError(e instanceof Error ? e.message : "Could not check the Telegram connection."); }
  }, [detail.workspace.id, sourceId, token]);
  useEffect(() => { const timer = window.setTimeout(() => { void load(); }, 0); return () => window.clearTimeout(timer); }, [load]);
  return <div className="mt-5 rounded-2xl border border-white/10 p-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><p className="font-medium">Ongoing Telegram updates</p><p className="mt-1 text-xs capitalize text-slate-500">{status?.state?.replaceAll("_", " ") || (sourceId ? "Checking availability" : "Plan a Telegram source first")}</p></div>{status?.state === "connected" && <span className="rounded-full bg-emerald-400/10 px-3 py-1 text-xs text-emerald-200">Receiving messages</span>}</div>
    <p className="mt-3 text-sm leading-6 text-slate-400">The official Comvoly bot will collect messages posted after it joins. Historical knowledge remains covered by the export above.</p>
    {status?.configured && ["not_prepared", "awaiting_bot"].includes(status.state) && !status.install_url && <button disabled={busy} onClick={async () => { setBusy(true); setError(""); try { const result = await api<TelegramLiveStatus>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/telegram/live/prepare`, { method: "POST", body: JSON.stringify({ source_id: sourceId }) }); setStatus(result); } catch (e) { setError(e instanceof Error ? e.message : "Could not prepare the Telegram connection."); } finally { setBusy(false); } }} className="mt-4 rounded-xl bg-[#ffcf4a] px-4 py-2 text-sm font-bold text-[#07152b]">{busy ? "Preparing…" : status.state === "awaiting_bot" ? "Create a new connection link" : "Create secure connection link"}</button>}
    {status?.install_url && <div className="mt-4"><p className="mb-3 text-sm text-slate-400">Open this private link while signed into the Telegram account that administers the intended group. Telegram will add the bot and send the one-time binding code automatically.</p><a href={status.install_url} target="_blank" rel="noreferrer" className="inline-flex rounded-xl bg-[#ffcf4a] px-4 py-2 text-sm font-bold text-[#07152b]">Add @{status.bot_username} to Telegram</a></div>}
    {status && !status.configured && <p className="mt-4 rounded-xl bg-white/[.04] p-3 text-sm text-slate-400">Ready for the official bot credentials. Comvoly will enable this control after BotFather registration and secure deployment configuration.</p>}
    {status?.configured && status.state !== "not_prepared" && <button onClick={() => void load()} className="mt-4 rounded-xl border border-white/15 px-4 py-2 text-sm">Check connection</button>}
    {status?.last_received_at && <p className="mt-3 text-xs text-slate-500">Last Telegram update: {formatDate(status.last_received_at)}</p>}
    {error && <p className="mt-3 text-sm text-rose-200">{error}</p>}
  </div>;
}

function WorkspaceIntelligencePanel({ detail, token }: { detail: WorkspaceDetail; token: string }) {
  const [question, setQuestion] = useState(""); const [answer, setAnswer] = useState<IntelligenceAnswer | null>(null);
  const [busy, setBusy] = useState(false); const [error, setError] = useState("");
  return <div className="rounded-3xl border border-[#ffcf4a]/25 bg-[#ffcf4a]/[.035] p-6"><Eyebrow>Interpret community knowledge</Eyebrow><h3 className="mt-2 text-xl font-semibold">Ask {detail.workspace.name}</h3><p className="mt-2 text-sm leading-6 text-slate-400">Pilot answers use only this workspace and always show their supporting community messages.</p>
    <form className="mt-5 flex flex-col gap-3 sm:flex-row" onSubmit={async (event) => { event.preventDefault(); setBusy(true); setError(""); setAnswer(null); try { setAnswer(await api<IntelligenceAnswer>(API_URL, token, `/v2/workspaces/${detail.workspace.id}/intelligence/ask`, { method: "POST", body: JSON.stringify({ question }) })); } catch (e) { setError(e instanceof Error ? e.message : "Comvoly could not answer that question."); } finally { setBusy(false); } }}><textarea required maxLength={1000} value={question} onChange={(e) => setQuestion(e.target.value)} placeholder="What has this community said about…?" className="min-h-24 flex-1 rounded-2xl border border-white/15 bg-[#061124] p-4 text-sm" /><button disabled={busy} className="rounded-2xl bg-[#ffcf4a] px-6 py-3 font-bold text-[#07152b]">{busy ? "Interpreting…" : "Ask Comvoly"}</button></form>
    {error && <p className="mt-4 text-sm text-rose-200">{error}</p>}
    {answer && <div className="mt-5 border-t border-white/10 pt-5"><p className="leading-7 text-slate-100">{answer.answer}</p><p className="mt-2 text-xs text-slate-500">Checked against {answer.evidence_count} authorised messages · extractive pilot</p><div className="mt-4 space-y-3">{answer.citations.map((item) => <article key={item.content_id} className="rounded-xl bg-[#061124] p-4"><div className="flex flex-wrap justify-between gap-2 text-xs text-slate-500"><span>{item.source_name} · {item.author}</span><span>Message {item.external_item_id}</span></div><p className="mt-2 text-sm leading-6 text-slate-300">{item.excerpt}</p></article>)}</div></div>}
  </div>;
}

function Metric({ label, value }: { label: string; value: number }) { return <div className="rounded-xl bg-white/[.04] p-3"><p className="text-lg font-semibold">{value.toLocaleString()}</p><p className="mt-1 text-xs text-slate-500">{label}</p></div>; }
function formatDate(value: string | null) { return value ? new Date(value).toLocaleDateString("en-GB") : "Unknown date"; }

function Invite({ workspaceId, token, setMessage, refresh }: { workspaceId: string; token: string; setMessage: (value: string) => void; refresh: () => Promise<void> }) {
  const [role, setRole] = useState("member"); const [email, setEmail] = useState(""); const [link, setLink] = useState("");
  return <div className="rounded-3xl border border-white/10 bg-white/[.035] p-6"><h3 className="text-lg font-semibold">Invite a member</h3><p className="mt-2 text-sm text-slate-400">The link expires after 72 hours and works with an existing or new Comvoly account.</p><form className="mt-5 grid gap-3 sm:grid-cols-[1fr_10rem_auto]" onSubmit={async (event) => { event.preventDefault(); try { const result = await api<{ token: string }>(API_URL, token, `/v2/workspaces/${workspaceId}/invitations`, { method: "POST", body: JSON.stringify({ role, email_hint: email || null }) }); const inviteLink = `${window.location.origin}/account?invite=${encodeURIComponent(result.token)}`; setLink(inviteLink); await refresh(); } catch (e) { setMessage(e instanceof Error ? e.message : "Could not create invitation."); } }}><input type="email" placeholder="Email (optional reminder)" value={email} onChange={(e) => setEmail(e.target.value)} className="rounded-xl border border-white/15 bg-[#061124] px-3 py-2 text-sm" /><select value={role} onChange={(e) => setRole(e.target.value)} className="rounded-xl border border-white/15 bg-[#061124] px-3 py-2 text-sm"><option value="member">Member</option><option value="moderator">Moderator</option><option value="administrator">Administrator</option></select><button className="rounded-xl bg-[#ffcf4a] px-4 py-2 text-sm font-bold text-[#07152b]">Create link</button></form>{link && <div className="mt-4 rounded-xl bg-[#061124] p-4"><p className="break-all text-xs text-slate-300">{link}</p><button onClick={async () => { await navigator.clipboard.writeText(link); setMessage("Invitation link copied."); }} className="mt-3 text-sm font-semibold text-[#ffcf4a]">Copy invitation link</button></div>}</div>;
}

function WorkspaceButton({ workspace, selected, onClick }: { workspace: WorkspaceSummary; selected: boolean; onClick: () => void }) { return <button onClick={onClick} className={`w-full rounded-2xl p-3 text-left ${selected ? "bg-white/10" : "hover:bg-white/[.05]"}`}><p className="font-medium">{workspace.name}</p><p className="mt-1 text-xs capitalize text-slate-500">{workspace.role}</p></button>; }
function EmptyState() { return <div className="rounded-3xl border border-white/10 bg-white/[.035] p-7"><h2 className="text-xl font-semibold">Your account is ready</h2><p className="mt-3 max-w-2xl leading-7 text-slate-400">Create a community workspace as an owner, or follow an invitation to join one. Registration alone never grants access to existing community knowledge.</p></div>; }
function Shell({ children, wide = false }: { children: React.ReactNode; wide?: boolean }) { return <main className="min-h-screen bg-[#07152d] px-4 py-8 text-white sm:px-8"><div className={`mx-auto ${wide ? "max-w-6xl" : "max-w-4xl"}`}><Link href="/" className="text-2xl font-black">COMVOLY<span className="text-[#ffcf4a]">.</span></Link><section className="mt-8 rounded-[2rem] border border-white/10 bg-[#091a36] p-5 shadow-2xl sm:p-9">{children}</section></div></main>; }
function Field({ label, value, setValue, type = "text", autoComplete }: { label: string; value: string; setValue: (value: string) => void; type?: string; autoComplete: string }) { return <label className="block text-sm text-slate-300">{label}<input required type={type} autoComplete={autoComplete} value={value} onChange={(e) => setValue(e.target.value)} className="mt-2 w-full rounded-xl border border-white/15 bg-[#061124] px-4 py-3 outline-none focus:border-[#ffcf4a]" /></label>; }
function Notice({ children }: { children: React.ReactNode }) { return <p className="mt-5 rounded-xl border border-amber-300/20 bg-amber-300/10 p-4 text-sm text-amber-100">{children}</p>; }
function Primary({ children }: { children: React.ReactNode }) { return <button className="w-full rounded-xl bg-[#ffcf4a] px-5 py-3 font-bold text-[#07152b]">{children}</button>; }
function Eyebrow({ children }: { children: React.ReactNode }) { return <p className="text-xs font-semibold uppercase tracking-[.18em] text-[#ffcf4a]">{children}</p>; }
