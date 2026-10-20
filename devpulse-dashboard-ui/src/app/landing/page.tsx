import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'RaksHex — API Change Intelligence',
  description: 'Compare authorized API contracts and review the evidence. The first stage of RaksHex Self-Repair.',
};

const modules = [
  { name: 'Self-Repair', status: 'Contract analysis available', description: 'Compare two inline OpenAPI contracts, review operation changes and retain a workspace-scoped evidence record. Code impact, patch validation and GitHub draft PRs are next.' },
  { name: 'Budget Lock', status: 'Planned', description: 'The roadmap includes enforceable action limits, cumulative budgets and emergency freezes. A live financial execution gateway is not enabled.' },
  { name: 'LeakShield', status: 'Security hardening pending', description: 'Authorized secret detection and containment remain part of the platform. Existing scanning needs further isolation and redaction before production use.' },
  { name: 'Controlled agent execution', status: 'Separate design track', description: 'Credential isolation, exact-action authorization, approvals and outcome evidence are required before an agent can perform a real external action.' },
];

export default function LandingPage() {
  return <div className="mx-auto max-w-5xl space-y-16 py-8 text-zinc-100">
    <nav aria-label="Product navigation" className="flex flex-wrap items-center justify-between gap-4 border-b border-zinc-800 pb-6">
      <Link href="/landing" className="text-xl font-bold">RaksHex</Link>
      <div className="flex flex-wrap gap-5 text-sm"><Link href="/self-repair">Self-Repair</Link><Link href="/login">Sign in</Link></div>
    </nav>
    <section className="space-y-6">
      <p className="inline-block rounded-full border border-blue-800 px-3 py-1 text-xs text-blue-200">API Change Intelligence · Early implementation</p>
      <h1 className="max-w-3xl text-4xl font-semibold leading-tight tracking-tight md:text-6xl">See what changed in your API contract.</h1>
      <p className="max-w-2xl text-lg leading-relaxed text-zinc-400">RaksHex starts with authorized contract analysis and a reviewable evidence trail. Code impact, tested patches and human-reviewed draft pull requests are the next stages of Self-Repair.</p>
      <div className="flex flex-wrap gap-4"><Link href="/self-repair" className="rounded-lg bg-blue-600 px-5 py-3 font-medium hover:bg-blue-500">Analyze contracts</Link><Link href="/login" className="rounded-lg border border-zinc-700 px-5 py-3">Create an account</Link></div>
      <p className="text-sm text-amber-200">This is an initial analysis workflow, not a production-ready repair platform. No automatic merge or provider action is performed.</p>
    </section>
    <section aria-labelledby="workflow-heading" className="space-y-6">
      <h2 id="workflow-heading" className="text-2xl font-semibold">From contract change to evidence</h2>
      <ol className="grid gap-4 md:grid-cols-3">
        <li className="rounded-xl border border-zinc-800 p-5"><h3 className="font-semibold">1. Authorize processing</h3><p className="mt-3 text-sm text-zinc-400">Sign in, choose your workspace and explicitly consent to submitting two contracts you are authorized to analyze.</p></li>
        <li className="rounded-xl border border-zinc-800 p-5"><h3 className="font-semibold">2. Compare operations</h3><p className="mt-3 text-sm text-zinc-400">Analyze inline OpenAPI 3.0/3.1 JSON for added, removed or structurally changed operations. References, callbacks and webhooks are not supported yet.</p></li>
        <li className="rounded-xl border border-zinc-800 p-5"><h3 className="font-semibold">3. Review the evidence</h3><p className="mt-3 text-sm text-zinc-400">Inspect results and limitations, revisit workspace history and retain human control. Analysis does not certify compatibility or a repaired integration.</p></li>
      </ol>
    </section>
    <section aria-labelledby="modules-heading" className="space-y-6">
      <h2 id="modules-heading" className="text-2xl font-semibold">One platform, delivered in stages</h2>
      <div className="grid gap-5 md:grid-cols-2">{modules.map(module => <article key={module.name} className="space-y-3 rounded-xl border border-zinc-800 bg-zinc-900/40 p-6">
        <p className="text-xs font-medium text-blue-300">{module.status}</p><h3 className="text-xl font-semibold">{module.name}</h3><p className="text-sm leading-relaxed text-zinc-400">{module.description}</p>
      </article>)}</div>
    </section>
    <section aria-labelledby="privacy-heading" className="space-y-4 rounded-xl border border-blue-900 p-6">
      <h2 id="privacy-heading" className="text-2xl font-semibold">A clear processing boundary</h2>
      <p className="leading-relaxed text-zinc-400">The contract-analysis intake stores input hashes and analysis metadata, not raw specifications. It does not access a repository, send code to a model provider or execute external actions. Do not submit credentials. Workspace owners and admins can delete saved analysis evidence.</p>
      <p className="text-sm text-zinc-400">Pricing and production release terms are not finalized. There are no measured savings or customer-adoption claims for this milestone.</p>
    </section>
    <footer className="flex flex-wrap justify-between gap-4 border-t border-zinc-800 pt-6 text-sm text-zinc-500"><p>RaksHex · API Change Intelligence</p><a href="https://github.com/rakshex/rakshex/tree/codex/rakshex-foundation-20261020" className="text-blue-300">View development source on GitHub</a></footer>
  </div>;
}
