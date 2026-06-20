import { useState, useRef } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const WS_BASE = API_BASE.replace('http', 'ws')

const SAMPLE_PAPERS = [
  { label: 'Mistral 7B', id: '2310.06825' },
  { label: 'Attention Is All You Need', id: '1706.03762' },
  { label: 'LoRA', id: '2106.09685' },
]

const VERDICT_STYLES = {
  'Highly Reproducible': { color: 'var(--sage)', bg: 'var(--sage-tint)' },
  'Reproducible with Effort': { color: 'var(--amber)', bg: 'var(--amber-tint)' },
  'Significant Barriers': { color: 'var(--red)', bg: 'var(--red-tint)' },
  'Not Reproducible': { color: 'var(--red)', bg: 'var(--red-tint)' },
}

const SEVERITY_STYLES = {
  high: { color: 'var(--red)', label: 'High' },
  medium: { color: 'var(--amber)', label: 'Medium' },
  low: { color: 'var(--sage)', label: 'Low' },
}

const CATEGORY_LABELS = {
  data_leakage: 'Data leakage',
  missing_baselines: 'Missing baselines',
  statistical_rigor: 'Statistical rigor',
  compute_transparency: 'Compute transparency',
  dataset_availability: 'Dataset availability',
  code_availability: 'Code availability',
  implausible_results: 'Implausible results',
}

function Stamp({ score }) {
  const color = score >= 7 ? 'var(--sage)' : score >= 4 ? 'var(--amber)' : 'var(--red)'
  return (
    <div className="score-stamp font-serif-display" style={{ color }}>
      <svg viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M 50 6 C 75 6 94 25 94 50 C 94 75 75 94 50 94 C 25 94 6 75 6 50 C 6 25 25 6 50 6"
          stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"
          style={{ opacity: 0.55 }}
        />
      </svg>
      <span className="text-3xl font-semibold relative">{score}</span>
    </div>
  )
}

function IssueRow({ issue }) {
  const sev = SEVERITY_STYLES[issue.severity] || SEVERITY_STYLES.low
  return (
    <div className="py-5 border-t border-[var(--rule)] first:border-t-0 first:pt-0">
      <div className="flex items-baseline gap-3 mb-2 flex-wrap">
        <span
          className="font-mono text-xs uppercase tracking-wider font-medium px-1.5 py-0.5"
          style={{ color: sev.color, border: `1px solid ${sev.color}` }}
        >
          {sev.label}
        </span>
        <span className="font-mono text-xs uppercase tracking-wider text-[var(--ink-faint)]">
          {CATEGORY_LABELS[issue.category] || issue.category}
        </span>
      </div>
      <p className="text-[15px] leading-relaxed mb-2">{issue.description}</p>
      <p className="text-sm text-[var(--ink-soft)] leading-relaxed">
        <span className="font-medium text-[var(--ink)]">→ </span>
        {issue.recommendation}
      </p>
    </div>
  )
}

function Section({ number, title, children }) {
  return (
    <section className="mb-12">
      <div className="flex items-baseline gap-3 mb-4 pb-2 border-b border-[var(--ink)]">
        <span className="font-mono text-xs text-[var(--ink-faint)]">{number}</span>
        <h2 className="font-serif-display text-xl font-semibold">{title}</h2>
      </div>
      {children}
    </section>
  )
}

export default function App() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const wsRef = useRef(null)

  const runAnalysis = (q) => {
    setError('')
    setResult(null)
    setLoading(true)
    setProgress('Connecting…')

    const ws = new WebSocket(`${WS_BASE}/ws/analyze`)
    wsRef.current = ws

    ws.onopen = () => ws.send(JSON.stringify({ query: q }))
    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'progress') setProgress(msg.message)
      else if (msg.type === 'result') { setResult(msg.data); setLoading(false) }
      else if (msg.type === 'error') { setError(msg.message); setLoading(false) }
    }
    ws.onerror = () => {
      setError('Could not reach the analysis server. Is the backend running?')
      setLoading(false)
    }
  }

  const runUpload = (file) => {
    setError('')
    setResult(null)
    setLoading(true)
    setProgress('Reading PDF…')

    const formData = new FormData()
    formData.append('file', file)

    fetch(`${API_BASE}/api/analyze/upload`, { method: 'POST', body: formData })
      .then(async (res) => {
        if (!res.ok) {
          const err = await res.json().catch(() => ({}))
          throw new Error(err.detail || 'Could not analyze this file.')
        }
        return res.json()
      })
      .then((data) => { setResult(data); setLoading(false) })
      .catch((err) => { setError(err.message); setLoading(false) })
  }

  const handleFileChange = (e) => {
    const file = e.target.files?.[0]
    if (file) runUpload(file)
    e.target.value = ''
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!query.trim()) return
    runAnalysis(query.trim())
  }

  return (
    <div className="min-h-screen">
      <div className="max-w-2xl mx-auto px-6 py-12 md:py-16">

        {/* Masthead */}
        <header className="mb-12 pb-8 border-b-2 border-[var(--ink)]">
          <div className="flex items-baseline justify-between mb-1">
            <span className="font-mono text-xs uppercase tracking-[0.15em] text-[var(--ink-faint)]">
              Vol. I · Automated Review
            </span>
            <span className="font-mono text-xs text-[var(--ink-faint)]">
              {new Date().toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
            </span>
          </div>
          <h1 className="font-serif-display text-4xl md:text-5xl font-semibold leading-tight mb-2">
            Paper Reproducibility Desk
          </h1>
          <p className="text-[var(--ink-soft)] leading-relaxed max-w-lg">
            Submit a paper! An arXiv link or ID, a direct PDF link, or upload the PDF. A panel of
            automated referees will check its methodology, hunt for code, and red-pen
            anything that looks hard to reproduce.
          </p>
        </header>

        {/* Input */}
        <form onSubmit={handleSubmit} className="mb-10">
          <label className="block font-mono text-xs uppercase tracking-wider text-[var(--ink-faint)] mb-2">
            Manuscript
          </label>
          <div className="flex flex-col sm:flex-row gap-2">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="arXiv URL, arXiv ID, or PDF link"
              className="flex-1 px-3 py-2.5 bg-[var(--paper-raised)] border border-[var(--ink)] outline-none focus:ring-2 focus:ring-[var(--red)] focus:ring-offset-0 transition placeholder:text-[var(--ink-faint)] font-mono text-sm"
            />
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 bg-[var(--ink)] text-[var(--paper)] font-medium text-sm hover:bg-[var(--ink-soft)] transition disabled:opacity-40 whitespace-nowrap"
            >
              {loading ? 'Reviewing…' : 'Submit for review'}
            </button>
            <label className="px-5 py-2.5 border border-[var(--ink)] font-medium text-sm hover:bg-[var(--paper-raised)] transition cursor-pointer text-center whitespace-nowrap">
              Upload PDF
              <input type="file" accept="application/pdf" onChange={handleFileChange} disabled={loading} className="hidden" />
            </label>
          </div>
          <div className="flex gap-4 mt-3 items-baseline flex-wrap">
            <span className="font-mono text-xs text-[var(--ink-faint)]">Examples —</span>
            {SAMPLE_PAPERS.map((p) => (
              <button
                key={p.id}
                type="button"
                onClick={() => { setQuery(p.id); runAnalysis(p.id) }}
                className="text-sm underline decoration-[var(--rule)] hover:decoration-[var(--red)] hover:text-[var(--red)] transition underline-offset-4"
              >
                {p.label}
              </button>
            ))}
          </div>
        </form>

        {/* Loading */}
        {loading && (
          <div className="py-16 text-center">
            <div className="font-mono text-sm text-[var(--ink-soft)] mb-3">{progress}</div>
            <div className="w-full h-px bg-[var(--rule)] relative overflow-hidden">
              <div className="absolute inset-y-0 left-0 w-1/3 bg-[var(--ink)] animate-pulse"></div>
            </div>
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="p-4 border-l-2 border-[var(--red)] bg-[var(--red-tint)] mb-8">
            <p className="font-mono text-xs uppercase tracking-wider text-[var(--red)] mb-1">
              {error.startsWith('This document') ? 'Invalid document' : 'Could not complete review'}
            </p>
            <p className="text-sm">{error.replace('Pipeline error: ', '')}</p>
          </div>
        )}

        {/* Results */}
        {result && (
          <article>
            {/* Paper byline */}
            <div className="mb-8 pb-6 border-b border-[var(--rule)]">
              <h2 className="font-serif-display text-2xl font-semibold leading-snug mb-2">
                {result.paper.title}
              </h2>
              <p className="text-sm text-[var(--ink-soft)] mb-1">
                {result.paper.authors?.length > 0
                  ? `${result.paper.authors.slice(0, 4).join(', ')}${result.paper.authors.length > 4 ? `, +${result.paper.authors.length - 4} more` : ''}`
                  : 'Authors not identified'}
              </p>
              <div className="flex items-center gap-3 flex-wrap">
                {result.paper.abs_url && (
                  <a href={result.paper.abs_url} target="_blank" rel="noreferrer"
                     className="font-mono text-xs text-[var(--ink-faint)] underline hover:text-[var(--red)]">
                    {result.paper.abs_url.replace('https://', '')}
                  </a>
                )}
                <span className="font-mono text-xs text-[var(--ink-faint)]">
                  · text source: {result.paper.fulltext_source?.replace(/_/g, ' ')}
                </span>
                {result._cached && (
                  <span className="font-mono text-xs text-[var(--ink-faint)]">· from archive</span>
                )}
              </div>
            </div>

            {/* Verdict block */}
            <div className="flex gap-6 items-start mb-12 p-6 bg-[var(--paper-raised)] border border-[var(--rule)]">
              <Stamp score={result.plausibility.overall_reproducibility_score} />
              <div className="flex-1">
                <div
                  className="inline-block font-mono text-xs uppercase tracking-wider font-medium px-2 py-1 mb-3"
                  style={{
                    color: VERDICT_STYLES[result.report.verdict]?.color,
                    background: VERDICT_STYLES[result.report.verdict]?.bg
                  }}
                >
                  {result.report.verdict}
                </div>
                <p className="text-[15px] leading-relaxed">{result.report.executive_summary}</p>
              </div>
            </div>

            {/* Top priorities */}
            <Section number="01" title="Where to start">
              <ol className="space-y-3">
                {result.report.top_priorities?.map((p, i) => (
                  <li key={i} className="flex gap-3 text-[15px] leading-relaxed">
                    <span className="font-mono text-[var(--ink-faint)] flex-shrink-0">{String(i + 1).padStart(2, '0')}</span>
                    <span>{p}</span>
                  </li>
                ))}
              </ol>
            </Section>

            {/* Issues */}
            <Section number="02" title="Referee notes">
              <div>
                {result.plausibility.issues?.length > 0
                  ? result.plausibility.issues.map((issue, i) => <IssueRow key={i} issue={issue} />)
                  : <p className="text-sm text-[var(--ink-soft)]">No issues flagged.</p>}
              </div>
            </Section>

            {/* Claims */}
            <Section number="03" title="Reported results">
              <p className="text-sm text-[var(--ink-soft)] italic mb-4 leading-relaxed">
                {result.claims.headline_claim}
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-sm font-mono">
                  <thead>
                    <tr className="border-b border-[var(--ink)]">
                      <th className="text-left py-2 pr-4 font-medium uppercase text-xs tracking-wider text-[var(--ink-faint)]">Metric</th>
                      <th className="text-left py-2 pr-4 font-medium uppercase text-xs tracking-wider text-[var(--ink-faint)]">Value</th>
                      <th className="text-left py-2 pr-4 font-medium uppercase text-xs tracking-wider text-[var(--ink-faint)]">Dataset</th>
                      <th className="text-left py-2 font-medium uppercase text-xs tracking-wider text-[var(--ink-faint)]">Method</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.claims.claims?.map((c, i) => (
                      <tr key={i} className="border-b border-[var(--rule)]">
                        <td className="py-2 pr-4">{c.metric}</td>
                        <td className="py-2 pr-4 font-semibold">{c.value}</td>
                        <td className="py-2 pr-4 text-[var(--ink-soft)]">{c.dataset}</td>
                        <td className="py-2 text-[var(--ink-soft)]">{c.method}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Section>

            {/* Methodology */}
            <Section number="04" title="Methodology on record">
              <div className="grid sm:grid-cols-2 gap-x-8 gap-y-6 text-sm">
                <div>
                  <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink-faint)] mb-2">Datasets</div>
                  <ul className="space-y-1 leading-relaxed">
                    {result.methodology.datasets?.map((d, i) => (
                      <li key={i}>{d.name} <span className="text-[var(--ink-faint)] font-mono text-xs">({d.availability})</span></li>
                    ))}
                  </ul>
                </div>
                <div>
                  <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink-faint)] mb-2">Models</div>
                  <ul className="space-y-1 leading-relaxed">
                    {result.methodology.models?.map((m, i) => <li key={i}>{m.name}</li>)}
                  </ul>
                </div>
                <div>
                  <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink-faint)] mb-2">Baselines</div>
                  <ul className="space-y-1 leading-relaxed">
                    {result.methodology.baselines?.map((b, i) => <li key={i}>{b}</li>)}
                  </ul>
                </div>
                <div>
                  <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink-faint)] mb-2">Metrics</div>
                  <ul className="space-y-1 leading-relaxed">
                    {result.methodology.metrics?.map((m, i) => <li key={i}>{m}</li>)}
                  </ul>
                </div>
                <div className="sm:col-span-2 pt-2 border-t border-[var(--rule)]">
                  <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink-faint)] mb-2">Training setup</div>
                  <p className="leading-relaxed">
                    Compute: {result.methodology.training_setup?.compute} ·{' '}
                    Optimizer: {result.methodology.training_setup?.optimizer} ·{' '}
                    Hardware: {result.methodology.training_setup?.hardware}
                  </p>
                </div>
                <div className="sm:col-span-2">
                  <div className="font-mono text-xs uppercase tracking-wider text-[var(--ink-faint)] mb-2">Split methodology</div>
                  <p className="leading-relaxed">{result.methodology.split_methodology}</p>
                </div>
              </div>
            </Section>

            {/* Code */}
            <Section number="05" title="Code on file">
              <p className="text-sm mb-4">
                Official implementation:{' '}
                <span className="font-medium" style={{ color: result.code_info.official_implementation_found ? 'var(--sage)' : 'var(--amber)' }}>
                  {result.code_info.official_implementation_found ? 'Found' : 'Not found'}
                </span>
              </p>
              <div className="space-y-0">
                {result.code_info.papers_with_code?.repositories?.map((r, i) => (
                  <a key={`pwc-${i}`} href={r.url} target="_blank" rel="noreferrer"
                     className="flex justify-between items-baseline gap-4 py-2.5 border-t border-[var(--rule)] first:border-t-0 hover:text-[var(--red)] transition group">
                    <span className="font-mono text-sm underline decoration-[var(--rule)] group-hover:decoration-[var(--red)] truncate">{r.url}</span>
                    <span className="font-mono text-xs text-[var(--ink-faint)] whitespace-nowrap">
                      {r.stars}★ · {r.framework}{r.is_official ? ' · official' : ''}
                    </span>
                  </a>
                ))}
                {result.code_info.github_candidates?.slice(0, 5).map((r, i) => (
                  <a key={`gh-${i}`} href={r.url} target="_blank" rel="noreferrer"
                     className="block py-2.5 border-t border-[var(--rule)] first:border-t-0 hover:text-[var(--red)] transition group">
                    <div className="flex justify-between items-baseline gap-4">
                      <span className="font-mono text-sm underline decoration-[var(--rule)] group-hover:decoration-[var(--red)]">{r.name}</span>
                      <span className="font-mono text-xs text-[var(--ink-faint)] whitespace-nowrap">{r.stars}★</span>
                    </div>
                    {r.description && <p className="text-xs text-[var(--ink-soft)] mt-1 leading-relaxed">{r.description}</p>}
                  </a>
                ))}
              </div>
            </Section>
          </article>
        )}

        {!result && !loading && !error && (
          <div className="py-16 text-center">
            <p className="text-sm text-[var(--ink-faint)] italic">Awaiting submission.</p>
          </div>
        )}

        <footer className="mt-16 pt-6 border-t border-[var(--rule)] font-mono text-xs text-[var(--ink-faint)] text-center">
          Shreya Shankar · Generated by an automated multi-agent reviewer · Not a substitute for peer review
        </footer>
      </div>
    </div>
  )
}
