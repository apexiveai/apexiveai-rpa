'use client';

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Activity, ArrowDown, ArrowUp, Bot, Check, ChevronDown, CirclePlus, Clock3,
  Code2, Copy, ExternalLink, FilePlus2, FolderKanban, Globe2, ListChecks,
  MousePointer2, Play, Plus, Save, Search, Settings2, Square, Terminal, Trash2,
  Workflow, X,
} from "lucide-react";

const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8111/api";

type Project = { id: number; name: string; description?: string; status: string; version: string };
type Step = Record<string, string | number | boolean | string[] | undefined> & { action: string };
type WorkflowItem = {
  id: number;
  project_id: number;
  name: string;
  interval_seconds: number | null;
  definition: { steps?: Step[] };
  enabled: boolean;
};
type Run = { id: number; workflow_id: number; status: string; error?: string | null; output: Record<string, unknown> };
type RobotStatus = { online: boolean; workers: number };

const ACTIONS = [
  { key: "browser_launch", label: "Launch Chrome / Edge", group: "BROWSER", icon: Globe2 },
  { key: "browser_navigate", label: "Open website", group: "BROWSER", icon: ExternalLink },
  { key: "browser_click", label: "Click web element", group: "BROWSER", icon: MousePointer2 },
  { key: "browser_fill", label: "Fill web field", group: "BROWSER", icon: Code2 },
  { key: "browser_press", label: "Press browser key", group: "BROWSER", icon: Square },
  { key: "browser_select", label: "Select dropdown option", group: "BROWSER", icon: ListChecks },
  { key: "browser_wait", label: "Wait for web element", group: "BROWSER", icon: Clock3 },
  { key: "browser_get_text", label: "Read web text", group: "BROWSER", icon: Code2 },
  { key: "browser_assert_text", label: "Assert web text", group: "BROWSER", icon: Check },
  { key: "browser_close", label: "Close browser", group: "BROWSER", icon: X },
  { key: "launch_app", label: "Launch Windows app", group: "WINDOWS", icon: Bot },
  { key: "wait_for_window", label: "Wait for window", group: "WINDOWS", icon: Clock3 },
  { key: "click", label: "Click UI element", group: "WINDOWS", icon: MousePointer2 },
  { key: "type_text", label: "Type text", group: "WINDOWS", icon: Code2 },
  { key: "press_key", label: "Press key", group: "WINDOWS", icon: Square },
  { key: "close_window", label: "Close window", group: "WINDOWS", icon: X },
  { key: "set_variable", label: "Set variable", group: "FLOW", icon: Settings2 },
  { key: "delay", label: "Wait", group: "FLOW", icon: Clock3 },
  { key: "log", label: "Log message", group: "FLOW", icon: Terminal },
] as const;

function newStep(action: string): Step {
  switch (action) {
    case "browser_launch": return { action, browser: "chrome", headless: false };
    case "browser_navigate": return { action, url: "", wait_until: "domcontentloaded", timeout: 30000 };
    case "browser_click": return { action, selector: "", timeout: 15000 };
    case "browser_fill": return { action, selector: "", text: "", timeout: 15000 };
    case "browser_press": return { action, selector: "", key: "Enter", timeout: 15000 };
    case "browser_select": return { action, selector: "", value: "", timeout: 15000 };
    case "browser_wait": return { action, selector: "", state: "visible", timeout: 15000 };
    case "browser_get_text": return { action, selector: "", name: "", timeout: 15000 };
    case "browser_assert_text": return { action, selector: "", text: "", exact: false, timeout: 15000 };
    case "browser_close": return { action };
    case "launch_app": return { action, executable: "", arguments: [] };
    case "wait_for_window": return { action, title: "", timeout: 30 };
    case "click": return { action, title: "", auto_id: "", control_type: "Button" };
    case "type_text": return { action, text: "", title: "", auto_id: "" };
    case "press_key": return { action, key: "{ENTER}" };
    case "set_variable": return { action, name: "value", value: "" };
    case "delay": return { action, seconds: 1 };
    case "log": return { action, message: "Workflow step completed" };
    default: return { action };
  }
}

const ACTION_GROUPS = ["BROWSER", "WINDOWS", "FLOW"] as const;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail || response.statusText}`);
  }
  return response.json() as Promise<T>;
}

function actionLabel(action: string) {
  return ACTIONS.find((item) => item.key === action)?.label ?? action;
}

export default function Home() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [workflows, setWorkflows] = useState<WorkflowItem[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [robotStatus, setRobotStatus] = useState<RobotStatus>({ online: false, workers: 0 });
  const [projectId, setProjectId] = useState<number | null>(null);
  const [workflowId, setWorkflowId] = useState<number | null>(null);
  const [workflowName, setWorkflowName] = useState("");
  const [steps, setSteps] = useState<Step[]>([]);
  const [projectName, setProjectName] = useState("");
  const [showProjectForm, setShowProjectForm] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const activeWorkflow = useMemo(
    () => workflows.find((workflow) => workflow.id === workflowId) ?? null,
    [workflows, workflowId],
  );

  const loadProjectsAndRuns = useCallback(async () => {
    const [projectList, runList, currentRobotStatus] = await Promise.all([
      request<Project[]>("/rpa/projects"),
      request<Run[]>("/rpa/runs"),
      request<RobotStatus>("/rpa/robot/status"),
    ]);
    setProjects(projectList);
    setRuns(runList);
    setRobotStatus(currentRobotStatus);
    setProjectId((current) => current ?? projectList[0]?.id ?? null);
  }, []);

  const loadWorkflows = useCallback(async (selectedProjectId: number) => {
    const list = await request<WorkflowItem[]>(`/rpa/projects/${selectedProjectId}/workflows`);
    setWorkflows(list);
    setWorkflowId((current) => list.some((workflow) => workflow.id === current) ? current : list[0]?.id ?? null);
    return list;
  }, []);

  useEffect(() => {
    loadProjectsAndRuns().catch((cause: unknown) => {
      setError(cause instanceof Error ? cause.message : "Unable to connect to the RPA API");
    });
    const timer = window.setInterval(() => {
      Promise.all([request<Run[]>("/rpa/runs"), request<RobotStatus>("/rpa/robot/status")])
        .then(([runList, currentRobotStatus]) => {
          setRuns(runList);
          setRobotStatus(currentRobotStatus);
        }).catch((cause: unknown) => {
        setError(cause instanceof Error ? cause.message : "Unable to refresh execution runs");
      });
    }, 5000);
    return () => window.clearInterval(timer);
  }, [loadProjectsAndRuns]);

  useEffect(() => {
    if (projectId === null) {
      setWorkflows([]);
      setWorkflowId(null);
      return;
    }
    loadWorkflows(projectId).catch((cause: unknown) => {
      setError(cause instanceof Error ? cause.message : "Unable to load workflows");
    });
  }, [projectId, loadWorkflows]);

  useEffect(() => {
    if (!activeWorkflow) {
      setWorkflowName("");
      setSteps([]);
      return;
    }
    setWorkflowName(activeWorkflow.name);
    setSteps(activeWorkflow.definition?.steps ?? []);
  }, [activeWorkflow]);

  async function createProject() {
    if (projectName.trim().length < 2) {
      setError("Project name must be at least two characters.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const project = await request<Project>("/rpa/projects", {
        method: "POST",
        body: JSON.stringify({ name: projectName.trim(), description: "Created in Apexive Studio" }),
      });
      setProjectName("");
      setShowProjectForm(false);
      await loadProjectsAndRuns();
      setProjectId(project.id);
      setNotice(`Project "${project.name}" created.`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Project could not be created");
    } finally {
      setLoading(false);
    }
  }

  async function createWorkflow() {
    if (projectId === null) {
      setError("Create or select a project first.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const workflow = await request<WorkflowItem>("/rpa/workflows", {
        method: "POST",
        body: JSON.stringify({
          project_id: projectId,
          name: `New workflow ${workflows.length + 1}`,
          definition: { steps: [] },
        }),
      });
      const list = await loadWorkflows(projectId);
      setWorkflowId(workflow.id);
      setNotice(`Workflow "${workflow.name}" created.`);
      if (!list.some((item) => item.id === workflow.id)) {
        setWorkflows([...list, workflow]);
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Workflow could not be created");
    } finally {
      setLoading(false);
    }
  }

  async function saveWorkflow(): Promise<boolean> {
    if (!activeWorkflow) return false;
    setSaving(true);
    setError("");
    try {
      const saved = await request<WorkflowItem>(`/rpa/workflows/${activeWorkflow.id}`, {
        method: "PUT",
        body: JSON.stringify({
          name: workflowName.trim(),
          interval_seconds: activeWorkflow.interval_seconds,
          definition: { steps },
        }),
      });
      setWorkflows((current) => current.map((workflow) => workflow.id === saved.id ? saved : workflow));
      setNotice("Workflow saved.");
      return true;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Workflow could not be saved");
      return false;
    } finally {
      setSaving(false);
    }
  }

  async function runWorkflow() {
    if (!activeWorkflow) return;
    setError("");
    try {
      if (!await saveWorkflow()) return;
      const run = await request<Run>(`/rpa/workflows/${activeWorkflow.id}/run`, { method: "POST" });
      setNotice(`Run #${run.id} queued. A connected Windows Robot will pick it up.`);
      setRuns((current) => [run, ...current]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Workflow could not be queued");
    }
  }

  function updateStep(index: number, key: string, value: string | number | boolean | string[]) {
    setSteps((current) => current.map((step, i) => i === index ? { ...step, [key]: value } : step));
  }

  function moveStep(index: number, offset: number) {
    const target = index + offset;
    if (target < 0 || target >= steps.length) return;
    setSteps((current) => {
      const result = [...current];
      [result[index], result[target]] = [result[target], result[index]];
      return result;
    });
  }

  function addStep(action: string) {
    setSteps((current) => [...current, newStep(action)]);
  }

  const workflowRuns = runs.filter((run) => run.workflow_id === workflowId).slice(0, 5);

  return (
    <main className="studio-shell">
      <header className="studio-topbar">
        <a className="brand" href="#"><span className="brand-mark"><Workflow size={19} /></span>
          <span><strong>APEXIVE</strong><small>RPA STUDIO</small></span>
        </a>
        <div className="topbar-center"><span className="status-dot" /> WORKSPACE <span className="muted">/</span> VISUAL DESIGNER</div>
        <div className="topbar-actions">
          <button className="button button-quiet" onClick={() => void loadProjectsAndRuns().catch((cause: unknown) => setError(String(cause)))}><Activity size={15} /> Refresh</button>
          <button className="button button-save" disabled={!activeWorkflow || saving} onClick={() => void saveWorkflow()}><Save size={15} /> {saving ? "Saving..." : "Save"}</button>
          <button className="button button-run" disabled={!activeWorkflow} onClick={() => void runWorkflow()}><Play size={14} fill="currentColor" /> Run workflow</button>
        </div>
      </header>

      {(error || notice) && <div className={`toast ${error ? "toast-error" : "toast-success"}`}>
        {error || notice}<button aria-label="Dismiss" onClick={() => { setError(""); setNotice(""); }}><X size={15} /></button>
      </div>}

      <div className="studio-layout">
        <aside className="left-sidebar">
          <div className="sidebar-section">
            <div className="sidebar-heading"><span>PROJECTS</span><button title="Create project" onClick={() => setShowProjectForm((show) => !show)}><Plus size={15} /></button></div>
            {showProjectForm && <div className="create-project">
              <input autoFocus value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="Project name"
                onKeyDown={(event) => { if (event.key === "Enter") void createProject(); if (event.key === "Escape") setShowProjectForm(false); }} />
              <button disabled={loading} onClick={() => void createProject()}><Check size={15} /></button>
            </div>}
            <div className="project-list">
              {projects.map((project) => <button key={project.id} className={`project-item ${project.id === projectId ? "selected" : ""}`} onClick={() => setProjectId(project.id)}>
                <FolderKanban size={15} /><span>{project.name}</span><ChevronDown size={13} className="project-chevron" />
              </button>)}
              {!projects.length && <p className="sidebar-empty">Create a project to begin.</p>}
            </div>
          </div>

          <div className="sidebar-section workflow-section">
            <div className="sidebar-heading"><span>WORKFLOWS</span><button title="Create workflow" disabled={projectId === null} onClick={() => void createWorkflow()}><FilePlus2 size={15} /></button></div>
            {workflows.map((workflow) => <button key={workflow.id} className={`workflow-item ${workflow.id === workflowId ? "selected" : ""}`} onClick={() => setWorkflowId(workflow.id)}>
              <Workflow size={15} /><span>{workflow.name}</span>
            </button>)}
            {!workflows.length && projectId !== null && <p className="sidebar-empty">No workflows in this project.</p>}
          </div>

          <div className="sidebar-bottom">
            <div className="robot-badge"><span className={`robot-pulse ${robotStatus.online ? "robot-online" : ""}`} /><Bot size={17} /><span><b>WINDOWS ROBOT</b><small>{robotStatus.online ? `${robotStatus.workers} worker${robotStatus.workers === 1 ? "" : "s"} connected` : "Queue ready · worker required"}</small></span></div>
            <div className="sidebar-foot">APEXIVE STUDIO <span>v0.2 · LOCAL</span></div>
          </div>
        </aside>

        <section className="designer">
          {activeWorkflow ? <>
            <div className="designer-toolbar">
              <div className="breadcrumb"><span>Projects</span><span>/</span><b>{projects.find((item) => item.id === projectId)?.name}</b><span>/</span><b className="breadcrumb-active">{activeWorkflow.name}</b></div>
              <div className="designer-tools"><button title="Search steps"><Search size={16} /></button><button title="Workflow settings"><Settings2 size={16} /></button></div>
            </div>
            <div className="workflow-heading">
              <div className="workflow-title">
                <span className="workflow-icon"><Workflow size={19} /></span>
                <div><input aria-label="Workflow name" value={workflowName} onChange={(event) => setWorkflowName(event.target.value)} />
                  <p>Visual workflow <span>·</span> Draft</p></div>
              </div>
              <div className="workflow-meta"><span><span className="tiny-dot" /> {steps.length} {steps.length === 1 ? "step" : "steps"}</span><span>Workflow ID #{activeWorkflow.id}</span></div>
            </div>
            <div className="canvas">
              <div className="canvas-grid" />
              <div className="flow">
                <div className="flow-trigger">
                  <span className="trigger-icon"><Play size={13} fill="currentColor" /></span>
                  <span><b>Manual trigger</b><small>Start workflow when run</small></span>
                  <span className="trigger-tag">START</span>
                </div>
                {steps.map((step, index) => {
                  const ActionIcon = ACTIONS.find((item) => item.key === step.action)?.icon ?? Code2;
                  return <div className="flow-step-wrap" key={`${index}-${step.action}`}>
                    <div className="connector"><span /></div>
                    <article className="step-card">
                      <div className="step-card-head">
                        <span className="step-number">{String(index + 1).padStart(2, "0")}</span>
                        <span className="step-action-icon"><ActionIcon size={15} /></span>
                        <strong>{actionLabel(step.action)}</strong>
                        <div className="step-controls">
                          <button title="Move up" disabled={index === 0} onClick={() => moveStep(index, -1)}><ArrowUp size={14} /></button>
                          <button title="Move down" disabled={index === steps.length - 1} onClick={() => moveStep(index, 1)}><ArrowDown size={14} /></button>
                          <button title="Duplicate step" onClick={() => setSteps((current) => [...current.slice(0, index + 1), { ...current[index] }, ...current.slice(index + 1)])}><Copy size={13} /></button>
                          <button title="Delete step" className="delete-step" onClick={() => setSteps((current) => current.filter((_, i) => i !== index))}><Trash2 size={14} /></button>
                        </div>
                      </div>
                      <div className="step-fields">{renderFields(step, index, updateStep)}</div>
                    </article>
                  </div>;
                })}
                <div className="add-step-anchor"><span className="connector-line" />
                  <div className="add-step-menu">
                    {ACTION_GROUPS.map((group) => <div className="action-group" key={group}>
                      <span className="action-group-label">{group === "FLOW" ? "FLOW CONTROL" : `${group} AUTOMATION`}</span>
                      <div className="action-group-items">{ACTIONS.filter((action) => action.group === group).map(({ key, label, icon: Icon }) =>
                        <button key={key} onClick={() => addStep(key)}><Icon size={15} /><span>{label}</span><CirclePlus size={14} className="add-action-icon" /></button>)}
                      </div>
                    </div>)}
                  </div>
                </div>
                <div className="flow-end"><span><Check size={13} /></span> END WORKFLOW</div>
              </div>
              {!steps.length && <div className="canvas-hint"><span>+</span><b>Build your automation</b><small>Add an action below the trigger to start designing.</small></div>}
            </div>
            <div className="execution-bar"><div className="execution-label"><Activity size={16} /><span>RECENT EXECUTIONS</span></div>
              <div className="execution-runs">{workflowRuns.length ? workflowRuns.map((run) => <div key={run.id} className="execution-run">
                <span className={`run-status run-${run.status}`} /> <b>Run #{run.id}</b><span>{run.status}</span>
                {run.error && <small title={run.error}>{run.error}</small>}
              </div>) : <span className="no-runs">No runs yet. Save and run the workflow to queue it for a Windows Robot.</span>}</div>
            </div>
          </> : <div className="empty-designer">
            <div className="empty-icon"><Workflow size={28} /></div><h2>Welcome to RPA Studio</h2>
            <p>Select a workflow or create one to start building a Windows automation.</p>
            <button className="button button-run" disabled={projectId === null || loading} onClick={() => void createWorkflow()}><Plus size={15} /> Create workflow</button>
            {!projects.length && <span>Create a project in the left panel first.</span>}
          </div>}
        </section>

        <aside className="right-sidebar">
          <div className="panel-header"><div><span className="panel-eyebrow">ACTIVITY</span><h2>Execution monitor</h2></div><Activity size={16} /></div>
          <div className="monitor-summary"><span>QUEUED + ACTIVE</span><b>{runs.filter((run) => run.status === "queued" || run.status === "running").length}</b>
            <small>Run requests waiting for a robot</small></div>
          <div className="monitor-heading">LATEST RUNS <span>{runs.length}</span></div>
          <div className="monitor-runs">{runs.slice(0, 12).map((run) => <div className="monitor-run" key={run.id}>
            <span className={`run-status run-${run.status}`} />
            <div><b>Run #{run.id}</b><small>Workflow #{run.workflow_id}</small></div>
            <span className={`run-label run-label-${run.status}`}>{run.status}</span>
          </div>)}{!runs.length && <div className="monitor-empty">Execution history will appear here.</div>}</div>
          <div className="worker-info"><Bot size={17} /><div><b>Windows Robot</b><small>{robotStatus.online ? "Connected and polling the workflow queue." : "Install & connect a worker to execute desktop steps."}</small></div><span className={robotStatus.online ? "worker-online" : "worker-offline"}>{robotStatus.online ? `${robotStatus.workers} ONLINE` : "NOT CONNECTED"}</span></div>
          <div className="supported-actions"><span>AVAILABLE ACTIONS</span><div>Chrome / Edge <i /> Windows UI <i /> Variables <i /> Delay <i /> Logs</div></div>
        </aside>
      </div>
    </main>
  );
}

function renderFields(step: Step, index: number, update: (index: number, key: string, value: string | number | boolean | string[]) => void) {
  const fields: {
    key: string;
    label: string;
    placeholder?: string;
    type?: "number" | "text" | "select";
    options?: { label: string; value: string }[];
    wide?: boolean;
  }[] = [];
  switch (step.action) {
    case "browser_launch":
      fields.push({ key: "browser", label: "Browser", type: "select", options: [{ label: "Google Chrome", value: "chrome" }, { label: "Microsoft Edge", value: "edge" }] });
      fields.push({ key: "headless", label: "Browser window", type: "select", options: [{ label: "Visible", value: "false" }, { label: "Headless", value: "true" }] });
      break;
    case "browser_navigate":
      fields.push({ key: "url", label: "Website URL", placeholder: "https://example.com", wide: true });
      fields.push({ key: "wait_until", label: "Page ready state", type: "select", options: [{ label: "DOM content loaded", value: "domcontentloaded" }, { label: "Load", value: "load" }, { label: "Commit", value: "commit" }] });
      fields.push({ key: "timeout", label: "Timeout (milliseconds)", type: "number" });
      break;
    case "browser_click":
      fields.push({ key: "selector", label: "CSS / Playwright selector", placeholder: "button[type=submit]", wide: true });
      fields.push({ key: "timeout", label: "Timeout (milliseconds)", type: "number" });
      break;
    case "browser_fill":
      fields.push({ key: "selector", label: "Field selector", placeholder: "#email or input[name=email]" });
      fields.push({ key: "text", label: "Text to fill", placeholder: "Text or ${variable}" });
      fields.push({ key: "timeout", label: "Timeout (milliseconds)", type: "number" });
      break;
    case "browser_press":
      fields.push({ key: "selector", label: "Optional element selector", placeholder: "Leave blank for page-level key" });
      fields.push({ key: "key", label: "Key", placeholder: "Enter, Tab, Control+A" });
      fields.push({ key: "timeout", label: "Timeout (milliseconds)", type: "number" });
      break;
    case "browser_select":
      fields.push({ key: "selector", label: "Dropdown selector", placeholder: "select[name=country]" });
      fields.push({ key: "value", label: "Option value", placeholder: "Select option value" });
      fields.push({ key: "timeout", label: "Timeout (milliseconds)", type: "number" });
      break;
    case "browser_wait":
      fields.push({ key: "selector", label: "Element selector", placeholder: "#result or .ready" });
      fields.push({ key: "state", label: "Wait for", type: "select", options: [{ label: "Visible", value: "visible" }, { label: "Hidden", value: "hidden" }, { label: "Attached", value: "attached" }, { label: "Detached", value: "detached" }] });
      fields.push({ key: "timeout", label: "Timeout (milliseconds)", type: "number" });
      break;
    case "browser_get_text":
      fields.push({ key: "selector", label: "Element selector", placeholder: "h1, #status" });
      fields.push({ key: "name", label: "Save as variable", placeholder: "page_title" });
      fields.push({ key: "timeout", label: "Timeout (milliseconds)", type: "number" });
      break;
    case "browser_assert_text":
      fields.push({ key: "selector", label: "Element selector", placeholder: "#status" });
      fields.push({ key: "text", label: "Expected text", placeholder: "Text to check" });
      fields.push({ key: "exact", label: "Match mode", type: "select", options: [{ label: "Contains text", value: "false" }, { label: "Exact match", value: "true" }] });
      fields.push({ key: "timeout", label: "Timeout (milliseconds)", type: "number" });
      break;
    case "browser_close":
      break;
    case "launch_app":
      fields.push({ key: "executable", label: "Application path", placeholder: "C:\\Program Files\\App\\app.exe", wide: true });
      fields.push({ key: "arguments", label: "Arguments (comma separated)", placeholder: "Optional launch arguments", wide: true });
      break;
    case "wait_for_window":
      fields.push({ key: "title", label: "Window title", placeholder: "Window title or exact name", wide: true });
      fields.push({ key: "timeout", label: "Timeout (seconds)", type: "number" });
      break;
    case "click":
      fields.push({ key: "title", label: "Element title", placeholder: "UI element title" });
      fields.push({ key: "auto_id", label: "Automation ID", placeholder: "UI element automation ID" });
      fields.push({ key: "control_type", label: "Control type", placeholder: "Button, Edit, Text..." });
      break;
    case "type_text":
      fields.push({ key: "text", label: "Text to type", placeholder: "Enter text or ${variable}", wide: true });
      fields.push({ key: "title", label: "Element title", placeholder: "Optional UI element title" });
      fields.push({ key: "auto_id", label: "Automation ID", placeholder: "Optional edit control ID" });
      break;
    case "press_key":
      fields.push({ key: "key", label: "Key", placeholder: "{ENTER} · {TAB} · ^a" });
      break;
    case "set_variable":
      fields.push({ key: "name", label: "Variable name", placeholder: "customer_name" });
      fields.push({ key: "value", label: "Value", placeholder: "Text or ${other_variable}" });
      break;
    case "delay":
      fields.push({ key: "seconds", label: "Duration (seconds)", type: "number" });
      break;
    case "log":
      fields.push({ key: "message", label: "Message", placeholder: "Message to add to run output", wide: true });
      break;
  }
  return fields.map((field) => {
    const value = field.key === "arguments" && Array.isArray(step.arguments) ? step.arguments.join(", ") : step[field.key];
    const inputValue = Array.isArray(value) ? value.join(", ") : value === undefined ? "" : String(value);
    return <label className={`step-field ${field.wide ? "field-wide" : ""}`} key={field.key}><span>{field.label}</span>
      {field.type === "select" ? <select value={field.key === "headless" || field.key === "exact" ? String(Boolean(value)) : String(value ?? "")}
        onChange={(event) => update(index, field.key, field.key === "headless" || field.key === "exact" ? event.target.value === "true" : event.target.value)}>
        {field.options?.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}
      </select> : <input type={field.type ?? "text"} value={inputValue} placeholder={field.placeholder}
        onChange={(event) => {
          const raw = event.target.value;
          const parsed: string | number = field.type === "number" ? Number(raw) : raw;
          update(index, field.key, field.key === "arguments" ? raw.split(",").map((item) => item.trim()).filter(Boolean) : parsed);
        }} />}
    </label>;
  });
}
