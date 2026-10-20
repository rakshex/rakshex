'use client';

import { FormEvent, useEffect, useState } from 'react';
import { apiRequest } from '@/lib/transport';

type Workspace = { id: string; name: string; role: string };
type Analysis = { id: string; workspace_id: string; created_at: string; evidence_hash: string;
  report: { outcome: string; before_hash: string; after_hash: string; before_operations: number;
    after_operations: number; changes: { operation_ref: string; method: string; kind: string; compatibility: string }[];
    limitations: string[] } };

export default function RepairAnalysis() {
  const [workspaceName, setWorkspaceName] = useState('');
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [workspaceId, setWorkspaceId] = useState('');
  const [before, setBefore] = useState('');
  const [after, setAfter] = useState('');
  const [consent, setConsent] = useState(false);
  const [history, setHistory] = useState<Analysis[]>([]);
  const [selected, setSelected] = useState<Analysis | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [workspaceLoadFailed, setWorkspaceLoadFailed] = useState(false);
  const [historyFailed, setHistoryFailed] = useState(false);
  const [pending, setPending] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    let active = true;
    apiRequest<{ workspaces: Workspace[] }>('/api/teams/workspaces').then(data => {
      if (active) { setWorkspaces(data.workspaces); setWorkspaceId(data.workspaces[0]?.id || ''); }
    }).catch(() => { if (active) { setWorkspaceLoadFailed(true); setError('Unable to load workspaces. Sign in and retry.'); } })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    setHistory([]); setSelected(null);
    if (!workspaceId) return () => { active = false; };
    setHistoryLoading(true); setHistoryFailed(false); setError('');
    apiRequest<{ analyses: Analysis[] }>(`/api/repair-analyses?workspace_id=${encodeURIComponent(workspaceId)}`)
      .then(data => { if (active) setHistory(data.analyses); })
      .catch(() => { if (active) { setHistoryFailed(true); setError('Unable to load analysis history.'); } })
      .finally(() => { if (active) setHistoryLoading(false); });
    return () => { active = false; };
  }, [workspaceId]);

  const workspace = workspaces.find(item => item.id === workspaceId);
  const canWrite = ['owner', 'admin', 'member'].includes(workspace?.role || '');

  async function submit(event: FormEvent) {
    event.preventDefault(); setError('');
    let payload;
    try { payload = JSON.stringify({ workspace_id: workspaceId, consent, before: JSON.parse(before), after: JSON.parse(after) }); }
    catch { setError('Both contracts must contain valid JSON.'); return; }
    if (new TextEncoder().encode(payload).length > 262144) { setError('Combined input must be at most 256 KiB.'); return; }
    setPending(true);
    try {
      const data = await apiRequest<{ analysis: Analysis }>('/api/repair-analyses', { method: 'POST', body: payload });
      setSelected(data.analysis); setHistory(items => [data.analysis, ...items].slice(0, 20));
      setBefore(''); setAfter(''); setConsent(false);
    } catch { setError('Analysis failed. Check authorization, consent, size and inline OpenAPI 3 format.'); }
    finally { setPending(false); }
  }

  async function remove(item: Analysis) {
    setPending(true); setError('');
    try {
      // DELETE has no JSON body; the generic JSON helper is deliberately not used.
      const { apiFetch } = await import('@/lib/transport');
      await apiFetch(`/api/repair-analyses/${item.id}`, { method: 'DELETE' });
      setHistory(items => items.filter(row => row.id !== item.id));
      if (selected?.id === item.id) setSelected(null);
    } catch { setError('Unable to delete evidence. Owner or admin access is required.'); }
    finally { setPending(false); }
  }

  async function createWorkspace(event: FormEvent) {
    event.preventDefault(); setPending(true); setError('');
    try {
      const data = await apiRequest<{ id: string; name: string }>('/api/teams/workspaces', {
        method: 'POST', body: JSON.stringify({ name: workspaceName.trim() }),
      });
      setWorkspaces(items => [...items, { id: data.id, name: data.name, role: 'owner' }]);
      setWorkspaceId(data.id); setWorkspaceName('');
    } catch { setError('Unable to create workspace. Sign in and retry.'); }
    finally { setPending(false); }
  }

  const field = 'w-full rounded-lg border border-zinc-700 bg-zinc-950 p-3 text-sm text-zinc-100';
  if (loading) return <p role="status">Loading workspaces…</p>;
  return <div className="space-y-6">
    <p className="rounded-lg border border-blue-800 p-4 text-sm text-blue-200">
      Contract analysis is available. Code impact, patches, isolated test validation and GitHub draft PR publication are pending integration.
      Only inline OpenAPI 3.0/3.1 JSON is supported; references, callbacks and webhooks are rejected.
    </p>
    {error && <p role="alert" className="text-red-300">{error}</p>}
    {workspaceLoadFailed ? <button onClick={() => window.location.reload()}>Retry loading workspaces</button> : !workspaces.length ? <form onSubmit={createWorkspace} className="space-y-3">
      <p>Create your first workspace to begin.</p>
      <label className="block">Workspace name<input className={field} value={workspaceName} onChange={e => setWorkspaceName(e.target.value)} maxLength={100} required disabled={pending} /></label>
      <button className="rounded-lg bg-blue-600 px-4 py-2 disabled:opacity-50" disabled={pending || !workspaceName.trim()}>Create workspace</button>
    </form> : <>
      <label className="block">Workspace
        <select className={field} value={workspaceId} disabled={pending} onChange={e => setWorkspaceId(e.target.value)}>
          {workspaces.map(item => <option key={item.id} value={item.id}>{item.name} ({item.role})</option>)}
        </select>
      </label>
      {canWrite ? <form onSubmit={submit} className="space-y-4">
        <div className="grid gap-4 lg:grid-cols-2">
          <label>Previous contract<textarea className={`${field} mt-2 font-mono`} rows={12} value={before} onChange={e => setBefore(e.target.value)} required disabled={pending} spellCheck={false} /></label>
          <label>Current contract<textarea className={`${field} mt-2 font-mono`} rows={12} value={after} onChange={e => setAfter(e.target.value)} required disabled={pending} spellCheck={false} /></label>
        </div>
        <p className="text-sm text-zinc-400">These contracts are processed on the server. Only input hashes, hashed operation references and result metadata are saved. Do not paste credentials. No repository is read or code sent to a model provider.</p>
        <label className="flex gap-3"><input type="checkbox" checked={consent} onChange={e => setConsent(e.target.checked)} required disabled={pending} />I am authorized to submit these contracts and consent to server-side analysis.</label>
        <button className="rounded-lg bg-blue-600 px-4 py-2 disabled:opacity-50" disabled={!consent || pending || historyLoading} type="submit">{pending ? 'Processing…' : 'Analyze contracts'}</button>
      </form> : <p>Your workspace role has read-only access.</p>}
      <section aria-label="Analysis history" className="space-y-3">
        <h2 className="text-lg font-semibold">Analysis history</h2>
        {historyLoading ? <p role="status">Loading history…</p> : historyFailed ? <p>History is unavailable.</p> : !history.length ? <p>No analyses in this workspace yet.</p> : history.map(item => <div key={item.id} className="flex flex-wrap gap-3 rounded-lg border border-zinc-800 p-3">
          <button className="text-blue-300" onClick={() => setSelected(item)}>{new Date(item.created_at).toLocaleString()} — {item.report.changes.length} operation changes</button>
          {['owner', 'admin'].includes(workspace?.role || '') && <button className="ml-auto text-red-300" disabled={pending} onClick={() => remove(item)}>Delete evidence</button>}
        </div>)}
      </section>
    </>}
    {selected && <section aria-label="Analysis evidence" className="space-y-3 rounded-lg border border-zinc-800 p-4">
      <h2 className="text-lg font-semibold">{selected.report.outcome === 'review_required' ? 'Human review required' : 'No operation change detected'}</h2>
      <p>{selected.report.before_operations} previous / {selected.report.after_operations} current operations. This result does not certify compatibility or a repair.</p>
      <p className="break-all text-xs text-zinc-400">Evidence hash: {selected.evidence_hash}</p>
      <ul>{selected.report.changes.map(change => <li key={change.operation_ref} className="break-all py-1 font-mono text-xs">{change.method} {change.operation_ref.slice(0, 16)}: {change.kind} ({change.compatibility})</li>)}</ul>
      <ul className="text-sm text-amber-200">{selected.report.limitations.map(item => <li key={item}>{item}</li>)}</ul>
    </section>}
  </div>;
}
