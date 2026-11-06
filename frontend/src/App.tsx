import { useCallback, useEffect, useMemo, useRef, useState, type FormEvent, type InputHTMLAttributes } from "react"
import { toast, Toaster } from "sonner"
import { getAuthToken, request, setAuthToken, type Application, type Company, type Stage, type Stats } from "./lib/api"
import "./App.css"

const stages: { key: Stage; label: string; color: string }[] = [
  { key: "applied", label: "Applied", color: "blue" },
  { key: "interview", label: "Interview", color: "violet" },
  { key: "offer", label: "Offer", color: "green" },
  { key: "rejected", label: "Rejected", color: "gray" },
]
const todayDate = new Date()
const today = todayDate.toISOString().slice(0, 10)
const todayLabel = todayDate.toLocaleDateString("en", { weekday: "long", month: "long", day: "numeric" })
const prettyDate = (value: string) => new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString("en", { month: "short", day: "numeric", year: "numeric" })
const initials = (name: string) => name.split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase()
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID ?? ""
const GOOGLE_SIGN_IN_CONFIGURED = Boolean(GOOGLE_CLIENT_ID && !GOOGLE_CLIENT_ID.toLowerCase().includes("your-client-id"))

function loadGoogleIdentity() {
  if (window.google?.accounts?.id) return Promise.resolve()
  return new Promise<void>((resolve, reject) => {
    let script = document.querySelector<HTMLScriptElement>('script[src="https://accounts.google.com/gsi/client"]')
    if (!script) {
      script = document.createElement("script")
      script.src = "https://accounts.google.com/gsi/client"
      script.async = true
      script.defer = true
      document.head.append(script)
    }
    script.addEventListener("load", () => resolve(), { once: true })
    script.addEventListener("error", () => reject(new Error("Could not load Google sign-in")), { once: true })
  })
}

function App() {
  const [applications, setApplications] = useState<Application[]>([])
  const [companies, setCompanies] = useState<Company[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [query, setQuery] = useState("")
  const [search, setSearch] = useState("")
  const [activeStages, setActiveStages] = useState<Stage[]>([])
  const [workMode, setWorkMode] = useState("")
  const [source, setSource] = useState("")
  const [followOnly, setFollowOnly] = useState(false)
  const [page, setPage] = useState<"board" | "companies" | "profile">("board")
  const [loading, setLoading] = useState(true)
  const [dialog, setDialog] = useState<"new" | "edit" | "company" | null>(null)
  const [editing, setEditing] = useState<Application | null>(null)
  const [selected, setSelected] = useState<Application | null>(null)
  const [dragId, setDragId] = useState<number | null>(null)
  const [dark, setDark] = useState(() => localStorage.getItem("joblee-theme") === "dark")
  const [authMode, setAuthMode] = useState<"checking" | "setup" | "login" | "authenticated">("checking")
  const [authEmail, setAuthEmail] = useState("")
  const [authError, setAuthError] = useState("")
  const [authBusy, setAuthBusy] = useState(false)
  const googleButtonRef = useRef<HTMLDivElement>(null)

  const filterParams = useMemo(() => {
    const p = new URLSearchParams()
    if (search) p.set("q", search)
    activeStages.forEach((stage) => p.append("status", stage))
    if (workMode) p.set("work_mode", workMode)
    if (source) p.set("source", source)
    return p.toString()
  }, [search, activeStages, workMode, source])

  const refresh = useCallback(async () => {
    setLoading(true)
    try {
      const boardParams = new URLSearchParams(filterParams)
      const statsParams = new URLSearchParams(filterParams)
      if (followOnly) boardParams.set("needs_follow_up", "true")
      if (followOnly) statsParams.set("needs_follow_up", "true")
      const [apps, statData, companyData] = await Promise.all([
        request<Application[]>(`/applications${boardParams.size ? `?${boardParams}` : ""}`),
        request<Stats>(`/stats${statsParams.size ? `?${statsParams}` : ""}`),
        request<Company[]>("/companies"),
      ])
      setApplications(apps)
      setStats(statData)
      setCompanies(companyData)
    } catch (error) {
      toast.error(error instanceof Error ? error.message : "Could not connect to the API")
    } finally { setLoading(false) }
  }, [filterParams, followOnly])

  async function signInWithGoogle(credential: string) {
    setAuthBusy(true); setAuthError("")
    try {
      const result = await request<{ access_token: string; user: { email: string } }>("/auth/google", {
        method: "POST", body: JSON.stringify({ credential }),
      })
      setAuthToken(result.access_token); setAuthEmail(result.user.email); setAuthMode("authenticated")
    } catch (error) { setAuthError(error instanceof Error ? error.message : "Could not sign in") }
    finally { setAuthBusy(false) }
  }

  useEffect(() => { const timer = window.setTimeout(() => setSearch(query.trim()), 300); return () => window.clearTimeout(timer) }, [query])
  useEffect(() => {
    let active = true
    void request<{ setup_required: boolean }>("/auth/status").then(async ({ setup_required }) => {
      if (!active) return
      if (setup_required) { setAuthMode("setup"); return }
      if (!getAuthToken()) { setAuthMode("login"); return }
      try {
        const user = await request<{ email: string }>("/auth/me")
        if (active) { setAuthEmail(user.email); setAuthMode("authenticated") }
      }
      catch { setAuthToken(null); if (active) setAuthMode("login") }
    }).catch((error) => { if (active) { setAuthError(error instanceof Error ? error.message : "Could not connect to the API"); setAuthMode("login") } })
    return () => { active = false }
  }, [])
  useEffect(() => {
    if ((authMode !== "setup" && authMode !== "login") || !GOOGLE_SIGN_IN_CONFIGURED || !googleButtonRef.current) return
    void loadGoogleIdentity().then(() => {
      if (!googleButtonRef.current || !window.google?.accounts?.id) return
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: ({ credential }) => { void signInWithGoogle(credential) },
      })
      googleButtonRef.current.replaceChildren()
      window.google.accounts.id.renderButton(googleButtonRef.current, { theme: dark ? "filled_black" : "outline", size: "large", shape: "pill", text: "continue_with", width: 320 })
    }).catch((error) => setAuthError(error instanceof Error ? error.message : "Could not load Google sign-in"))
  }, [authMode, dark])
  useEffect(() => { if (authMode !== "authenticated") return; const timer = window.setTimeout(() => void refresh(), 0); return () => window.clearTimeout(timer) }, [refresh, authMode])
  useEffect(() => { document.documentElement.classList.toggle("dark", dark); localStorage.setItem("joblee-theme", dark ? "dark" : "light") }, [dark])

  async function move(id: number, status: Stage) {
    const original = applications
    setApplications((items) => items.map((item) => item.id === id ? { ...item, status, needs_follow_up: false } : item))
    try {
      await request(`/applications/${id}/status`, { method: "PATCH", body: JSON.stringify({ status }) })
      const detail = await request<Application>(`/applications/${id}`)
      setSelected((current) => current?.id === id ? detail : current)
      await refresh()
    }
    catch (error) { setApplications(original); toast.error(error instanceof Error ? error.message : "Could not move application") }
  }

  async function saveApplication(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    const companyChoice = String(form.get("company"))
    const companyId = Number(companyChoice)
    const payload: Record<string, unknown> = {
      job_title: String(form.get("job_title")).trim(), status: String(form.get("status")),
      applied_date: String(form.get("applied_date")), job_url: String(form.get("job_url") || "") || null,
      location: String(form.get("location") || "") || null, work_mode: String(form.get("work_mode") || "") || null,
      source: String(form.get("source") || "") || null,
      salary_min: form.get("salary_min") ? Number(form.get("salary_min")) : null,
      salary_max: form.get("salary_max") ? Number(form.get("salary_max")) : null,
    }
    if (companyChoice === "new") payload.company = { name: String(form.get("company_new")).trim() }
    else payload.company_id = companyId
    try {
      if (dialog === "edit" && editing) {
        delete payload.company
        await request(`/applications/${editing.id}`, { method: "PATCH", body: JSON.stringify(payload) })
      } else await request("/applications", { method: "POST", body: JSON.stringify(payload) })
      toast.success(dialog === "edit" ? "Application updated" : "Application added")
      setDialog(null); setEditing(null); await refresh()
    } catch (error) { toast.error(error instanceof Error ? error.message : "Could not save application") }
  }

  async function removeApplication(app: Application) {
    if (!window.confirm(`Delete ${app.job_title} at ${app.company_name}?`)) return
    try { await request(`/applications/${app.id}`, { method: "DELETE" }); setSelected(null); toast.success("Application deleted"); await refresh() }
    catch (error) { toast.error(error instanceof Error ? error.message : "Could not delete application") }
  }

  async function addNote(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!selected) return
    const form = new FormData(event.currentTarget)
    try { await request(`/applications/${selected.id}/notes`, { method: "POST", body: JSON.stringify({ content: form.get("content") }) }); toast.success("Note added"); await refresh(); setSelected(await request<Application>(`/applications/${selected.id}`)) }
    catch (error) { toast.error(error instanceof Error ? error.message : "Could not add note") }
  }

  async function followUp(id: number, action: "done" | "snooze" | "reject") {
    try {
      if (action === "done") await request(`/follow-ups/${id}/done`, { method: "POST" })
      if (action === "snooze") await request(`/follow-ups/${id}/snooze`, { method: "POST", body: JSON.stringify({ days: 3 }) })
      if (action === "reject") await request(`/applications/${id}/status`, { method: "PATCH", body: JSON.stringify({ status: "rejected" }) })
      toast.success(action === "done" ? "Follow-up logged" : action === "snooze" ? "Reminder snoozed for 3 days" : "Moved to rejected")
      await refresh()
    } catch (error) { toast.error(error instanceof Error ? error.message : "Could not update reminder") }
  }

  async function saveCompany(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const form = new FormData(event.currentTarget)
    try {
      await request("/companies", { method: "POST", body: JSON.stringify({ name: form.get("name"), website: form.get("website") || null, location: form.get("location") || null, industry: form.get("industry") || null }) })
      toast.success("Company added"); setDialog(null); await refresh()
    } catch (error) { toast.error(error instanceof Error ? error.message : "Could not save company") }
  }

  async function editCompany(company: Company) {
    const name = window.prompt("Company name", company.name)?.trim()
    if (!name || name === company.name) return
    try { await request(`/companies/${company.id}`, { method: "PATCH", body: JSON.stringify({ name }) }); toast.success("Company updated"); await refresh() }
    catch (error) { toast.error(error instanceof Error ? error.message : "Could not update company") }
  }

  async function deleteCompany(company: Company) {
    if (!window.confirm(`Delete ${company.name}?`)) return
    try { await request(`/companies/${company.id}`, { method: "DELETE" }); toast.success("Company deleted"); await refresh() }
    catch (error) { toast.error(error instanceof Error ? error.message : "Could not delete company") }
  }

  async function updateNote(noteId: number, current: string) {
    const content = window.prompt("Edit note", current)?.trim()
    if (!content || content === current || !selected) return
    try { await request(`/notes/${noteId}`, { method: "PATCH", body: JSON.stringify({ content }) }); await refresh(); setSelected(await request<Application>(`/applications/${selected.id}`)); toast.success("Note updated") }
    catch (error) { toast.error(error instanceof Error ? error.message : "Could not update note") }
  }

  async function deleteNote(noteId: number) {
    if (!selected || !window.confirm("Delete this note?")) return
    try { await request(`/notes/${noteId}`, { method: "DELETE" }); await refresh(); setSelected(await request<Application>(`/applications/${selected.id}`)); toast.success("Note deleted") }
    catch (error) { toast.error(error instanceof Error ? error.message : "Could not delete note") }
  }

  async function logout() {
    try { await request("/auth/logout", { method: "POST" }) } catch { /* Clear the local session even if it expired. */ }
    setAuthToken(null); setApplications([]); setCompanies([]); setStats(null); setAuthMode("login")
  }

  if (authMode !== "authenticated") return <>
    <Toaster position="top-right" richColors />
    <div className="auth-screen"><div className="auth-card">
      <div className="brand-mark">J</div>
      <p className="eyebrow">JOBLEE · PRIVATE TRACKER</p>
      <h1>{authMode === "checking" ? "Connecting…" : authMode === "setup" ? "Get started with Google" : "Sign in to Joblee"}</h1>
      <p className="auth-copy">Use your Google account to securely access your job search tracker.</p>
      {authMode !== "checking" && <>
        {!GOOGLE_SIGN_IN_CONFIGURED ? <p className="auth-error" role="alert">Add a valid Google OAuth Web client ID to root .env and frontend/.env.local. Replace the sample client ID, then restart the app.</p> : <div className={`google-button-wrap${authBusy ? " is-busy" : ""}`} ref={googleButtonRef} />}
        {authBusy && <p className="auth-copy auth-wait">Signing in…</p>}
        {authError && <p className="auth-error" role="alert">{authError}</p>}
      </>}
    </div></div>
  </>

  const activeFilters = Boolean(search || activeStages.length || workMode || source || followOnly)
  const followUps = applications.filter((item) => item.needs_follow_up)

  return <div className="app-shell">
    <Toaster position="top-right" richColors />
    <header className="topbar"><a className="brand" href="#board" onClick={() => setPage("board")}><span className="brand-mark">j.</span><span>joblee</span></a>
      <nav className="main-nav"><button className={page === "board" ? "nav-link active" : "nav-link"} onClick={() => setPage("board")}>Board</button><button className={page === "companies" ? "nav-link active" : "nav-link"} onClick={() => setPage("companies")}>Companies</button><button className={page === "profile" ? "nav-link active" : "nav-link"} onClick={() => setPage("profile")}>Profile</button></nav>
      <div className="top-actions"><button className="icon-button" title="Toggle color theme" onClick={() => setDark((value) => !value)}>{dark ? "☀" : "◐"}</button><button className="text-action" onClick={() => void logout()} title={`Sign out ${authEmail}`}>Sign out</button><button className="primary-button" onClick={() => { setEditing(null); setDialog("new") }}><span>＋</span> Add application</button></div>
    </header>

    <main className="main-content">
      {page === "board" ? <>
        <section className="page-heading"><div><div className="eyebrow">YOUR CAREER, IN MOTION</div><h1>Application board</h1><p>Keep every opportunity moving forward.</p></div><div className="heading-date"><span className="date-dot" /> {todayLabel}</div></section>
        <section className="stats-grid">
          {[{ label: "Total applications", value: stats?.total ?? "—", icon: "▤", tone: "ink" }, { label: "In interview", value: stats?.interviews ?? "—", icon: "◎", tone: "purple" }, { label: "Offers received", value: stats?.offers ?? "—", icon: "✦", tone: "mint" }, { label: "Rejected", value: stats?.rejected ?? "—", icon: "↘", tone: "ink" }, { label: "Response rate", value: stats ? `${Math.round(stats.response_rate * 100)}%` : "—", icon: "↗", tone: "blue" }, { label: "Follow-ups due", value: stats?.follow_ups_due ?? "—", icon: "◷", tone: "purple" }].map((stat) => <article className="stat-card" key={stat.label}><span className={`stat-icon ${stat.tone}`}>{stat.icon}</span><div><div className="stat-value">{stat.value}</div><div className="stat-label">{stat.label}</div></div><span className="stat-spark">⌁</span></article>)}
        </section>
        {followUps.length > 0 && <section className="reminder-panel"><div className="reminder-title"><span className="reminder-icon">↗</span><div><strong>Follow up today</strong><p>{followUps.length} {followUps.length === 1 ? "application has" : "applications have"} been waiting for a response</p></div></div><div className="reminder-list">{followUps.slice(0, 3).map((item) => <div className="reminder-row" key={item.id}><span className="company-avatar small">{initials(item.company_name)}</span><div className="reminder-job"><strong>{item.job_title}</strong><span>{item.company_name} · quiet since {prettyDate(item.last_activity_at)}</span></div><button className="text-action" onClick={() => void followUp(item.id, "done")}>Mark done</button><button className="subtle-action" onClick={() => void followUp(item.id, "snooze")}>Snooze</button><button className="subtle-action" onClick={() => void followUp(item.id, "reject")}>Reject</button></div>)}</div></section>}
        <section className="board-section"><div className="board-toolbar"><div><h2>Pipeline <span className="count-pill">{applications.length}</span></h2><p>Your opportunities, all in one place</p></div><div className="filters"><label className="search-box"><span>⌕</span><input aria-label="Search applications" placeholder="Search roles, companies…" value={query} onChange={(event) => setQuery(event.target.value)} /><kbd>⌘ K</kbd></label><select aria-label="Filter work mode" value={workMode} onChange={(event) => setWorkMode(event.target.value)}><option value="">All work modes</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">On-site</option></select><select aria-label="Filter source" value={source} onChange={(event) => setSource(event.target.value)}><option value="">All sources</option><option>LinkedIn</option><option>Referral</option><option>Company site</option><option>Other</option></select><label className="follow-toggle"><input type="checkbox" checked={followOnly} onChange={(event) => setFollowOnly(event.target.checked)} /> Follow-ups</label>{activeFilters && <button className="clear-button" onClick={() => { setQuery(""); setSearch(""); setActiveStages([]); setWorkMode(""); setSource(""); setFollowOnly(false) }}>Clear</button>}</div></div>
          <div className="stage-filters">{stages.map((stage) => <button key={stage.key} className={`stage-chip ${activeStages.includes(stage.key) ? `selected ${stage.color}` : ""}`} onClick={() => setActiveStages((current) => current.includes(stage.key) ? current.filter((item) => item !== stage.key) : [...current, stage.key])}><span className={`stage-dot ${stage.color}`} />{stage.label}</button>)}</div>
          <div className="kanban-board">{stages.map((stage) => {
            const items = applications.filter((item) => item.status === stage.key)
            return <section key={stage.key} className={`kanban-column ${stage.color}`} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); if (dragId !== null) void move(dragId, stage.key); setDragId(null) }}>
              <header className="column-header"><div className="column-title"><span className={`stage-dot ${stage.color}`} /><h3>{stage.label}</h3><span className="column-count">{items.length}</span></div><button aria-label={`Add ${stage.label.toLowerCase()} application`} className="column-add" onClick={() => { setEditing(null); setDialog("new") }}>＋</button></header>
              <div className="card-stack">{loading && applications.length === 0 ? <div className="loading-card">Loading…</div> : items.length === 0 ? <div className="empty-column"><span>✳</span><strong>Nothing here yet</strong><small>Drag a card here or add an application</small></div> : items.map((item) => <article key={item.id} draggable onDragStart={() => setDragId(item.id)} onDragEnd={() => setDragId(null)} className={`job-card ${dragId === item.id ? "dragging" : ""}`} onClick={() => { setSelected(item); void request<Application>(`/applications/${item.id}`).then(setSelected).catch(() => {}) }}><div className="card-topline"><span className="company-avatar">{initials(item.company_name)}</span><button className="more-button" aria-label="Edit application" onClick={(event) => { event.stopPropagation(); setEditing(item); setDialog("edit") }}>•••</button></div><div className="job-card-title">{item.job_title}</div><div className="company-name">{item.company_name}</div><div className="card-meta"><span>⌖ {item.location || "Location flexible"}</span><span>◷ {prettyDate(item.applied_date)}</span></div><div className="card-footer"><span className="work-tag">{item.work_mode || "Not specified"}</span>{item.needs_follow_up && <span className="follow-badge">Follow up</span>}<span className="note-count">▤ {item.note_count}</span><select aria-label={`Move ${item.job_title}`} value="" onClick={(event) => event.stopPropagation()} onChange={(event) => { if (event.target.value) void move(item.id, event.target.value as Stage) }}><option value="">Move</option>{stages.filter((choice) => choice.key !== item.status).map((choice) => <option key={choice.key} value={choice.key}>{choice.label}</option>)}</select></div></article>)}</div>
              <button className="add-card-button" onClick={() => { setEditing(null); setDialog("new") }}>＋ Add application</button>
            </section>
          })}</div>
        </section>
      </> : page === "companies" ? <section className="companies-page"><div className="page-heading"><div><div className="eyebrow">YOUR NETWORK</div><h1>Companies</h1><p>Manage the teams behind your opportunities.</p></div><button className="primary-button" onClick={() => setDialog("company")}>＋ Add company</button></div><div className="company-grid">{companies.map((company) => <article key={company.id} className="company-card"><span className="company-avatar">{initials(company.name)}</span><div><h3>{company.name}</h3><p>{company.industry || "Company"}{company.location ? ` · ${company.location}` : ""}</p></div><span className="company-app-count">{company.application_count} {company.application_count === 1 ? "application" : "applications"}</span><button className="more-button" aria-label={`Edit ${company.name}`} onClick={() => void editCompany(company)}>•••</button><button className="company-delete" disabled={company.application_count > 0} title={company.application_count ? "Remove its applications first" : "Delete company"} onClick={() => void deleteCompany(company)}>×</button></article>)}</div></section> : <section className="profile-page"><div className="page-heading"><div><div className="eyebrow">YOUR ACCOUNT</div><h1>Profile</h1><p>Manage your Joblee account and sign-in details.</p></div></div><article className="profile-card"><div className="profile-avatar">{authEmail.slice(0, 1).toUpperCase() || "G"}</div><div className="profile-details"><span className="eyebrow">GOOGLE ACCOUNT</span><h2>{authEmail || "Signed-in Google account"}</h2><p>Your Google account is connected to Joblee.</p></div><span className="profile-status"><span /> Connected</span></article><article className="profile-security"><div><h2>Account security</h2><p>Your tracker is protected by your Google sign-in. Signing out ends this session on this device.</p></div><button className="secondary-button" onClick={() => void logout()}>Sign out</button></article></section>}
        </main>

    {dialog && <div className="modal-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) { setDialog(null); setEditing(null) } }}><section className="modal"><div className="modal-heading"><div><div className="eyebrow">{dialog === "edit" ? "UPDATE DETAILS" : dialog === "company" ? "YOUR NETWORK" : "NEW OPPORTUNITY"}</div><h2>{dialog === "edit" ? "Edit application" : dialog === "company" ? "Add a company" : "Add application"}</h2></div><button className="icon-button" aria-label="Close" onClick={() => { setDialog(null); setEditing(null) }}>×</button></div>{dialog === "company" ? <form onSubmit={(event) => void saveCompany(event)} className="form-grid"><Field label="Company name" name="name" required placeholder="e.g. Linear" /><Field label="Website" name="website" placeholder="https://example.com" /><Field label="Location" name="location" placeholder="City, country" /><Field label="Industry" name="industry" placeholder="Technology" /><div className="modal-actions"><button type="button" className="secondary-button" onClick={() => setDialog(null)}>Cancel</button><button className="primary-button">Save company</button></div></form> : <form onSubmit={(event) => void saveApplication(event)} className="form-grid"><label className="form-field"><span>Company</span><select name="company" defaultValue={editing ? String(editing.company_id) : "new"} required>{!editing && <option value="new">＋ Create new company</option>}{companies.map((company) => <option value={company.id} key={company.id}>{company.name}</option>)}</select></label>{!editing && <Field label="New company name" name="company_new" required placeholder="e.g. Linear" />}<Field label="Job title" name="job_title" defaultValue={editing?.job_title} required maxLength={120} placeholder="Senior Product Designer" /><label className="form-field"><span>Stage</span><select name="status" defaultValue={editing?.status || "applied"}>{stages.map((stage) => <option key={stage.key} value={stage.key}>{stage.label}</option>)}</select></label><Field label="Applied date" name="applied_date" type="date" defaultValue={editing?.applied_date || today} required max={today} /><Field label="Job URL" name="job_url" type="url" defaultValue={editing?.job_url || ""} placeholder="https://…" /><Field label="Location" name="location" defaultValue={editing?.location || ""} placeholder="Remote, New York…" /><label className="form-field"><span>Work mode</span><select name="work_mode" defaultValue={editing?.work_mode || ""}><option value="">Choose mode</option><option value="remote">Remote</option><option value="hybrid">Hybrid</option><option value="onsite">On-site</option></select></label><label className="form-field"><span>Source</span><select name="source" defaultValue={editing?.source || ""}><option value="">Choose source</option><option>LinkedIn</option><option>Referral</option><option>Company site</option><option>Other</option></select></label><Field label="Salary min" name="salary_min" type="number" min="0" defaultValue={editing?.salary_min ?? ""} placeholder="Optional" /><Field label="Salary max" name="salary_max" type="number" min="0" defaultValue={editing?.salary_max ?? ""} placeholder="Optional" /><div className="modal-actions"><button type="button" className="secondary-button" onClick={() => { setDialog(null); setEditing(null) }}>Cancel</button><button className="primary-button">{editing ? "Save changes" : "Add application"}</button></div></form>}</section></div>}

    {selected && <div className="drawer-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setSelected(null) }}><aside className="detail-drawer"><div className="drawer-top"><span className="eyebrow">APPLICATION DETAILS</span><button className="icon-button" onClick={() => setSelected(null)}>×</button></div><span className="company-avatar large">{initials(selected.company_name)}</span><h2>{selected.job_title}</h2><p className="drawer-company">{selected.company_name}{selected.company_industry ? ` · ${selected.company_industry}` : ""}</p><label className="form-field drawer-stage"><span>Current stage</span><select value={selected.status} onChange={(event) => void move(selected.id, event.target.value as Stage)}>{stages.map((stage) => <option key={stage.key} value={stage.key}>{stage.label}</option>)}</select></label><div className="detail-grid"><div><small>Applied</small><strong>{prettyDate(selected.applied_date)}</strong></div><div><small>Work mode</small><strong>{selected.work_mode || "Not specified"}</strong></div><div><small>Location</small><strong>{selected.location || "Flexible"}</strong></div><div><small>Source</small><strong>{selected.source || "Not specified"}</strong></div></div>{selected.job_url && <a className="job-link" href={selected.job_url} target="_blank" rel="noreferrer">Open job listing ↗</a>}<div className="drawer-section"><div className="section-heading"><h3>Notes</h3><span>{selected.notes?.length || 0}</span></div><form className="note-form" onSubmit={(event) => void addNote(event)}><textarea name="content" required maxLength={2000} placeholder="Add a note about this opportunity…" /><button className="primary-button">Add note</button></form><div className="notes-list">{selected.notes?.map((note) => <article key={note.id} className="note-item"><p>{note.content}</p><small>{new Date(note.created_at).toLocaleString()}</small><div className="note-actions"><button onClick={() => void updateNote(note.id, note.content)}>Edit</button><button onClick={() => void deleteNote(note.id)}>Delete</button></div></article>)}</div></div><div className="drawer-section"><div className="section-heading"><h3>Status history</h3></div>{selected.history?.map((entry) => <div className="history-row" key={entry.id}><span className={`stage-dot ${entry.to_status}`} /><span>{entry.from_status ? `${entry.from_status} → ` : "Created as "}{entry.to_status}</span><small>{prettyDate(entry.changed_at)}</small></div>)}</div><button className="danger-button" onClick={() => void removeApplication(selected)}>Delete application</button></aside></div>}
  </div>
}

function Field({ label, name, ...props }: { label: string; name: string } & InputHTMLAttributes<HTMLInputElement>) {
  return <label className="form-field"><span>{label}</span><input name={name} {...props} /></label>
}

export default App
