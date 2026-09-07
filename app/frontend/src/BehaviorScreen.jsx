import { useEffect, useState } from 'react'

const behaviors = [
  ['🌅', 'Wake Up', 'wake-up', true],
  ['🎛', 'Function Demonstration', 'function-demonstration', false],
  ['🐾', 'Patrol', 'patrol', true],
  ['💬', 'Response', 'response', true],
  ['💤', 'Rest', 'rest', true],
  ['🤲', 'Be Picked Up', 'be-picked-up', true],
  ['🙂', 'Face Track', 'face-track', true],
  ['💪', 'Push Up', 'push-up', true],
  ['🌙', 'Howling', 'howling', true],
  ['⚖️', 'Balance', 'balance', true],
  ['⌨️', 'Play PiDog with Keyboard', 'keyboard-control', false],
  ['⚽', 'Ball Track', 'ball-track', true],
]

function BehaviorScreen({ onToast }) {
  const [status, setStatus] = useState({ running: false, behavior: null })
  const [busy, setBusy] = useState('')

  const refreshStatus = async () => {
    try {
      const response = await fetch('/api/behaviors/status', { cache: 'no-store' })
      if (!response.ok) return
      const data = await response.json()
      setStatus({
        running: data.running === true,
        behavior: typeof data.behavior === 'string' ? data.behavior : null,
      })
    } catch {
      // Keep the last known state through transient API misses.
    }
  }

  useEffect(() => {
    let cancelled = false

    const poll = async () => {
      if (cancelled) return
      await refreshStatus()
    }

    poll()
    const interval = window.setInterval(poll, 1500)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [])

  const toggleBehavior = async (name, key, runnable) => {
    if (!runnable) {
      onToast(`${name} is terminal-only · use brownie-hub`)
      return
    }

    if (status.running && status.behavior !== key) {
      onToast('Stop the active behavior first')
      return
    }

    setBusy(key)
    try {
      let response

      if (status.running && status.behavior === key) {
        response = await fetch('/api/behaviors/stop', {
          method: 'POST',
          cache: 'no-store',
        })
      } else {
        await fetch('/api/camera/stop', {
          method: 'POST',
          cache: 'no-store',
        }).catch(() => {})

        response = await fetch(`/api/behaviors/${encodeURIComponent(key)}/start`, {
          method: 'POST',
          cache: 'no-store',
        })
      }

      const data = await response.json().catch(() => null)
      if (!response.ok) {
        throw new Error(data?.detail || `${name} request failed`)
      }

      setStatus({
        running: data.running === true,
        behavior: typeof data.behavior === 'string' ? data.behavior : null,
      })
      onToast(data.message || (data.running ? `${name} started` : `${name} stopped`))
    } catch (error) {
      onToast(error?.message || `${name} request failed`)
    } finally {
      setBusy('')
      window.setTimeout(refreshStatus, 350)
    }
  }

  return (
    <div className="screen-stack">
      <section className="actions-library">
        {behaviors.map(([icon, name, key, runnable]) => {
          const active = status.running && status.behavior === key
          return (
            <button
              type="button"
              className="card behavior-card"
              key={key}
              onClick={() => toggleBehavior(name, key, runnable)}
              disabled={Boolean(busy) && busy !== key}
              aria-pressed={active}
              title={runnable ? (active ? `Stop ${name}` : `Start ${name}`) : `${name} requires brownie-hub`}
              style={active ? { borderColor: 'rgba(232, 167, 93, 0.75)' } : undefined}
            >
              <span className="behavior-icon">{icon}</span>
              <span className="behavior-copy"><b>{name}</b></span>
              <span className="behavior-play">
                {busy === key ? '…' : active ? '■' : runnable ? '▶' : '⌘'}
              </span>
            </button>
          )
        })}
      </section>
    </div>
  )
}

export default BehaviorScreen
