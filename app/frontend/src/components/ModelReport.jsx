import { useState, useEffect } from 'react'

// ── Helpers ───────────────────────────────────────────────────────────────────

function pct(v, decimals = 1) {
  if (v == null) return '—'
  return `${(v * 100).toFixed(decimals)}%`
}

function pp(v) {
  if (v == null) return '—'
  const sign = v >= 0 ? '+' : ''
  return `${sign}${(v * 100).toFixed(1)}pp`
}

// ── Hero section ──────────────────────────────────────────────────────────────

function Hero({ data }) {
  const { overall_accuracy, total_games, n_seasons, baseline_seed, baseline_adjEM } = data
  const vsSeeds  = overall_accuracy - baseline_seed
  const vsAdjEM  = overall_accuracy - baseline_adjEM

  return (
    <div className="mr-hero">
      <div className="mr-hero-eyebrow mono">LEAVE-YEAR-OUT CROSS-VALIDATION · 2002–2025</div>
      <div className="mr-hero-headline">
        <span className="mr-hero-number display">{pct(overall_accuracy, 1)}</span>
        <span className="mr-hero-label display">overall accuracy</span>
      </div>
      <div className="mr-hero-sub mono">
        {total_games.toLocaleString()} games · {n_seasons} seasons · model trained on all other years, tested on each held-out season
      </div>
      <div className="mr-hero-pills">
        <div className="mr-hero-pill">
          <span className="mr-hero-pill-val positive mono">{pp(vsSeeds)}</span>
          <span className="mr-hero-pill-label mono">vs seed baseline ({pct(baseline_seed, 0)})</span>
        </div>
        <div className="mr-hero-pill">
          <span className="mr-hero-pill-val positive mono">{pp(vsAdjEM)}</span>
          <span className="mr-hero-pill-label mono">vs AdjEM-only ({pct(baseline_adjEM, 0)})</span>
        </div>
        <div className="mr-hero-pill">
          <span className="mr-hero-pill-val mono">{total_games.toLocaleString()}</span>
          <span className="mr-hero-pill-label mono">games evaluated</span>
        </div>
        <div className="mr-hero-pill">
          <span className="mr-hero-pill-val mono">{n_seasons}</span>
          <span className="mr-hero-pill-label mono">seasons</span>
        </div>
      </div>
    </div>
  )
}

// ── Baseline comparison ───────────────────────────────────────────────────────

function BaselineComparison({ data }) {
  const { overall_accuracy, baseline_seed, baseline_adjEM } = data
  const maxAcc = overall_accuracy

  return (
    <div className="mr-card">
      <div className="mr-baseline-grid">
        {[
          { label: 'SEED-ONLY BASELINE', acc: baseline_seed,    note: 'pick higher seed every game' },
          { label: 'ADJEM-ONLY BASELINE', acc: baseline_adjEM,  note: 'pick team with better efficiency margin' },
          { label: 'THIS MODEL',          acc: overall_accuracy, note: 'full feature set · LYO evaluation', highlight: true },
        ].map(({ label, acc, note, highlight }) => (
          <div key={label} className={`mr-baseline-item${highlight ? ' highlight' : ''}`}>
            <div className="mr-baseline-name mono">{label}</div>
            <div className="mr-baseline-acc mono">{pct(acc, 1)}</div>
            <div className="mr-baseline-bar-track">
              <div className="mr-baseline-bar-fill" style={{ width: `${(acc / maxAcc) * 100}%` }} />
            </div>
            <div className="mr-baseline-delta mono" style={{ color: highlight ? 'var(--gold-bright)' : 'var(--cream-dim)', opacity: highlight ? 1 : 0.4 }}>
              {highlight ? `+${((acc - baseline_seed) * 100).toFixed(1)}pp over seed baseline` : note}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Round-by-round breakdown ──────────────────────────────────────────────────

function RoundBreakdown({ rounds }) {
  if (!rounds?.length) return null
  const maxAcc = Math.max(...rounds.map(r => r.accuracy ?? 0))

  return (
    <div className="mr-card">
      <div className="mr-round-rows">
        {rounds.map(r => (
          <div key={r.round_name} className="mr-round-row">
            <div className="mr-round-label mono">{r.round_name}</div>
            <div className="mr-round-bar-track">
              <div className="mr-round-bar-fill"
                style={{ width: r.accuracy ? `${(r.accuracy / Math.max(maxAcc, 0.85)) * 100}%` : '0%' }}
              />
            </div>
            <div className="mr-round-pct mono">{pct(r.accuracy, 1)}</div>
            <div className="mr-round-n mono">{r.correct}/{r.total} games</div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Year-by-year SVG chart ────────────────────────────────────────────────────

function YearChart({ years }) {
  if (!years?.length) return null

  const W = 920, H = 230, ML = 36, MR = 12, MT = 16, MB = 36
  const cW = W - ML - MR
  const cH = H - MT - MB
  const N  = years.length

  const minY = 0.50, maxY = 0.85
  const range = maxY - minY

  const xOf = i  => ML + (i + 0.5) * (cW / N)
  const yOf = v  => MT + cH - ((v - minY) / range) * cH

  const meanAcc = years.reduce((s, d) => s + d.accuracy, 0) / years.length
  const meanY   = yOf(meanAcc)

  const bW     = Math.max(4, cW / N - 5)
  const seedBW = Math.max(2, bW * 0.45)

  return (
    <div className="mr-card">
      <div className="mr-year-legend">
        <div className="mr-year-legend-item">
          <div className="mr-year-legend-dot" style={{ background: 'rgba(201,168,76,0.75)' }} />
          <span className="mono">Model accuracy</span>
        </div>
        <div className="mr-year-legend-item">
          <div className="mr-year-legend-dot" style={{ background: 'rgba(96,165,250,0.4)' }} />
          <span className="mono">Seed-only baseline</span>
        </div>
        <div className="mr-year-legend-item">
          <div className="mr-year-legend-dot" style={{ background: 'rgba(248,113,113,0.55)', border: '1px solid rgba(248,113,113,0.4)' }} />
          <span className="mono">Chaos year (below average)</span>
        </div>
      </div>

      <div className="mr-year-chart-wrap">
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block', minWidth: 480 }}>
          {/* Y axis grid + labels */}
          {[0.55, 0.60, 0.65, 0.70, 0.75, 0.80].map(v => (
            <g key={v}>
              <line x1={ML} x2={W - MR} y1={yOf(v)} y2={yOf(v)}
                stroke="rgba(255,255,255,0.04)" strokeWidth={1} />
              <text x={ML - 3} y={yOf(v) + 3} textAnchor="end"
                fill="rgba(255,255,255,0.25)" fontSize={8} fontFamily="monospace">
                {(v * 100).toFixed(0)}
              </text>
            </g>
          ))}

          {/* Mean line */}
          <line x1={ML} x2={W - MR} y1={meanY} y2={meanY}
            stroke="rgba(201,168,76,0.25)" strokeWidth={1} strokeDasharray="5 4" />
          <text x={W - MR + 2} y={meanY + 3}
            fill="rgba(201,168,76,0.4)" fontSize={7} fontFamily="monospace">
            avg
          </text>

          {years.map((d, i) => {
            const x       = xOf(i)
            const yModel  = yOf(d.accuracy)
            const ySeed   = yOf(d.seed_accuracy ?? 0.58)
            const bHModel = MT + cH - yModel
            const bHSeed  = MT + cH - ySeed
            const chaos   = d.chaos
            const strong  = d.strong

            const modelColor = chaos
              ? 'rgba(248,113,113,0.65)'
              : strong
              ? 'rgba(201,168,76,0.95)'
              : 'rgba(201,168,76,0.6)'

            return (
              <g key={d.year}>
                {/* Seed bar (behind) */}
                <rect x={x - bW / 2} y={ySeed} width={bW} height={bHSeed}
                  fill="rgba(96,165,250,0.18)" rx={1} />

                {/* Model bar (front) */}
                <rect x={x - seedBW / 2} y={yModel} width={seedBW} height={bHModel}
                  fill={modelColor} rx={1} opacity={0.9} />

                {/* Year label */}
                <text x={x} y={H - 6} textAnchor="middle"
                  fill={chaos ? '#f87171' : 'rgba(255,255,255,0.3)'}
                  fontSize={8} fontFamily="monospace">
                  {String(d.year).slice(2)}
                </text>

                {/* Chaos / strong label above bar */}
                {(chaos || strong) && (
                  <text x={x} y={yModel - 4} textAnchor="middle"
                    fill={chaos ? '#f87171' : '#c9a84c'}
                    fontSize={7} fontFamily="monospace" opacity={0.7}>
                    {chaos ? '●' : '★'}
                  </text>
                )}

                <title>{`${d.year}: model ${pct(d.accuracy)} | seed ${pct(d.seed_accuracy)} | upsets ${pct(d.upset_rate)}`}</title>
              </g>
            )
          })}
        </svg>
      </div>

      {/* Hover/legend note */}
      <div style={{ fontSize: '0.58rem', color: 'var(--cream-dim)', opacity: 0.35, marginTop: 8 }} className="mono">
        ★ strong year (model {">"} avg+5pp)  ·  ● chaos year (model {"<"} avg−5pp or high upsets)  ·  hover bars for details
      </div>
    </div>
  )
}

// ── Best / Worst calls table ──────────────────────────────────────────────────

function CallsTable({ games, type }) {
  const isLock = type === 'lock'
  const title  = isLock ? '🔒 THE LOCKS — Highest-Confidence Correct Calls' : '💥 THE MISSES — Highest-Confidence Wrong Calls'
  const cls    = isLock ? 'locks' : 'misses'
  const confCls = isLock ? 'mr-calls-conf-lock' : 'mr-calls-conf-miss'

  return (
    <div className="mr-calls-panel">
      <div className={`mr-calls-panel-title mono ${cls}`}>{title}</div>
      <div className="mr-calls-table-wrap">
        <table className="mr-calls-table">
          <thead>
            <tr>
              <th className="mono">Yr</th>
              <th className="mono">Rd</th>
              <th className="mono">Model pick</th>
              <th className="mono">Opponent</th>
              <th className="mono">Conf.</th>
            </tr>
          </thead>
          <tbody>
            {games.map((g, i) => {
              const loser = g.model_winner === g.team1 ? g.team2 : g.team1
              return (
                <tr key={i}>
                  <td className="mono" style={{ opacity: 0.5 }}>{g.year}</td>
                  <td className="mono" style={{ opacity: 0.5 }}>{g.round_name}</td>
                  <td className={`mr-calls-winner`}>{g.model_winner}</td>
                  <td className="mr-calls-loser mono">{loser}</td>
                  <td className={`${confCls} mono`}>{pct(g.confidence, 1)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Calibration strip ─────────────────────────────────────────────────────────

function CalibrationStrip({ buckets }) {
  if (!buckets?.length) return null

  return (
    <div className="mr-card">
      <div className="mr-cal-grid">
        {buckets.map((b, i) => {
          const label = `${(b.bucket_lo * 100).toFixed(0)}–${(b.bucket_hi * 100).toFixed(0)}%`
          const rate  = b.actual
          const expected = b.predicted
          return (
            <div key={i} className="mr-cal-bucket">
              <div className="mr-cal-bucket-label mono">{label}</div>
              <div className="mr-cal-bar-track">
                <div className="mr-cal-bar-fill" style={{ width: `${Math.round(rate * 100)}%` }} />
                <div className="mr-cal-expected" style={{ left: `${Math.round(expected * 100)}%` }} />
              </div>
              <div className="mr-cal-stat mono">{pct(rate)}</div>
              <div className="mr-cal-n mono">n={b.n} · exp {pct(expected)}</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ── Seed accuracy ─────────────────────────────────────────────────────────────

function SeedAccuracy({ rows }) {
  if (!rows?.length) return null

  // Group by seed_diff, average across rounds
  const grouped = {}
  rows.forEach(r => {
    const key = `${r.seed_diff}`
    if (!grouped[key]) grouped[key] = { seed_diff: r.seed_diff, n: 0, actual_sum: 0, model_sum: 0 }
    grouped[key].n            += r.n
    grouped[key].actual_sum   += r.actual_upset_rate * r.n
    grouped[key].model_sum    += r.model_upset_rate * r.n
  })

  const sorted = Object.values(grouped).sort((a, b) => a.seed_diff - b.seed_diff)

  return (
    <div className="mr-seed-table-wrap">
      <table className="mr-seed-table">
        <thead>
          <tr>
            <th className="mono">Seed gap</th>
            <th className="mono">Games</th>
            <th className="mono">Actual upset %</th>
            <th className="mono">Model upset %</th>
            <th className="mono">Model edge</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map(r => {
            const actual = r.actual_sum / r.n
            const model  = r.model_sum  / r.n
            const delta  = model - actual
            return (
              <tr key={r.seed_diff}>
                <td className="mono" style={{ color: 'var(--cream)' }}>±{r.seed_diff}</td>
                <td className="mono" style={{ opacity: 0.5 }}>{r.n}</td>
                <td>
                  <span className="mr-seed-acc-bar-track">
                    <span className="mr-seed-acc-bar-fill" style={{ display: 'block', width: `${Math.min(actual * 400, 100)}%` }} />
                  </span>
                  <span className="mono">{pct(actual)}</span>
                </td>
                <td className="mono">{pct(model)}</td>
                <td className={`mono ${Math.abs(delta) < 0.02 ? '' : delta > 0 ? 'mr-seed-acc-over' : 'mr-seed-acc-under'}`}>
                  {delta >= 0 ? '+' : ''}{pct(delta)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

// ── Main ──────────────────────────────────────────────────────────────────────

export default function ModelReport() {
  const [data,    setData]    = useState(null)
  const [loading, setLoading] = useState(true)
  const [error,   setError]   = useState(null)

  useEffect(() => {
    fetch('/api/model-report')
      .then(r => r.ok ? r.json() : r.json().then(e => { throw new Error(e.detail || r.statusText) }))
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  if (loading) return (
    <div className="mr-viewer">
      <div className="mr-loading"><div className="mr-spinner" /><span className="mono">Building model report…</span></div>
    </div>
  )

  if (error) return (
    <div className="mr-viewer"><div className="mr-error mono">{error}</div></div>
  )

  if (!data) return null

  return (
    <div className="mr-viewer">

      <Hero data={data} />

      {/* Baselines */}
      <div className="mr-section">
        <div className="mr-section-title display">Baseline Comparison</div>
        <div className="mr-section-sub mono">
          How much does the full feature set add over simpler heuristics?
        </div>
        <BaselineComparison data={data} />
      </div>

      {/* Round breakdown */}
      <div className="mr-section">
        <div className="mr-section-title display">Accuracy by Round</div>
        <div className="mr-section-sub mono">
          Leave-year-out accuracy for each tournament stage · aggregated across all {data.n_seasons} seasons
        </div>
        <RoundBreakdown rounds={data.round_accuracy} />
      </div>

      {/* Year chart */}
      <div className="mr-section">
        <div className="mr-section-title display">Year-by-Year Performance</div>
        <div className="mr-section-sub mono">
          Model accuracy (gold) vs seed-only baseline (blue) per season · chaos years in red
        </div>
        <YearChart years={data.yearly_accuracy} />
      </div>

      {/* Best / Worst calls */}
      <div className="mr-section">
        <div className="mr-section-title display">Best & Worst Calls</div>
        <div className="mr-section-sub mono">
          Top 15 most confident correct predictions · and top 15 most confident wrong ones
        </div>
        <div className="mr-calls-grid">
          <CallsTable games={data.best_calls}  type="lock" />
          <CallsTable games={data.worst_calls} type="miss" />
        </div>
      </div>

      {/* Calibration */}
      {data.calibration?.length > 0 && (
        <div className="mr-section">
          <div className="mr-section-title display">Confidence Calibration</div>
          <div className="mr-section-sub mono">
            When the model says 70%, does it win 70% of the time? White tick = expected rate · bar = actual rate
          </div>
          <CalibrationStrip buckets={data.calibration} />
        </div>
      )}

      {/* Seed accuracy */}
      {data.upset_by_seed?.length > 0 && (
        <div className="mr-section">
          <div className="mr-section-title display">Upset Rate by Seed Gap</div>
          <div className="mr-section-sub mono">
            How often does the lower seed actually win? Model vs historical actual — across all rounds and years
          </div>
          <SeedAccuracy rows={data.upset_by_seed} />
        </div>
      )}

    </div>
  )
}
