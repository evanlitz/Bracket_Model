import { useState, useEffect } from 'react'

const ROUND_KEYS  = ['1', '2', '3', '4', '5', '6']
const ROUND_LABELS = { '1': 'R64', '2': 'R32', '3': 'S16', '4': 'E8', '5': 'F4', '6': 'NCG' }
const TRAJ_ROUNDS  = ['1', '2', '3', '4', '5'] // skip NCG (tiny sample)

const FEATURE_COLORS = [
  '#c9a84c', '#3b82f6', '#22c55e', '#f87171',
  '#a78bfa', '#fb923c', '#38bdf8', '#f472b6',
]

// ── Accuracy bar across rounds ────────────────────────────────────────────────

function AccuracyStrip({ data }) {
  const rounds = ROUND_KEYS.map(rk => ({
    key: rk,
    label: ROUND_LABELS[rk],
    cv:   data.rounds[rk]?.cv_acc,
    seed: data.rounds[rk]?.seed_acc,
    n:    data.rounds[rk]?.n_games ?? 0,
  })).filter(r => r.cv != null)

  return (
    <div className="fi-accuracy-strip">
      {rounds.map(r => {
        const delta     = r.cv - (r.seed ?? r.cv)
        const deltaSign = delta > 0.005 ? 'pos' : delta < -0.005 ? 'neg' : 'zero'
        return (
          <div key={r.key} className="fi-acc-card">
            <div className="fi-acc-round">{r.label}</div>
            <div className="fi-acc-pct mono">{(r.cv * 100).toFixed(0)}%</div>
            {r.seed != null && (
              <div className={`fi-acc-delta mono fi-delta ${deltaSign}`}>
                {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
              </div>
            )}
            <div className="fi-acc-n mono">{r.n}g</div>
            {/* bar fill */}
            <div className="fi-acc-bar-track">
              <div className="fi-acc-bar-fill" style={{ width: `${r.cv * 100}%` }} />
              {r.seed != null && (
                <div className="fi-acc-bar-seed" style={{ left: `${r.seed * 100}%` }} />
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

// ── Horizontal bar chart (permutation or correlation) ────────────────────────

function FeatureChart({ title, items, colorClass, showAll, onToggle, coverageMap }) {
  if (!items || items.length === 0) {
    return (
      <div className="fi-chart-card">
        <div className="fi-chart-title">{title}</div>
        <div className="fi-no-data">Not computed — sample too small</div>
      </div>
    )
  }

  const displayed = showAll ? items : items.slice(0, 15)
  const maxAbs = Math.max(...items.map(d => Math.abs(d.value)), 0.0001)

  return (
    <div className="fi-chart-card">
      <div className="fi-chart-title">{title}</div>

      {displayed.map((d, i) => {
        const pct      = (Math.abs(d.value) / maxAbs) * 100
        const isNeg    = d.value < 0
        const barClass = `fi-bar ${isNeg ? 'neg' : colorClass}`
        const cov      = coverageMap[d.feature]
        const lowCov   = cov !== undefined && cov < 0.80

        return (
          <div className="fi-row" key={d.feature}>
            <span className={`fi-feat-label${i < 5 ? ' top' : ''}`} title={d.label}>
              {d.label}
            </span>
            <div className="fi-bar-wrap">
              <div className={barClass} style={{ width: `${pct}%` }} />
              <span className={`fi-val${isNeg ? ' neg-val' : ''}`}>
                {d.value >= 0 ? '+' : ''}{d.value.toFixed(4)}
              </span>
              {lowCov && (
                <span className="fi-cov-flag" title={`Coverage: ${(cov * 100).toFixed(0)}%`}>*</span>
              )}
            </div>
          </div>
        )
      })}

      {items.length > 15 && (
        <button className="fi-show-toggle" onClick={onToggle}>
          {showAll ? 'Show Top 15' : `Show All ${items.length}`}
        </button>
      )}
    </div>
  )
}

// ── Sortable full-feature table ───────────────────────────────────────────────

function FeatureTable({ roundData, featLabels }) {
  const hasPerm = !!(roundData?.permutation)
  const [sortCol, setSortCol] = useState(hasPerm ? 'perm' : 'corr')
  const [sortAsc, setSortAsc] = useState(false)

  if (!roundData) return null

  const permMap = {}
  const corrMap = {}
  const covMap  = {}

  if (roundData.permutation) {
    roundData.permutation.forEach(d => { permMap[d.feature] = d.value })
  }
  roundData.correlation.forEach(d => { corrMap[d.feature] = d.value })
  roundData.coverage.forEach(d   => { covMap[d.feature]   = d.value })

  const features = Object.keys(featLabels)

  const sorted = [...features].sort((a, b) => {
    let va, vb
    if (sortCol === 'perm') {
      va = permMap[a] !== undefined ? Math.abs(permMap[a]) : -1
      vb = permMap[b] !== undefined ? Math.abs(permMap[b]) : -1
    } else if (sortCol === 'corr') {
      va = corrMap[a] !== undefined ? Math.abs(corrMap[a]) : -Infinity
      vb = corrMap[b] !== undefined ? Math.abs(corrMap[b]) : -Infinity
    } else {
      va = covMap[a] !== undefined ? covMap[a] : -Infinity
      vb = covMap[b] !== undefined ? covMap[b] : -Infinity
    }
    return sortAsc ? va - vb : vb - va
  })

  const handleSort = col => {
    if (sortCol === col) setSortAsc(a => !a)
    else { setSortCol(col); setSortAsc(false) }
  }

  const permTop = roundData.permutation
    ? [...roundData.permutation].sort((a, b) => b.value - a.value).slice(0, 10).map(d => d.feature)
    : []

  function covClass(v) {
    if (v === undefined) return ''
    if (v > 0.90) return 'cov-hi'
    if (v >= 0.80) return 'cov-md'
    return 'cov-lo'
  }

  return (
    <div className="fi-table-section">
      <div className="fi-table-title">Full Feature Rankings</div>
      <div style={{ overflowX: 'auto' }}>
        <table className="fi-table">
          <thead>
            <tr>
              <th style={{ width: 32 }}>#</th>
              <th>Feature</th>
              <th
                className={`sortable${sortCol === 'perm' ? ' sorted' + (sortAsc ? ' asc' : '') : ''}`}
                onClick={() => handleSort('perm')}
                title="Sort by permutation importance"
              >Permutation</th>
              <th
                className={`sortable${sortCol === 'corr' ? ' sorted' + (sortAsc ? ' asc' : '') : ''}`}
                onClick={() => handleSort('corr')}
                title="Sort by correlation"
              >Correlation</th>
              <th
                className={`sortable${sortCol === 'cov' ? ' sorted' + (sortAsc ? ' asc' : '') : ''}`}
                onClick={() => handleSort('cov')}
                title="Sort by coverage"
              >Coverage</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((feat, idx) => {
              const pv  = permMap[feat]
              const cv  = corrMap[feat]
              const cov = covMap[feat]
              return (
                <tr key={feat}>
                  <td className="rank">{idx + 1}</td>
                  <td className="feat">{featLabels[feat]}</td>
                  <td className={`mono${permTop.includes(feat) ? ' top10' : ''}${pv !== undefined && pv < 0 ? ' neg' : ''}`}>
                    {pv !== undefined
                      ? `${pv >= 0 ? '+' : ''}${pv.toFixed(4)}`
                      : <span style={{ opacity: 0.35 }}>—</span>}
                  </td>
                  <td className="mono">
                    {cv !== undefined
                      ? `${cv >= 0 ? '+' : ''}${cv.toFixed(3)}`
                      : <span style={{ opacity: 0.35 }}>—</span>}
                  </td>
                  <td className={`mono ${covClass(cov)}`}>
                    {cov !== undefined ? `${(cov * 100).toFixed(0)}%` : '—'}
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {roundData.coverage.some(d => d.value < 0.80) && (
        <div className="fi-footnote">
          * Features with &lt;80% coverage have NaN data for early seasons — model handles these
          natively via HistGradientBoosting but importance may be understated.
        </div>
      )}
    </div>
  )
}

// ── Trajectory bump chart ─────────────────────────────────────────────────────

const RANK_LIMIT = 12

function TrajectoryChart({ data }) {
  const rankMaps = {}
  TRAJ_ROUNDS.forEach(rk => {
    rankMaps[rk] = {}
    ;(data.rounds[rk]?.permutation || []).forEach((d, i) => {
      rankMaps[rk][d.feature] = i + 1
    })
  })

  const top8 = (data.rounds['overall']?.permutation || []).slice(0, 8)
  if (top8.length === 0) return <div className="fi-no-data">No overall data</div>

  // Wider chart to fit full feature labels without truncation
  const W = 1060, H = 420
  const ML = 240, MR = 40, MT = 48, MB = 44
  const cW = W - ML - MR
  const cH = H - MT - MB
  const cols = TRAJ_ROUNDS.length

  const xOf = i    => ML + (i / (cols - 1)) * cW
  const yOf = rank => MT + ((rank - 1) / (RANK_LIMIT - 1)) * cH

  // S-curve bezier path between two points (classic bump-chart look)
  const bezier = (p1, p2) => {
    const mx = (p1.x + p2.x) / 2
    return `M${p1.x},${p1.y} C${mx},${p1.y} ${mx},${p2.y} ${p2.x},${p2.y}`
  }
  // Bezier from a point to a fixed-y destination (for off-chart transitions)
  const bezierToY = (p1, x2, y2) => {
    const mx = (p1.x + x2) / 2
    return `M${p1.x},${p1.y} C${mx},${p1.y} ${mx},${y2} ${x2},${y2}`
  }

  // Nudge left-side labels so they don't stack
  function nudgeLabels(items) {
    const MIN_GAP = 15
    const placed = items
      .map((f, fi) => {
        const rank = rankMaps[TRAJ_ROUNDS[0]][f.feature]
        const inRange = rank && rank <= RANK_LIMIT
        return { fi, y: inRange ? yOf(rank) : null }
      })
      .filter(d => d.y !== null)
      .sort((a, b) => a.y - b.y)

    for (let i = 1; i < placed.length; i++) {
      if (placed[i].y - placed[i - 1].y < MIN_GAP)
        placed[i].y = placed[i - 1].y + MIN_GAP
    }
    for (let i = placed.length - 1; i >= 0; i--) {
      if (placed[i].y > MT + cH) placed[i].y = MT + cH
      if (i > 0 && placed[i].y - placed[i - 1].y < MIN_GAP)
        placed[i - 1].y = placed[i].y - MIN_GAP
    }

    const out = {}
    placed.forEach(d => { out[d.fi] = d.y })
    return out
  }

  const labelY = nudgeLabels(top8)

  return (
    <div className="fi-trajectory-wrap">
      <div className="fi-trajectory-legend">
        {top8.map((f, fi) => (
          <span key={f.feature} className="fi-legend-item">
            <span className="fi-legend-dot" style={{ background: FEATURE_COLORS[fi] }} />
            {f.label}
          </span>
        ))}
      </div>

      <div style={{ overflow: 'hidden', maxWidth: `${W}px` }}>
        <svg
          viewBox={`0 0 ${W} ${H}`}
          width="100%"
          style={{ display: 'block' }}
          aria-label="Feature importance rank trajectory across tournament rounds"
        >
          <defs>
            <clipPath id="traj-clip">
              <rect x={0} y={0} width={W} height={H} />
            </clipPath>
          </defs>
          <g clipPath="url(#traj-clip)">

            {/* Top-3 gold highlight band */}
            <rect
              x={ML} y={yOf(1) - 10}
              width={cW} height={yOf(3) - yOf(1) + 20}
              fill="rgba(201,168,76,0.07)" rx={3}
            />
            <text x={ML + cW + 6} y={yOf(1) + 4}
              fill="rgba(201,168,76,0.35)" fontSize={8} fontFamily="monospace">
              TOP 3
            </text>

            {/* Vertical column lines */}
            {TRAJ_ROUNDS.map((rk, i) => (
              <line key={rk}
                x1={xOf(i)} x2={xOf(i)} y1={MT} y2={MT + cH}
                stroke="rgba(255,255,255,0.07)" strokeWidth={1}
              />
            ))}

            {/* Horizontal rank guides */}
            {[1, 3, 6, 9, 12].map(r => (
              <g key={r}>
                <line
                  x1={ML} x2={ML + cW} y1={yOf(r)} y2={yOf(r)}
                  stroke={r === 1 ? 'rgba(255,255,255,0.12)' : 'rgba(255,255,255,0.04)'}
                  strokeWidth={1} strokeDasharray="3 5"
                />
                <text x={ML - 8} y={yOf(r) + 4} textAnchor="end"
                  fill="rgba(255,255,255,0.3)" fontSize={9} fontFamily="monospace">
                  #{r}
                </text>
              </g>
            ))}

            {/* Round column headers */}
            {TRAJ_ROUNDS.map((rk, i) => (
              <text key={rk} x={xOf(i)} y={MT - 22} textAnchor="middle"
                fill="#c9a84c" fontSize={12} fontFamily="monospace" letterSpacing={1.5}
                fontWeight="bold">
                {ROUND_LABELS[rk]}
              </text>
            ))}

            {/* Feature curves + dots */}
            {top8.map((f, fi) => {
              const color = FEATURE_COLORS[fi]
              const pts = TRAJ_ROUNDS.map((rk, i) => {
                const rank = rankMaps[rk][f.feature]
                if (!rank) return null
                const inRange = rank <= RANK_LIMIT
                return { x: xOf(i), y: inRange ? yOf(rank) : null, rank, inRange }
              })

              // Smooth bezier segments
              const paths = []
              for (let i = 0; i < pts.length - 1; i++) {
                const p1 = pts[i], p2 = pts[i + 1]
                if (!p1 || !p2) continue
                if (p1.inRange && p2.inRange) {
                  paths.push(
                    <path key={`l${i}`} d={bezier(p1, p2)} fill="none"
                      stroke={color} strokeWidth={2.5} opacity={0.88}
                      strokeLinecap="round"
                    />
                  )
                } else if (p1.inRange && !p2.inRange) {
                  paths.push(
                    <path key={`l${i}`} d={bezierToY(p1, p2.x, MT + cH)} fill="none"
                      stroke={color} strokeWidth={1.5} opacity={0.3}
                      strokeDasharray="5 3" strokeLinecap="round"
                    />
                  )
                } else if (!p1.inRange && p2.inRange) {
                  paths.push(
                    <path key={`l${i}`} d={bezierToY(p2, p1.x, MT + cH)} fill="none"
                      stroke={color} strokeWidth={1.5} opacity={0.3}
                      strokeDasharray="5 3" strokeLinecap="round"
                    />
                  )
                }
              }

              // Dots + rank labels (in-range), pill badges (off-chart)
              const markers = pts.map((p, i) => {
                if (!p) return null
                if (p.inRange) {
                  return (
                    <g key={`d${i}`}>
                      <circle cx={p.x} cy={p.y} r={6}
                        fill={color} stroke="var(--bg)" strokeWidth={2.5} />
                      <text x={p.x} y={p.y - 11} textAnchor="middle"
                        fill={color} fontSize={9} fontFamily="monospace" fontWeight="600"
                        opacity={0.85}>
                        #{p.rank}
                      </text>
                    </g>
                  )
                }
                // Off-chart: pill badge with rank
                const by = MT + cH + 6
                return (
                  <g key={`d${i}`}>
                    {/* pill background */}
                    <rect x={p.x - 17} y={by} width={34} height={15} rx={7}
                      fill={color} opacity={0.18}
                    />
                    <rect x={p.x - 17} y={by} width={34} height={15} rx={7}
                      fill="none" stroke={color} strokeWidth={1} opacity={0.4}
                    />
                    <text x={p.x} y={by + 11} textAnchor="middle"
                      fill={color} fontSize={9} fontFamily="monospace" fontWeight="600"
                      opacity={0.85}>
                      ▼{p.rank}
                    </text>
                  </g>
                )
              })

              // Left label — full name, no truncation at this margin width
              const r64rank = rankMaps[TRAJ_ROUNDS[0]][f.feature]
              const r64InRange = r64rank && r64rank <= RANK_LIMIT

              return (
                <g key={f.feature}>
                  {paths}
                  {markers}
                  {labelY[fi] != null && (
                    <>
                      {r64InRange && (
                        <line
                          x1={ML - 5} x2={ML - 14}
                          y1={yOf(r64rank)} y2={labelY[fi]}
                          stroke={color} strokeWidth={1} opacity={0.35}
                        />
                      )}
                      <text x={ML - 16} y={labelY[fi] + 4} textAnchor="end"
                        fill={color} fontSize={11} fontFamily="sans-serif" fontWeight="500">
                        {f.label}
                      </text>
                    </>
                  )}
                </g>
              )
            })}

          </g>
        </svg>
      </div>

      <div className="fi-trajectory-note mono">
        Rank = permutation importance position in that round · 1 = most predictive ·
        Top 8 features by overall importance · ▼N = ranked outside top {RANK_LIMIT} ·
        F4 has small sample
      </div>
    </div>
  )
}

// ── Main viewer ───────────────────────────────────────────────────────────────

const TAB_ORDER = ['overview', 'trajectory', ...ROUND_KEYS]
const TAB_LABELS = {
  overview:   'Overview',
  trajectory: 'Trajectory',
  ...ROUND_LABELS,
}

export default function FeatureImportanceViewer() {
  const [data, setData]         = useState(null)
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [activeTab, setActiveTab] = useState('overview')
  const [showAllPerm, setShowAllPerm] = useState(false)
  const [showAllCorr, setShowAllCorr] = useState(false)

  useEffect(() => {
    fetch('/api/feature-importance')
      .then(r => {
        if (!r.ok) return r.json().then(e => { throw new Error(e.detail || r.statusText) })
        return r.json()
      })
      .then(d => { setData(d); setLoading(false) })
      .catch(e => { setError(e.message); setLoading(false) })
  }, [])

  if (loading) return <div className="state-msg loading">Loading feature importance data…</div>
  if (error)   return <div className="state-msg" style={{ color: 'var(--red-bright)' }}>{error}</div>
  if (!data)   return null

  // Decide which round data to show for bar charts
  const roundKey  = activeTab === 'overview' ? 'overall' : activeTab
  const rd        = data.rounds[roundKey]
  const coverageMap = {}
  rd?.coverage?.forEach(d => { coverageMap[d.feature] = d.value })

  const delta      = rd?.cv_acc != null && rd?.seed_acc != null ? rd.cv_acc - rd.seed_acc : null
  const deltaClass = delta == null ? 'zero' : delta > 0.005 ? 'pos' : delta < -0.005 ? 'neg' : 'zero'

  function switchTab(t) {
    setActiveTab(t)
    setShowAllPerm(false)
    setShowAllCorr(false)
  }

  return (
    <div className="fi-viewer">

      {/* ── Tab bar ── */}
      <div className="fi-round-bar">
        {TAB_ORDER.map(key => (
          <button
            key={key}
            className={`tab-btn fi-round-btn${key === 'trajectory' ? ' fi-traj-btn' : ''}${activeTab === key ? ' active' : ''}`}
            onClick={() => switchTab(key)}
          >
            {TAB_LABELS[key]}
          </button>
        ))}
      </div>

      {/* ── Overview: accuracy strip + overall charts + table ── */}
      {activeTab === 'overview' && (
        <>
          <div className="fi-overview-header">
            <div>
              <div className="fi-stats-title">
                {data.rounds['overall']?.name ?? 'Overall'} &nbsp;·&nbsp;
                {data.rounds['overall']?.n_games ?? data.n_games} games
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--cream-dim)', marginTop: 3 }}>
                {data.n_features} features · {data.generated_at}
              </div>
            </div>
            {delta != null && (
              <div className="fi-stats-metrics">
                <div className="fi-metric">
                  <span className="fi-stats-label">Model Accuracy</span>
                  <span className="fi-stats-val">{(rd.cv_acc * 100).toFixed(1)}%</span>
                </div>
                {rd.seed_acc != null && (
                  <div className="fi-metric">
                    <span className="fi-stats-label">Seed Baseline</span>
                    <span className="fi-stats-val">{(rd.seed_acc * 100).toFixed(1)}%</span>
                  </div>
                )}
                <div className="fi-metric">
                  <span className="fi-stats-label">Delta</span>
                  <span className={`fi-stats-val fi-delta ${deltaClass}`}>
                    {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
                  </span>
                </div>
              </div>
            )}
          </div>

          <AccuracyStrip data={data} />

          <div className="fi-charts-row">
            <FeatureChart
              title="Permutation Importance · Accuracy drop when feature shuffled"
              items={rd?.permutation}
              colorClass="gold"
              showAll={showAllPerm}
              onToggle={() => setShowAllPerm(v => !v)}
              coverageMap={coverageMap}
            />
            <FeatureChart
              title="Univariate Correlation · With win/loss outcome"
              items={rd?.correlation}
              colorClass="blue"
              showAll={showAllCorr}
              onToggle={() => setShowAllCorr(v => !v)}
              coverageMap={coverageMap}
            />
          </div>

          <FeatureTable roundData={rd} featLabels={data.feature_labels} />
        </>
      )}

      {/* ── Trajectory view ── */}
      {activeTab === 'trajectory' && (
        <div style={{ padding: '12px 0' }}>
          <div className="fi-section-heading">
            How Feature Importance Shifts Across Rounds
          </div>
          <div className="fi-section-sub mono">
            Top 8 features by overall permutation importance · rank = position in that round's importance list
          </div>
          <TrajectoryChart data={data} />
        </div>
      )}

      {/* ── Per-round view (R64–NCG) ── */}
      {ROUND_KEYS.includes(activeTab) && rd && (
        <>
          <div className="fi-stats-header">
            <div>
              <div className="fi-stats-title">
                {rd.name} &nbsp;·&nbsp; {rd.n_games} games
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--cream-dim)', marginTop: 3 }}>
                {data.n_features} features · {data.generated_at}
              </div>
            </div>
            {rd.cv_acc != null && (
              <div className="fi-stats-metrics">
                <div className="fi-metric">
                  <span className="fi-stats-label">Model Accuracy</span>
                  <span className="fi-stats-val">{(rd.cv_acc * 100).toFixed(1)}%</span>
                </div>
                {rd.seed_acc != null && (
                  <div className="fi-metric">
                    <span className="fi-stats-label">Seed Baseline</span>
                    <span className="fi-stats-val">{(rd.seed_acc * 100).toFixed(1)}%</span>
                  </div>
                )}
                {delta != null && (
                  <div className="fi-metric">
                    <span className="fi-stats-label">Delta</span>
                    <span className={`fi-stats-val fi-delta ${deltaClass}`}>
                      {delta >= 0 ? '+' : ''}{(delta * 100).toFixed(1)}%
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="fi-charts-row">
            {rd.permutation ? (
              <FeatureChart
                title="Permutation Importance · Accuracy drop when feature shuffled"
                items={rd.permutation}
                colorClass="gold"
                showAll={showAllPerm}
                onToggle={() => setShowAllPerm(v => !v)}
                coverageMap={coverageMap}
              />
            ) : (
              <div className="fi-chart-card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 6, padding: '28px 20px', opacity: 0.5 }}>
                <div className="fi-chart-title">Permutation Importance</div>
                <div className="mono" style={{ fontSize: '0.65rem', color: 'var(--cream-dim)', textAlign: 'center' }}>
                  Not computed for {rd.name}<br />
                  Only {rd.n_games} games — sample too small for reliable permutation testing
                </div>
              </div>
            )}
            <FeatureChart
              title="Univariate Correlation · With win/loss outcome"
              items={rd.correlation}
              colorClass="blue"
              showAll={showAllCorr}
              onToggle={() => setShowAllCorr(v => !v)}
              coverageMap={coverageMap}
            />
          </div>

          <FeatureTable roundData={rd} featLabels={data.feature_labels} />
        </>
      )}

      {/* ── Empty state for NCG (tiny sample) ── */}
      {ROUND_KEYS.includes(activeTab) && !rd && (
        <div className="state-msg">No data for {TAB_LABELS[activeTab]}</div>
      )}

    </div>
  )
}
