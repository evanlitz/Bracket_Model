import { useState, useEffect } from 'react'

// ── Colour palette ─────────────────────────────────────────────────────────────
const PALETTE = [
  '#c9a84c','#3b82f6','#22c55e','#f87171',
  '#a78bfa','#fb923c','#38bdf8','#f472b6',
  '#84cc16','#e879f9','#fbbf24','#67e8f9',
]

const ERA_COLORS = { '2002–2010': '#3b82f6', '2011–2017': '#c9a84c', '2018–2025': '#22c55e' }

// ── Tiny SVG helpers ──────────────────────────────────────────────────────────

function fmt1(v)   { return v == null ? '—' : (v * 100).toFixed(1) + '%' }
function fmtN(v,d=3) { return v == null ? '—' : v.toFixed(d) }

// ── Section wrapper ───────────────────────────────────────────────────────────

function Section({ title, sub, children }) {
  return (
    <div className="an-section">
      <div className="an-section-title">{title}</div>
      {sub && <div className="an-section-sub mono">{sub}</div>}
      {children}
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// 1. YEARLY ACCURACY — bar chart per year
// ═══════════════════════════════════════════════════════════════════════════════

function YearlyAccuracyChart({ data }) {
  const [metric, setMetric] = useState('accuracy')

  const METRICS = [
    { key: 'accuracy',    label: 'Accuracy',     color: '#c9a84c', invert: false },
    { key: 'brier',       label: 'Brier Score',  color: '#f87171', invert: true  },
    { key: 'upset_rate',  label: 'Upset Rate',   color: '#a78bfa', invert: false },
  ]
  const met = METRICS.find(m => m.key === metric)

  const valid = data.filter(d => d[metric] != null)
  if (!valid.length) return <div className="an-no-data">No data</div>

  const vals = valid.map(d => d[metric])
  const minV = Math.min(...vals)
  const maxV = Math.max(...vals)
  const range = maxV - minV || 0.01
  const mean  = vals.reduce((a, b) => a + b, 0) / vals.length

  // SVG
  const W = 900, H = 220, ML = 36, MR = 12, MT = 12, MB = 28
  const cW = W - ML - MR
  const cH = H - MT - MB
  const bW  = Math.max(1, cW / valid.length - 3)

  const xOf  = i   => ML + (i + 0.5) * (cW / valid.length)
  const yOf  = v   => MT + cH - ((v - minV) / range) * cH
  const meanY = yOf(mean)

  return (
    <div className="an-chart-card">
      <div className="an-chart-top">
        <div className="an-chart-label">{met.label} by Year  ·  mean {(mean * 100).toFixed(1)}%</div>
        <div className="an-metric-btns">
          {METRICS.map(m => (
            <button key={m.key}
              className={`an-metric-btn${metric === m.key ? ' active' : ''}`}
              onClick={() => setMetric(m.key)}
            >{m.label}</button>
          ))}
        </div>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
        {/* Mean line */}
        <line x1={ML} x2={W - MR} y1={meanY} y2={meanY}
          stroke="rgba(255,255,255,0.15)" strokeWidth={1} strokeDasharray="4 4" />

        {valid.map((d, i) => {
          const x  = xOf(i) - bW / 2
          const y  = yOf(d[metric])
          const bH = MT + cH - y
          const isHigh = met.invert ? d[metric] < mean : d[metric] > mean
          const color  = isHigh ? met.color : 'rgba(201,168,76,0.25)'
          return (
            <g key={d.year}>
              <rect x={x} y={y} width={bW} height={bH} fill={color} rx={1} opacity={0.85} />
              {/* Year label — every 3 years */}
              {i % 3 === 0 && (
                <text x={xOf(i)} y={H - 4} textAnchor="middle"
                  fill="rgba(255,255,255,0.35)" fontSize={9} fontFamily="monospace">
                  {d.year}
                </text>
              )}
            </g>
          )
        })}

        {/* Y axis ticks */}
        {[minV, mean, maxV].map((v, i) => (
          <text key={i} x={ML - 3} y={yOf(v) + 3} textAnchor="end"
            fill="rgba(255,255,255,0.3)" fontSize={8} fontFamily="monospace">
            {(v * 100).toFixed(0)}%
          </text>
        ))}
      </svg>

      {/* Stat row */}
      <div className="an-year-stats">
        {valid.map(d => (
          <div key={d.year} className="an-year-cell" title={`${d.year}: acc ${fmt1(d.accuracy)}, Brier ${fmtN(d.brier)}, upsets ${fmt1(d.upset_rate)}`}>
            <div className="an-year-cell-yr mono">{d.year}</div>
            <div className="an-year-cell-val mono"
              style={{ color: d[metric] != null && d[metric] > mean === !met.invert ? met.color : 'var(--cream-dim)' }}>
              {d[metric] != null ? (d[metric] * 100).toFixed(0) + '%' : '—'}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// 2. CALIBRATION CURVE
// ═══════════════════════════════════════════════════════════════════════════════

function CalibrationChart({ data }) {
  if (!data?.length) return <div className="an-no-data">No calibration data</div>

  const W = 500, H = 320, M = 48
  const cW = W - 2 * M, cH = H - 2 * M

  const xOf = v => M + (v - 0.5) * cW / 0.5   // 0.5 → 1.0
  const yOf = v => M + (1 - v) * cH             // 0 → 1

  const linePath = data.map((d, i) =>
    `${i === 0 ? 'M' : 'L'}${xOf(d.predicted).toFixed(1)},${yOf(d.actual).toFixed(1)}`
  ).join(' ')

  // Perfect calibration line
  const perfectPath = `M${xOf(0.5)},${yOf(0.5)} L${xOf(1.0)},${yOf(1.0)}`

  // Axis ticks
  const ticks = [0.5, 0.6, 0.7, 0.8, 0.9, 1.0]

  return (
    <div className="an-chart-card">
      <div className="an-chart-label">
        Model Calibration — Predicted Confidence vs Actual Win Rate
      </div>
      <div className="an-chart-sub mono">
        Perfect calibration = diagonal line · Curve above = under-confident · Below = over-confident
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block', maxWidth: 480 }}>
        {/* Grid */}
        {ticks.map(t => (
          <g key={t}>
            <line x1={xOf(t)} x2={xOf(t)} y1={M} y2={M + cH}
              stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
            <line x1={M} x2={M + cW} y1={yOf(t)} y2={yOf(t)}
              stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
            <text x={xOf(t)} y={M + cH + 14} textAnchor="middle"
              fill="rgba(255,255,255,0.3)" fontSize={9} fontFamily="monospace">
              {(t * 100).toFixed(0)}%
            </text>
            <text x={M - 6} y={yOf(t) + 3} textAnchor="end"
              fill="rgba(255,255,255,0.3)" fontSize={9} fontFamily="monospace">
              {(t * 100).toFixed(0)}%
            </text>
          </g>
        ))}

        {/* Axis labels */}
        <text x={M + cW / 2} y={H - 4} textAnchor="middle"
          fill="rgba(255,255,255,0.4)" fontSize={10} fontFamily="monospace">
          PREDICTED CONFIDENCE
        </text>
        <text
          transform={`rotate(-90) translate(${-(M + cH / 2)},${13})`}
          textAnchor="middle" fill="rgba(255,255,255,0.4)" fontSize={10} fontFamily="monospace">
          ACTUAL WIN RATE
        </text>

        {/* Perfect calibration */}
        <path d={perfectPath} fill="none"
          stroke="rgba(255,255,255,0.2)" strokeWidth={1.5} strokeDasharray="5 4" />

        {/* Confidence band (±5%) */}
        <path
          d={`M${xOf(0.5)},${yOf(0.55)} L${xOf(1.0)},${yOf(1.05)} L${xOf(1.0)},${yOf(0.95)} L${xOf(0.5)},${yOf(0.45)} Z`}
          fill="rgba(255,255,255,0.03)"
        />

        {/* Actual calibration line */}
        <path d={linePath} fill="none"
          stroke="#c9a84c" strokeWidth={2.5} strokeLinejoin="round" />

        {/* Data points */}
        {data.map((d, i) => (
          <g key={i}>
            <circle cx={xOf(d.predicted)} cy={yOf(d.actual)} r={5}
              fill="#c9a84c" stroke="var(--bg)" strokeWidth={2} />
            <title>{`Predicted: ${(d.predicted * 100).toFixed(1)}% → Actual: ${(d.actual * 100).toFixed(1)}% (n=${d.n})`}</title>
          </g>
        ))}
      </svg>

      {/* Data table below */}
      <div className="an-cal-table-wrap">
        <table className="an-cal-table">
          <thead>
            <tr>
              <th>Confidence</th>
              <th>Predicted</th>
              <th>Actual</th>
              <th>Δ</th>
              <th>n</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d, i) => {
              const delta = d.actual - d.predicted
              return (
                <tr key={i}>
                  <td className="mono">{(d.bucket_lo * 100).toFixed(0)}–{(d.bucket_hi * 100).toFixed(0)}%</td>
                  <td className="mono">{(d.predicted * 100).toFixed(1)}%</td>
                  <td className="mono">{(d.actual * 100).toFixed(1)}%</td>
                  <td className="mono" style={{ color: delta > 0.02 ? '#22c55e' : delta < -0.02 ? '#f87171' : 'var(--cream-dim)' }}>
                    {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
                  </td>
                  <td className="mono" style={{ opacity: 0.5 }}>{d.n}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// 3. YEARLY FEATURE CORRELATION — line chart per feature over time
// ═══════════════════════════════════════════════════════════════════════════════

function YearlyFeatureChart({ data, tracked }) {
  const [selected, setSelected] = useState(
    tracked.slice(0, 4).map(f => f.feature)
  )

  const years = Object.keys(data).map(Number).sort()
  if (!years.length) return <div className="an-no-data">No data</div>

  function toggle(feat) {
    setSelected(prev =>
      prev.includes(feat)
        ? prev.filter(f => f !== feat)
        : [...prev, feat]
    )
  }

  const W = 900, H = 240, ML = 44, MR = 16, MT = 16, MB = 28
  const cW = W - ML - MR, cH = H - MT - MB

  const xOf = i   => ML + (i / (years.length - 1)) * cW
  const yOf = v   => MT + cH / 2 - v * (cH / 2) * 2.2  // centred on 0, ±1 at edges

  const zeroY = yOf(0)

  return (
    <div className="an-chart-card">
      <div className="an-chart-label">Feature Correlation with Win/Loss · By Year</div>
      <div className="an-chart-sub mono">Click features to toggle · Positive = favours team1 · Trend shows if signal is growing or fading</div>

      {/* Feature toggles */}
      <div className="an-feature-toggles">
        {tracked.map((f, fi) => {
          const on = selected.includes(f.feature)
          return (
            <button key={f.feature}
              className={`an-toggle-btn${on ? ' on' : ''}`}
              style={{ '--btn-color': PALETTE[fi % PALETTE.length] }}
              onClick={() => toggle(f.feature)}
            >
              <span className="an-toggle-dot" style={{ background: on ? PALETTE[fi % PALETTE.length] : 'transparent', borderColor: PALETTE[fi % PALETTE.length] }} />
              {f.label}
            </button>
          )
        })}
      </div>

      <svg viewBox={`0 0 ${W} ${H}`} width="100%" style={{ display: 'block' }}>
        {/* Zero line */}
        <line x1={ML} x2={W - MR} y1={zeroY} y2={zeroY}
          stroke="rgba(255,255,255,0.18)" strokeWidth={1} />

        {/* Y axis labels */}
        {[-0.4, -0.2, 0, 0.2, 0.4].map(v => (
          <g key={v}>
            <line x1={ML} x2={W - MR} y1={yOf(v)} y2={yOf(v)}
              stroke="rgba(255,255,255,0.04)" strokeWidth={1} />
            <text x={ML - 4} y={yOf(v) + 3} textAnchor="end"
              fill="rgba(255,255,255,0.25)" fontSize={8} fontFamily="monospace">
              {v >= 0 ? '+' : ''}{v.toFixed(1)}
            </text>
          </g>
        ))}

        {/* Year markers */}
        {years.filter((_, i) => i % 4 === 0).map(yr => {
          const i = years.indexOf(yr)
          return (
            <g key={yr}>
              <line x1={xOf(i)} x2={xOf(i)} y1={MT} y2={MT + cH}
                stroke="rgba(255,255,255,0.05)" strokeWidth={1} />
              <text x={xOf(i)} y={H - 6} textAnchor="middle"
                fill="rgba(255,255,255,0.3)" fontSize={9} fontFamily="monospace">
                {yr}
              </text>
            </g>
          )
        })}

        {/* Feature lines */}
        {tracked.map((f, fi) => {
          if (!selected.includes(f.feature)) return null
          const color = PALETTE[fi % PALETTE.length]
          const points = years.map((yr, i) => {
            const yrData = data[String(yr)] || []
            const entry  = yrData.find(e => e.feature === f.feature)
            return (entry && entry.correlation != null) ? { x: xOf(i), y: yOf(entry.correlation), v: entry.correlation } : null
          })

          const segments = []
          let cur = []
          points.forEach(p => {
            if (p) cur.push(p)
            else if (cur.length) { segments.push(cur); cur = [] }
          })
          if (cur.length) segments.push(cur)

          return (
            <g key={f.feature}>
              {segments.map((seg, si) => (
                <path key={si}
                  d={seg.map((p, pi) => `${pi === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')}
                  fill="none" stroke={color} strokeWidth={2} opacity={0.8}
                />
              ))}
              {points.map((p, pi) => p && (
                <circle key={pi} cx={p.x} cy={p.y} r={3}
                  fill={color} stroke="var(--bg)" strokeWidth={1.5} opacity={0.8}>
                  <title>{`${f.label} ${years[pi]}: ${p.v != null ? (p.v >= 0 ? '+' : '') + p.v.toFixed(3) : 'n/a'}`}</title>
                </circle>
              ))}
            </g>
          )
        })}
      </svg>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// 4. ERA COMPARISON
// ═══════════════════════════════════════════════════════════════════════════════

function EraComparisonChart({ data }) {
  if (!data?.length) return <div className="an-no-data">No era data</div>

  // Collect union of top features across eras
  const featSet = new Set()
  data.forEach(e => e.top_features.slice(0, 10).forEach(f => featSet.add(f.feature)))
  const feats = [...featSet]

  // Build lookup: era → feature → correlation
  const lkp = {}
  data.forEach(e => {
    lkp[e.era] = {}
    e.top_features.forEach(f => { lkp[e.era][f.feature] = f.correlation })
  })

  // Feature labels
  const labels = {}
  data.forEach(e => e.top_features.forEach(f => { labels[f.feature] = f.label }))

  // Sort by max abs correlation across eras
  const sorted = [...feats].sort((a, b) => {
    const ma = Math.max(...data.map(e => Math.abs(lkp[e.era][a] || 0)))
    const mb = Math.max(...data.map(e => Math.abs(lkp[e.era][b] || 0)))
    return mb - ma
  }).slice(0, 12)

  const maxCorr = 0.45

  return (
    <div className="an-chart-card">
      <div className="an-chart-label">Feature Importance Across Eras — Correlation with Outcome</div>
      <div className="an-chart-sub mono">How predictive power of each feature has shifted across the history of the model</div>

      {/* Legend */}
      <div className="an-era-legend">
        {data.map(e => (
          <span key={e.era} className="an-era-legend-item">
            <span className="an-era-dot" style={{ background: ERA_COLORS[e.era] }} />
            {e.era}  ·  {e.n_games}g
          </span>
        ))}
      </div>

      <div className="an-era-grid">
        {sorted.map(feat => (
          <div key={feat} className="an-era-row">
            <div className="an-era-feat-label" title={labels[feat]}>{labels[feat]}</div>
            {data.map(e => {
              const v    = lkp[e.era][feat]
              const pct  = v != null ? (Math.abs(v) / maxCorr) * 100 : 0
              const isNeg = v != null && v < 0
              return (
                <div key={e.era} className="an-era-bar-wrap" title={v != null ? `${e.era}: ${v >= 0 ? '+' : ''}${v.toFixed(3)}` : 'n/a'}>
                  <div
                    className="an-era-bar"
                    style={{
                      width: `${pct}%`,
                      background: isNeg
                        ? `linear-gradient(90deg, #9b1c1c, #f87171)`
                        : `linear-gradient(90deg, ${ERA_COLORS[e.era]}55, ${ERA_COLORS[e.era]})`,
                    }}
                  />
                  <span className="an-era-val mono" style={{ color: v == null ? 'transparent' : isNeg ? '#f87171' : ERA_COLORS[e.era] }}>
                    {v != null ? (v >= 0 ? '+' : '') + v.toFixed(3) : ''}
                  </span>
                </div>
              )
            })}
          </div>
        ))}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// 5. UPSET ANALYSIS
// ═══════════════════════════════════════════════════════════════════════════════

function UpsetAnalysis({ data }) {
  if (!data) return <div className="an-no-data">No upset data</div>
  const { by_seed_matchup, upset_feature_correlation, non_upset_feature_correlation,
          n_upsets, n_non_upsets } = data

  // Combine upset vs non-upset correlations for comparison
  const uMap  = {}; (upset_feature_correlation || []).forEach(f => { uMap[f.feature] = f })
  const nuMap = {}; (non_upset_feature_correlation || []).forEach(f => { nuMap[f.feature] = f })
  const allFeats = [...new Set([
    ...(upset_feature_correlation || []).slice(0, 12).map(f => f.feature),
    ...(non_upset_feature_correlation || []).slice(0, 12).map(f => f.feature),
  ])]

  const maxV = 0.45

  return (
    <div className="an-chart-card">
      <div className="an-chart-label">Upset Analysis</div>
      <div className="an-chart-sub mono">
        {n_upsets} upsets · {n_non_upsets} non-upsets · which features predict upsets vs expected outcomes?
      </div>

      {/* Seed matchup table */}
      {by_seed_matchup?.length > 0 && (
        <div className="an-upset-matchup-wrap">
          <div className="an-sub-label">Upset Rate by Seed Differential</div>
          <table className="an-upset-table">
            <thead>
              <tr>
                <th>Round</th>
                <th>Seed Gap</th>
                <th>Games</th>
                <th>Actual Upset %</th>
                <th>Model Upset %</th>
                <th>Δ</th>
              </tr>
            </thead>
            <tbody>
              {by_seed_matchup.map((m, i) => {
                const delta = m.model_upset_rate - m.actual_upset_rate
                return (
                  <tr key={i}>
                    <td className="mono">{m.round}</td>
                    <td className="mono">{m.seed_diff}</td>
                    <td className="mono" style={{ opacity: 0.55 }}>{m.n}</td>
                    <td className="mono">{(m.actual_upset_rate * 100).toFixed(1)}%</td>
                    <td className="mono">{(m.model_upset_rate * 100).toFixed(1)}%</td>
                    <td className="mono" style={{ color: delta > 0.02 ? '#f87171' : delta < -0.02 ? '#22c55e' : 'var(--cream-dim)' }}>
                      {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Feature comparison: upset vs normal games */}
      <div className="an-sub-label" style={{ marginTop: 18 }}>Feature Correlation: Upsets vs Normal Outcomes</div>
      <div className="an-upset-legend">
        <span><span className="an-era-dot" style={{ background: '#f87171' }} />Upset games</span>
        <span><span className="an-era-dot" style={{ background: '#3b82f6' }} />Normal games</span>
      </div>
      <div className="an-era-grid">
        {allFeats.map(feat => {
          const u  = uMap[feat]
          const nu = nuMap[feat]
          const label = u?.label || nu?.label || feat
          return (
            <div key={feat} className="an-era-row">
              <div className="an-era-feat-label" title={label}>{label}</div>
              {[{ d: u, color: '#f87171' }, { d: nu, color: '#3b82f6' }].map(({ d, color }, i) => {
                const v   = d?.correlation
                const pct = v != null ? (Math.abs(v) / maxV) * 100 : 0
                return (
                  <div key={i} className="an-era-bar-wrap" title={v != null ? (v >= 0 ? '+' : '') + v.toFixed(3) : 'n/a'}>
                    <div className="an-era-bar"
                      style={{ width: `${pct}%`, background: v != null && v < 0 ? 'linear-gradient(90deg,#9b1c1c,#f87171)' : `linear-gradient(90deg,${color}44,${color})` }} />
                    <span className="an-era-val mono" style={{ color: v == null ? 'transparent' : v < 0 ? '#f87171' : color }}>
                      {v != null ? (v >= 0 ? '+' : '') + v.toFixed(3) : ''}
                    </span>
                  </div>
                )
              })}
            </div>
          )
        })}
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// 6. FEATURE REDUNDANCY HEATMAP
// ═══════════════════════════════════════════════════════════════════════════════

function RedundancyHeatmap({ data }) {
  if (!data?.features?.length) return <div className="an-no-data">No redundancy data</div>
  const { features, labels, matrix } = data
  const N = features.length

  // colour: -1=blue, 0=transparent, +1=gold
  function cellColor(v) {
    const a = Math.abs(v)
    if (a < 0.1) return 'rgba(255,255,255,0.03)'
    if (v > 0) return `rgba(201,168,76,${Math.min(a, 1) * 0.85})`
    return `rgba(248,113,113,${Math.min(a, 1) * 0.85})`
  }

  return (
    <div className="an-chart-card">
      <div className="an-chart-label">Feature Redundancy — Pairwise Correlation Matrix</div>
      <div className="an-chart-sub mono">
        Gold = positive correlation · Red = inverse · Dark = independent · Highly correlated features carry redundant signal
      </div>
      <div className="an-heatmap-scroll">
        <table className="an-heatmap-table">
          <thead>
            <tr>
              <th className="an-hm-corner" />
              {labels.map((l, i) => (
                <th key={i} className="an-hm-col-head" title={l}>
                  <span className="an-hm-rotated">{l}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {matrix.map((row, ri) => (
              <tr key={ri}>
                <td className="an-hm-row-label" title={labels[ri]}>
                  {labels[ri]}
                </td>
                {row.map((v, ci) => (
                  <td key={ci}
                    className="an-hm-cell"
                    style={{ background: cellColor(v) }}
                    title={`${labels[ri]} × ${labels[ci]}: ${v >= 0 ? '+' : ''}${v.toFixed(3)}`}
                  >
                    {ri === ci ? '' : Math.abs(v) > 0.5 ? v.toFixed(2) : ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ═══════════════════════════════════════════════════════════════════════════════
// Main AnalyticsViewer
// ═══════════════════════════════════════════════════════════════════════════════

const SECTIONS = [
  { key: 'accuracy',    label: 'Accuracy by Year'   },
  { key: 'calibration', label: 'Calibration'        },
  { key: 'yearly_fi',   label: 'Features Over Time' },
  { key: 'era',         label: 'Era Comparison'     },
  { key: 'upsets',      label: 'Upset Analysis'     },
  { key: 'redundancy',  label: 'Redundancy'         },
]

export default function AnalyticsViewer() {
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState(null)
  const [active, setActive]   = useState('accuracy')

  useEffect(() => {
    fetch('/api/analytics')
      .then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.detail || r.statusText) })
        return r.json()
      })
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  if (loading) return <div className="state-msg loading">Loading analytics…</div>
  if (error)   return (
    <div className="state-msg" style={{ color: 'var(--cream-dim)', maxWidth: 560 }}>
      <div style={{ color: 'var(--gold-bright)', marginBottom: 8 }}>Analytics not yet generated</div>
      <div className="mono" style={{ fontSize: '0.78rem' }}>
        Run from the project root:<br />
        <span style={{ color: '#22c55e' }}>python scripts/precompute_analytics.py</span>
      </div>
      <div style={{ marginTop: 8, fontSize: '0.72rem', opacity: 0.6 }}>
        Runtime ~5–10 min. Then restart the backend.
      </div>
    </div>
  )
  if (!data) return null

  return (
    <div className="an-viewer">
      {/* Header */}
      <div className="an-header">
        <div className="an-header-title display">Model Analytics</div>
        <div className="an-header-meta mono">
          {data.n_games} games · {data.n_features} features · 2002–2025 · generated {data.generated_at}
        </div>
      </div>

      {/* Section nav */}
      <div className="an-nav">
        {SECTIONS.map(s => (
          <button key={s.key}
            className={`tab-btn an-nav-btn${active === s.key ? ' active' : ''}`}
            onClick={() => setActive(s.key)}
          >{s.label}</button>
        ))}
      </div>

      {/* Content */}
      <div className="an-content">
        {active === 'accuracy' && (
          <Section
            title="Model Accuracy by Year"
            sub="Leave-year-out: model trained on all other years, evaluated on each held-out year"
          >
            <YearlyAccuracyChart data={data.yearly_accuracy} />
          </Section>
        )}

        {active === 'calibration' && (
          <Section
            title="Calibration Curve"
            sub="Does 75% confidence actually win 75% of the time? Favourite's predicted probability vs actual win rate"
          >
            <CalibrationChart data={data.calibration} />
          </Section>
        )}

        {active === 'yearly_fi' && (
          <Section
            title="Feature Importance Over Time"
            sub="Correlation of each feature with win/loss outcome, computed separately for each year 2002–2025"
          >
            <YearlyFeatureChart
              data={data.yearly_feature_correlation}
              tracked={data.tracked_features}
            />
          </Section>
        )}

        {active === 'era' && (
          <Section
            title="Era Comparison"
            sub="How feature predictive power has shifted across three eras of college basketball"
          >
            <EraComparisonChart data={data.era_comparison} />
          </Section>
        )}

        {active === 'upsets' && (
          <Section
            title="Upset Analysis"
            sub="Where does the model get fooled? Feature signatures of upsets vs expected outcomes"
          >
            <UpsetAnalysis data={data.upset_analysis} />
          </Section>
        )}

        {active === 'redundancy' && (
          <Section
            title="Feature Redundancy Matrix"
            sub="Pairwise correlation between top features — highly correlated pairs carry overlapping signal"
          >
            <RedundancyHeatmap data={data.feature_redundancy} />
          </Section>
        )}
      </div>
    </div>
  )
}
