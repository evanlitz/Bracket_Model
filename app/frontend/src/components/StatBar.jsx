import { useEffect, useState } from 'react'

export default function StatBar({ label, value, type = 'combined' }) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    // Trigger animation after mount
    const t = setTimeout(() => setWidth(value ?? 0), 60)
    return () => clearTimeout(t)
  }, [value])

  return (
    <div className="sim-bar-row">
      <div className="sim-bar-label mono">{label}</div>
      <div className="sim-bar-track">
        <div
          className={`sim-bar-fill ${type}-bar`}
          style={{ width: `${width}%` }}
        />
      </div>
      <div className="sim-bar-val display">{value ?? '—'}</div>
    </div>
  )
}
