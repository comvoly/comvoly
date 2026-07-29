"use client";

import { useMemo, useState } from "react";

type Workspace = { id: string; name: string; role: string; accent: string; unread: number };
type View = "home" | "ask" | "catch-up" | "explore" | "manage";

const workspaces: Workspace[] = [
  { id: "ev", name: "EV Owners Network", role: "Owner", accent: "#ffcf4a", unread: 18 },
  { id: "growth", name: "Creator Growth Lab", role: "Member", accent: "#65d8c4", unread: 6 },
  { id: "fitness", name: "Everyday Strength", role: "Member", accent: "#9aa8ff", unread: 0 },
];

const setup = [
  ["Community details", "Tell members what this workspace covers", true],
  ["Connect a source", "Telegram, Discord or an approved import", true],
  ["Import history", "Bring existing community knowledge into Comvoly", false],
  ["Review knowledge", "Test answers and inspect their evidence", false],
  ["Invite members", "Open the workspace after your review", false],
] as const;

const members = [
  ["Stephen Hammond", "Owner", "Active", "SH"],
  ["Maya Patel", "Administrator", "Active", "MP"],
  ["Jordan Lee", "Member", "Invitation sent", "JL"],
] as const;

function Icon({ children }: { children: React.ReactNode }) {
  return <span aria-hidden className="grid h-9 w-9 place-items-center rounded-xl border border-white/8 bg-white/[0.04] text-sm">{children}</span>;
}

export default function WorkspacePreview() {
  const [workspaceId, setWorkspaceId] = useState("ev");
  const [view, setView] = useState<View>("home");
  const [switching, setSwitching] = useState(false);
  const workspace = useMemo(() => workspaces.find((item) => item.id === workspaceId)!, [workspaceId]);

  function chooseWorkspace(id: string) {
    setWorkspaceId(id);
    setSwitching(false);
    setView("home");
  }

  return (
    <main className="min-h-screen bg-[#061124] text-slate-100">
      <div className="fixed inset-0 bg-[radial-gradient(circle_at_80%_0%,rgba(46,111,218,.22),transparent_30%),radial-gradient(circle_at_0%_100%,rgba(255,207,74,.08),transparent_26%)]" />
      <div className="relative mx-auto flex min-h-screen max-w-[1500px]">
        <aside className="hidden w-64 shrink-0 border-r border-white/8 bg-[#07152b]/80 p-5 lg:flex lg:flex-col">
          <div className="flex items-center gap-3 px-2"><span className="grid h-10 w-10 place-items-center rounded-xl bg-[#ffcf4a] font-black text-[#07152b]">C</span><span className="text-lg font-semibold">Comvoly</span></div>
          <button onClick={() => setSwitching(!switching)} className="mt-8 flex w-full items-center gap-3 rounded-2xl border border-white/10 bg-white/[0.05] p-3 text-left hover:bg-white/[0.08]">
            <span className="grid h-9 w-9 place-items-center rounded-xl font-bold text-[#061124]" style={{ background: workspace.accent }}>{workspace.name.slice(0, 2).toUpperCase()}</span>
            <span className="min-w-0 flex-1"><strong className="block truncate text-sm">{workspace.name}</strong><span className="text-xs text-slate-400">{workspace.role}</span></span><span className="text-slate-500">⌄</span>
          </button>
          {switching && <div className="mt-2 rounded-2xl border border-white/10 bg-[#0b1a33] p-2 shadow-2xl">{workspaces.map((item) => <button key={item.id} onClick={() => chooseWorkspace(item.id)} className="flex w-full items-center gap-3 rounded-xl p-3 text-left hover:bg-white/[0.06]"><span className="h-3 w-3 rounded-full" style={{ background: item.accent }} /><span className="min-w-0 flex-1 truncate text-sm">{item.name}</span>{item.unread > 0 && <span className="rounded-full bg-[#ffcf4a] px-2 py-0.5 text-xs font-bold text-[#07152b]">{item.unread}</span>}</button>)}</div>}
          <nav className="mt-7 space-y-1">{([['home','Home','⌂'],['ask','Ask Comvoly','✦'],['catch-up','Catch up','↻'],['explore','Explore','◈'],['manage','Manage','⚙']] as [View,string,string][]).map(([id,label,glyph]) => <button key={id} onClick={() => setView(id)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm ${view === id ? "bg-white/10 text-white" : "text-slate-400 hover:bg-white/[0.05] hover:text-white"}`}><span className="w-5 text-center text-[#ffcf4a]">{glyph}</span>{label}</button>)}</nav>
          <div className="mt-auto rounded-2xl border border-white/8 bg-white/[0.035] p-4"><p className="text-xs text-slate-500">Signed in as</p><p className="mt-1 text-sm font-medium">Stephen Hammond</p><p className="mt-1 text-xs text-slate-400">3 communities linked</p></div>
        </aside>

        <section className="min-w-0 flex-1">
          <header className="sticky top-0 z-10 flex h-16 items-center justify-between border-b border-white/8 bg-[#061124]/90 px-5 backdrop-blur-xl sm:px-8">
            <button onClick={() => setSwitching(!switching)} className="flex min-w-0 items-center gap-3 lg:hidden"><span className="grid h-9 w-9 place-items-center rounded-xl font-bold text-[#061124]" style={{ background: workspace.accent }}>{workspace.name.slice(0, 2).toUpperCase()}</span><span className="truncate text-sm font-semibold">{workspace.name}</span><span>⌄</span></button>
            <div className="hidden lg:block"><p className="text-xs text-slate-500">Workspace</p><h1 className="font-semibold">{workspace.name}</h1></div>
            <div className="flex items-center gap-2"><span className="hidden rounded-full border border-emerald-300/15 bg-emerald-300/[0.08] px-3 py-1.5 text-xs text-emerald-200 sm:block">Private workspace</span><Icon>SH</Icon></div>
          </header>
          {switching && <div className="absolute left-4 right-4 top-16 z-20 rounded-2xl border border-white/10 bg-[#0b1a33] p-2 shadow-2xl lg:hidden">{workspaces.map((item) => <button key={item.id} onClick={() => chooseWorkspace(item.id)} className="flex w-full items-center gap-3 rounded-xl p-3 text-left hover:bg-white/[0.06]"><span className="h-3 w-3 rounded-full" style={{ background: item.accent }} /><span className="flex-1 text-sm">{item.name}</span><span className="text-xs text-slate-500">{item.role}</span></button>)}</div>}

          <div className="mx-auto max-w-6xl p-5 sm:p-8 lg:p-10">
            {view === "home" && <HomeView workspace={workspace} onManage={() => setView("manage")} />}
            {view === "ask" && <EmptyFeature eyebrow="Interpret community knowledge" title="Ask Comvoly" text="Ask a real question. Comvoly will interpret related discussions, distinguish consensus from disagreement and ground its answer in original evidence." action="Ask a question" />}
            {view === "catch-up" && <EmptyFeature eyebrow="Since your last visit" title="Catch up without catching up" text="See decisions, unresolved questions, recommendations and important resources—not an undifferentiated message summary." action="Generate catch-up" />}
            {view === "explore" && <EmptyFeature eyebrow="Community intelligence" title="Explore what this community knows" text="Browse recurring themes, trusted recommendations, debated topics, useful resources and decisions discovered across the community history." action="Explore knowledge" />}
            {view === "manage" && <ManageView />}
          </div>
          <nav className="fixed inset-x-0 bottom-0 z-20 grid grid-cols-5 border-t border-white/10 bg-[#07152b]/95 px-1 py-2 backdrop-blur lg:hidden">{([['home','Home','⌂'],['ask','Ask','✦'],['catch-up','Catch up','↻'],['explore','Explore','◈'],['manage','Manage','⚙']] as [View,string,string][]).map(([id,label,glyph]) => <button key={id} onClick={() => setView(id)} className={`flex flex-col items-center gap-1 text-[10px] ${view === id ? "text-[#ffcf4a]" : "text-slate-500"}`}><span className="text-lg">{glyph}</span>{label}</button>)}</nav>
        </section>
      </div>
    </main>
  );
}

function HomeView({ workspace, onManage }: { workspace: Workspace; onManage: () => void }) {
  return <><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#ffcf4a]">Good morning, Stephen</p><div className="mt-3 flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><h2 className="max-w-2xl text-3xl font-semibold tracking-tight sm:text-4xl">What does your community know?</h2><p className="mt-3 max-w-2xl leading-7 text-slate-400">Comvoly interprets conversations, experience and resources across {workspace.name}, then shows the evidence behind every insight.</p></div><button className="shrink-0 rounded-xl bg-[#ffcf4a] px-5 py-3 text-sm font-bold text-[#07152b]">Ask Comvoly</button></div>
  <div className="mt-8 grid gap-4 md:grid-cols-3"><Stat label="Knowledge imported" value="12,840 messages" note="3 years of community history" /><Stat label="Sources understood" value="426 resources" note="Links, files, images and discussions" /><Stat label="Since your last visit" value="4 decisions" note="Plus 7 recommendations" /></div>
  <section className="mt-6 rounded-3xl border border-white/9 bg-white/[0.035] p-5 sm:p-7"><div className="flex items-start justify-between gap-4"><div><p className="text-xs font-semibold uppercase tracking-wider text-[#ffcf4a]">Owner setup</p><h3 className="mt-2 text-xl font-semibold">Prepare your community</h3><p className="mt-2 text-sm text-slate-400">2 of 5 steps complete. Members cannot enter until you finish review.</p></div><span className="rounded-full bg-white/[0.06] px-3 py-1.5 text-xs">40%</span></div><div className="mt-5 h-1.5 overflow-hidden rounded-full bg-white/8"><div className="h-full w-2/5 rounded-full bg-[#ffcf4a]" /></div><div className="mt-5 grid gap-2">{setup.map(([title,note,done]) => <button key={title} onClick={onManage} className="flex items-center gap-4 rounded-2xl border border-white/7 bg-[#07152b]/70 p-4 text-left hover:border-white/15"><span className={`grid h-7 w-7 shrink-0 place-items-center rounded-full text-xs ${done ? "bg-emerald-300/15 text-emerald-200" : "border border-white/15 text-slate-500"}`}>{done ? "✓" : ""}</span><span className="min-w-0 flex-1"><strong className="block text-sm">{title}</strong><span className="mt-1 block text-xs text-slate-500">{note}</span></span><span className="text-slate-600">›</span></button>)}</div></section></>;
}

function ManageView() { return <><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#ffcf4a]">Owner controls</p><h2 className="mt-3 text-3xl font-semibold">Manage community</h2><p className="mt-3 text-slate-400">Connect knowledge sources, review access and control how this workspace operates.</p><div className="mt-8 grid gap-5 lg:grid-cols-[1.2fr_.8fr]"><section className="rounded-3xl border border-white/9 bg-white/[0.035] p-5 sm:p-7"><div className="flex items-center justify-between"><div><h3 className="text-lg font-semibold">Members</h3><p className="mt-1 text-sm text-slate-500">People who can access this workspace</p></div><button className="rounded-xl bg-[#ffcf4a] px-4 py-2.5 text-sm font-bold text-[#07152b]">Invite member</button></div><div className="mt-5 divide-y divide-white/7">{members.map(([name,role,state,initials]) => <div key={name} className="flex items-center gap-3 py-4"><span className="grid h-10 w-10 place-items-center rounded-full bg-white/8 text-xs font-semibold">{initials}</span><span className="min-w-0 flex-1"><strong className="block truncate text-sm">{name}</strong><span className="text-xs text-slate-500">{state}</span></span><span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300">{role}</span></div>)}</div></section><section className="rounded-3xl border border-white/9 bg-white/[0.035] p-5 sm:p-7"><h3 className="text-lg font-semibold">Connected sources</h3><div className="mt-5 rounded-2xl border border-white/8 bg-[#07152b]/80 p-4"><div className="flex items-center gap-3"><span className="grid h-10 w-10 place-items-center rounded-xl bg-sky-400/15 text-sky-300">↗</span><span className="flex-1"><strong className="block text-sm">Telegram</strong><span className="text-xs text-emerald-300">Connected</span></span></div><p className="mt-4 text-xs leading-5 text-slate-500">Ongoing messages are healthy. Historical import still needs owner review.</p></div><button className="mt-4 w-full rounded-xl border border-white/10 px-4 py-3 text-sm font-semibold hover:bg-white/5">Connect another source</button></section></div></> }

function Stat({ label, value, note }: { label: string; value: string; note: string }) { return <div className="rounded-2xl border border-white/9 bg-white/[0.035] p-5"><p className="text-xs text-slate-500">{label}</p><strong className="mt-3 block text-xl text-[#ffcf4a]">{value}</strong><p className="mt-2 text-xs text-slate-500">{note}</p></div> }
function EmptyFeature({ eyebrow, title, text, action }: { eyebrow: string; title: string; text: string; action: string }) { return <div className="grid min-h-[65vh] place-items-center"><div className="max-w-2xl text-center"><p className="text-xs font-semibold uppercase tracking-[.18em] text-[#ffcf4a]">{eyebrow}</p><h2 className="mt-4 text-4xl font-semibold tracking-tight sm:text-5xl">{title}</h2><p className="mx-auto mt-5 max-w-xl text-lg leading-8 text-slate-400">{text}</p><button className="mt-8 rounded-xl bg-[#ffcf4a] px-6 py-3.5 font-bold text-[#07152b]">{action}</button></div></div> }
