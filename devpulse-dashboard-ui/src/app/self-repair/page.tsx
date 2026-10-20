'use client';
import { useState } from 'react';
import RepairAnalysis from '@/components/RepairAnalysis';
import RepairWorkbench from '@/components/RepairWorkbench';

export default function SelfRepairPage(){
  const [tab,setTab]=useState<'analysis'|'repair'>('analysis');
  return <div className="min-w-0 space-y-6">
    <div><h1 className="text-2xl font-bold">RaksHex Self-Repair</h1><p className="mt-1 text-sm text-zinc-400">Find a contract change, prepare a bounded repair and review test evidence before publishing.</p></div>
    <div className="flex flex-wrap gap-2" aria-label="Self-Repair workflows">{(['analysis','repair'] as const).map(value=><button key={value} aria-pressed={tab===value} onClick={()=>setTab(value)} className={`rounded-lg border px-4 py-2 text-sm focus-visible:outline-2 focus-visible:outline-blue-300 ${tab===value?'border-blue-500 bg-blue-950 text-blue-100':'border-zinc-700 text-zinc-300'}`}>{value==='analysis'?'Contract analysis':'Repair and validate'}</button>)}</div>
    {tab==='analysis'?<RepairAnalysis/>:<RepairWorkbench/>}
  </div>;
}
