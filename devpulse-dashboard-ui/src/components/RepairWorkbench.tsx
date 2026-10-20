'use client';

import { FormEvent, useEffect, useState } from 'react';
import { apiFetch, apiRequest } from '@/lib/transport';

type Workspace = {id:string;name:string;role:string};
type Check = {status:string;tests:number;reason:string;output_hash:string;image:string};
type Job = {id:string;status:string;patch_hash:string;evidence_hash:string;created_at:string;
  report:{migration?:{removed:string;added:string;provenance:string};before_hash?:string;after_hash?:string;message:string;repository:string;base_sha:string;scope:string[];impacts:{file:string;line:number;kind:string}[];
    checks:{accepted?:boolean;before?:Check;after?:Check};limitations:string[];publication?:{url:string}}};
const field='mt-1 w-full min-w-0 rounded-lg border border-zinc-700 bg-zinc-950 p-3 text-sm text-zinc-100 focus-visible:outline-2 focus-visible:outline-blue-400';
const button='rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-500 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-300 disabled:opacity-50';

export default function RepairWorkbench(){
  const [workspaces,setWorkspaces]=useState<Workspace[]>([]);
  const [workspace,setWorkspace]=useState('');
  const [jobs,setJobs]=useState<Job[]>([]);
  const [publicationConfigured,setPublicationConfigured]=useState(false);
  const [manifest,setManifest]=useState('');
  const [consent,setConsent]=useState(false);
  const [error,setError]=useState('');
  const [pending,setPending]=useState(false);
  const [loading,setLoading]=useState(true);
  const [diff,setDiff]=useState<{id:string;text:string}|null>(null);
  const [refresh,setRefresh]=useState(0);
  useEffect(()=>{let active=true;apiRequest<{workspaces:Workspace[]}>('/api/teams/workspaces')
    .then(data=>{if(active){setWorkspaces(data.workspaces);setWorkspace(data.workspaces[0]?.id||'');}})
    .catch(()=>{if(active)setError('Workspaces unavailable. Sign in and retry.');})
    .finally(()=>{if(active)setLoading(false);});return()=>{active=false;};},[]);
  useEffect(()=>{let active=true;
    async function load(){if(!workspace)return;try{
      const data=await apiRequest<{jobs:Job[];publication_configured:boolean}>(`/api/repair-jobs?workspace_id=${encodeURIComponent(workspace)}`);
      if(active){setJobs(data.jobs);setPublicationConfigured(data.publication_configured);}
    }catch{if(active)setError('Repair history unavailable. Retry when the backend is connected.');}}
    void load();const timer=setInterval(load,5000);return()=>{active=false;clearInterval(timer);};},[workspace,refresh]);
  const role=workspaces.find(w=>w.id===workspace)?.role||'';
  const canWrite=['owner','admin','member'].includes(role);const admin=['owner','admin'].includes(role);
  async function submit(event:FormEvent){event.preventDefault();setError('');setDiff(null);
    let body:string;
    try{const input=JSON.parse(manifest);if(!input || Array.isArray(input) || typeof input!=='object')throw Error();
      body=JSON.stringify({...input,workspace_id:workspace,consent});
      if(new TextEncoder().encode(body).length>786432)throw Error();
    }catch{setError('Use a valid repair manifest JSON file under 768 KiB.');return;}
    setPending(true);
    try{await apiRequest('/api/repair-jobs',{method:'POST',body});setManifest('');setConsent(false);setRefresh(v=>v+1);}
    catch{setError('Repair refused or unavailable. Check the confirmed rename, static source scope, tests and encryption configuration. Only one active job is allowed per workspace.');}
    finally{setPending(false);}
  }
  async function artifact(job:Job){setPending(true);setError('');try{
    const data=await apiRequest<{diff:string;patch_hash:string}>(`/api/repair-jobs/${job.id}/artifact`);
    if(data.patch_hash!==job.patch_hash)throw Error();setDiff({id:job.id,text:data.diff});
  }catch{setError('Patch unavailable. Refresh evidence and retry.');}finally{setPending(false);}}
  async function publish(job:Job){if(!window.confirm('Publish this exact validated patch as a draft PR? A person must review and merge it.'))return;
    setPending(true);setError('');try{await apiRequest(`/api/repair-jobs/${job.id}/publish`,{method:'POST',body:JSON.stringify({consent:true,evidence_hash:job.evidence_hash})});setDiff(null);setRefresh(v=>v+1);}
    catch{setError('Publication was not queued. Check current permissions, evidence and the workspace GitHub App connection.');}finally{setPending(false);}}
  async function remove(job:Job){if(!window.confirm('Permanently delete this job and its encrypted source and patch? Existing GitHub PRs will remain.'))return;
    setPending(true);setError('');try{await apiFetch(`/api/repair-jobs/${job.id}`,{method:'DELETE'});if(diff?.id===job.id)setDiff(null);setRefresh(v=>v+1);}
    catch{setError('Could not delete evidence. Wait for the worker to finish and check admin access.');}finally{setPending(false);}}
  if(loading)return <p role="status">Loading repair workspace…</p>;
  return <div className="space-y-6">
    <div className="rounded-xl border border-blue-900 bg-blue-950/20 p-4 text-sm text-blue-100">
      <h2 className="font-semibold">Repair a confirmed API request property rename</h2>
      <p className="mt-2">Supported now: Python requests calls with a literal HTTPS URL and inline JSON object. Submit existing regression tests and an explicit migration reference. Dynamic calls, other SDKs and semantic changes require manual repair.</p>
      <p className="mt-2">Plan → isolated failing/passing tests → review exact diff → approve draft PR. Nothing is merged automatically.</p>
    </div>
    {error&&<p role="alert" className="rounded-lg border border-red-900 p-3 text-red-200">{error}</p>}
    {!workspaces.length?<p>Create a workspace in the Contract analysis tab, then reopen this workflow.</p>:<>
      <label className="block">Repair workspace<select className={field} value={workspace} disabled={pending} onChange={e=>{setWorkspace(e.target.value);setJobs([]);setManifest('');setConsent(false);setDiff(null);setError('');}}>{workspaces.map(w=><option key={w.id} value={w.id}>{w.name} ({w.role})</option>)}</select></label>
      {canWrite?<form onSubmit={submit} className="space-y-4 rounded-xl border border-zinc-800 p-4 sm:p-6">
        <h3 className="font-semibold">1. Submit a scoped repair manifest</h3>
        <p className="text-sm text-zinc-400">Include before/after inline OpenAPI contracts, files (relative .py path → source, including tests/test_*.py), repository, optional source_root, base_branch, immutable base_sha and rule (method, path, origin, removed, added, provenance). The source must match the repository commit before a PR can be published.</p>
        <label className="block text-sm">Load manifest JSON<input className="mt-2 block w-full text-sm file:mr-3 file:rounded-lg file:border-0 file:bg-zinc-800 file:p-2" type="file" accept=".json,application/json" disabled={pending} onChange={async e=>{const file=e.target.files?.[0];if(!file)return;if(file.size>786432){setError('Manifest exceeds 768 KiB.');return;}setManifest(await file.text());setConsent(false);e.target.value='';}}/></label>
        <label className="block text-sm">Repair manifest<textarea className={`${field} font-mono`} rows={12} value={manifest} onChange={e=>{setManifest(e.target.value);setConsent(false);}} required disabled={pending} spellCheck={false}/></label>
        <p className="text-sm text-zinc-400">Submitted contracts, scoped source and patch are encrypted on the server until you delete the job. Tests run on a separate worker with no network or credentials. No source is sent to a model. Avoid submitting secrets. Authorized workspace members can review the diff.</p>
        <label className="flex items-start gap-3 text-sm"><input className="mt-1" type="checkbox" required checked={consent} disabled={pending} onChange={e=>setConsent(e.target.checked)}/>I am authorized to submit these files and consent to encrypted storage and isolated test execution.</label>
        <button className={button} disabled={pending||!consent||!manifest.trim()}>{pending?'Submitting…':'Plan repair and queue validation'}</button>
      </form>:<p>Your workspace role can review evidence but cannot submit repairs.</p>}
      <section aria-label="Repair jobs" className="space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-lg font-semibold">2. Review validation and patch</h3><button className="text-sm text-blue-300 underline" disabled={pending} onClick={()=>{setError('');setRefresh(v=>v+1);}}>Refresh repair jobs</button></div>
        {!publicationConfigured&&<p className="rounded-lg border border-amber-900 p-3 text-sm text-amber-100">GitHub App publication is not connected for this workspace. Planning and worker validation are available; publishing remains blocked until an administrator connects the repository.</p>}
        {!jobs.length?<p className="text-zinc-400">No repair jobs in this workspace yet.</p>:jobs.map(job=><article key={job.id} className="min-w-0 space-y-3 rounded-xl border border-zinc-800 p-4 sm:p-6">
          <div className="flex flex-wrap justify-between gap-2"><h4 className="break-all font-medium">{job.report.repository}</h4><span role="status" className="rounded bg-zinc-800 px-2 py-1 text-xs">{job.status.replaceAll('_',' ')}</span></div>
          <p className="text-sm">{job.report.message}</p>
          {job.report.migration&&<p className="break-all text-sm text-zinc-300">Proposed migration: <code>{job.report.migration.removed}</code> → <code>{job.report.migration.added}</code>. <a className="text-blue-300 underline" href={job.report.migration.provenance} target="_blank" rel="noopener noreferrer">Review migration reference</a></p>}
          {job.report.before_hash&&<p className="break-all text-xs text-zinc-400">Contract fingerprints: {job.report.before_hash} → {job.report.after_hash}</p>}
          <p className="break-all text-xs text-zinc-400">Base commit: {job.report.base_sha}<br/>Patch SHA-256: {job.patch_hash}</p>
          <ul className="space-y-1 text-sm">{job.report.impacts.map((impact,i)=><li className="break-all" key={i}>{impact.file}:{impact.line} — request property rename</li>)}</ul>
          {job.report.checks.before&&job.report.checks.after&&<div className="grid gap-3 sm:grid-cols-2">{(['before','after'] as const).map(stage=>{const check=job.report.checks[stage]!;return <div className="rounded-lg bg-zinc-900 p-3 text-sm" key={stage}><strong>{stage==='before'?'Baseline':'Candidate'}: {check.status}</strong><p>{check.tests} tests · {check.reason}</p><p className="mt-1 break-all text-xs text-zinc-400">Output fingerprint: {check.output_hash}</p></div>;})}</div>}
          <div className="flex flex-wrap gap-3"><button className={button} disabled={pending} onClick={()=>artifact(job)}>Review patch</button>
            {admin&&job.status==='validated'&&<button className={button} disabled={pending||!publicationConfigured||diff?.id!==job.id} onClick={()=>publish(job)}>Approve draft PR publication</button>}
            {job.report.publication&&<a className="rounded-lg border border-blue-700 px-4 py-2 text-sm text-blue-200" href={job.report.publication.url} target="_blank" rel="noopener noreferrer">Open draft PR</a>}
            {admin&&<button className="px-3 py-2 text-sm text-red-300 underline" disabled={pending||['validating','publishing','publication_queued'].includes(job.status)} onClick={()=>remove(job)}>Delete repair data</button>}
          </div>
          {diff?.id===job.id&&<div><h5 className="mb-2 text-sm font-semibold">Exact proposed patch</h5><pre tabIndex={0} aria-label="Proposed patch" className="max-h-96 overflow-auto rounded-lg border border-zinc-700 bg-zinc-950 p-3 text-xs">{diff.text}</pre></div>}
          <ul className="text-xs text-amber-200">{job.report.limitations.map(item=><li key={item}>{item}</li>)}</ul>
        </article>)}
      </section>
    </>}
  </div>;
}
