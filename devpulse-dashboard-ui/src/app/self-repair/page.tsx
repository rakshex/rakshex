import RepairAnalysis from '@/components/RepairAnalysis';

export default function SelfRepairPage() {
  return <div className="space-y-6">
    <div><h1 className="text-2xl font-bold">RaksHex Self-Repair</h1>
      <p className="mt-1 text-sm text-zinc-400">Start with evidence of an upstream contract change.</p></div>
    <RepairAnalysis />
  </div>;
}
