import { useState } from 'react'

const PALETTE = [
  '#3b82f6', '#ef4444', '#22c55e', '#f59e0b',
  '#8b5cf6', '#ec4899', '#14b8a6', '#f97316',
  '#06b6d4', '#a855f7', '#84cc16', '#f43f5e',
]

function teamColor(name) {
  let h = 0
  for (let i = 0; i < name.length; i++) {
    h = (Math.imul(31, h) + name.charCodeAt(i)) | 0
  }
  return PALETTE[Math.abs(h) % PALETTE.length]
}

function teamInitials(name) {
  const SKIP = new Set(['of', 'the', 'at', 'and', 'a'])
  const words = name.replace(/\./g, '').trim().split(/\s+/)
  const meaningful = words.filter(w => !SKIP.has(w.toLowerCase()))
  if (meaningful.length === 0) return name.slice(0, 2).toUpperCase()
  if (meaningful.length === 1) return meaningful[0].slice(0, 2).toUpperCase()
  return meaningful.map(w => w[0]).join('').slice(0, 3).toUpperCase()
}

function teamSlug(name) {
  return name
    .replace(/ /g, '_')
    .replace(/\./g, '')
    .replace(/'/g, '')
    .replace(/&/g, 'and')
    .replace(/[()]/g, '')
}

export default function TeamAvatar({ team, size = 48 }) {
  const [imgFailed, setImgFailed] = useState(false)
  const bg = teamColor(team)
  const initials = teamInitials(team)
  const fontSize = Math.round(size * 0.38)
  const slug = teamSlug(team)

  const circleStyle = {
    width: size,
    height: size,
    borderRadius: '50%',
    background: bg,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    boxShadow: `0 0 14px ${bg}55`,
  }

  if (!imgFailed) {
    return (
      <div style={{ width: size, height: size, flexShrink: 0 }}>
        <img
          src={`/logos/${slug}.png`}
          alt={team}
          width={size}
          height={size}
          style={{ borderRadius: '50%', objectFit: 'contain' }}
          onError={() => setImgFailed(true)}
        />
      </div>
    )
  }

  return (
    <div className="team-avatar" style={circleStyle}>
      <span
        className="mono"
        style={{
          color: '#fff',
          fontSize,
          fontWeight: 700,
          letterSpacing: '0.05em',
          lineHeight: 1,
          userSelect: 'none',
        }}
      >
        {initials}
      </span>
    </div>
  )
}
