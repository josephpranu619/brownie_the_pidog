import { useEffect, useState } from 'react'
import './App.css'

const telemetry = [
  ['Battery', '86', '%'],
  ['Distance', '74', 'cm'],
  ['CPU', '49', '°C'],
  ['Pose', 'Stand', ''],
]

const quickActions = [
  ['😊', 'Happy', 'Tail + head gesture'],
  ['👀', 'Curious', 'Look + head tilt'],
  ['🤝', 'Handshake', 'Front paw action'],
  ['🐾', 'Come here', 'Custom macro'],
]

function ActionButton({ children, action, className = '' }) {
  const event = new CustomEvent('brownie-demo-action', { detail: action })

  return (
    <button
      type="button"
      className={className}
      onClick={() => window.dispatchEvent(event)}
    >
      {children}
    </button>
  )
}

function DPad({ label, prefix = '' }) {
  const name = (direction) => `${prefix}${direction}`.trim()

  return (
    <div className="joy-box">
      <div className="joy-label">{label}</div>
      <div className="dpad">
        <ActionButton className="dpad-button up" action={name('up')} aria-label={`${label} up`}>▲</ActionButton>
        <ActionButton className="dpad-button left" action={name('left')} aria-label={`${label} left`}>◀</ActionButton>
        <div className="dpad-center" aria-hidden="true" />
        <ActionButton className="dpad-button right" action={name('right')} aria-label={`${label} right`}>▶</ActionButton>
        <ActionButton className="dpad-button down" action={name('down')} aria-label={`${label} down`}>▼</ActionButton>
      </div>
    </div>
  )
}

function App() {
  const [toast, setToast] = useState('')
  const [activeNav, setActiveNav] = useState('Control')

  useEffect(() => {
    let timeout

    const handleAction = (event) => {
      setToast(`${event.detail} · demo only`)
      clearTimeout(timeout)
      timeout = setTimeout(() => setToast(''), 1200)
    }

    window.addEventListener('brownie-demo-action', handleAction)
    return () => {
      clearTimeout(timeout)
      window.removeEventListener('brownie-demo-action', handleAction)
    }
  }, [])

  const changeNav = (name) => {
    setActiveNav(name)
    window.dispatchEvent(new CustomEvent('brownie-demo-action', { detail: name }))
  }

  return (
    <>
      <div className={`toast ${toast ? 'show' : ''}`} role="status">
        {toast}
      </div>

      <main className="shell">
        <header className="topbar">
          <div className="brand">
            <div className="logo" aria-hidden="true">🐕</div>
            <div>
              <div className="title">Brownie</div>
              <div className="subtitle">PiDog Control</div>
            </div>
          </div>
          <div className="online"><span className="dot" /> Online</div>
        </header>

        <section className="main-grid">
          <div className="card camera">
            <div className="camera-view">
              <div className="fake-room">
                <div className="floor" />
                <div className="dog" aria-hidden="true">🐕‍🦺</div>
              </div>
              <div className="camera-top">
                <div className="pill live"><span /> LIVE</div>
                <div className="pill">720p · 24 fps</div>
              </div>
              <div className="camera-label">
                <h1>Brownie Cam</h1>
                <p>Front camera · simulated preview</p>
              </div>
            </div>
          </div>

          <div className="side-column">
            <section className="card panel">
              <div className="section-title"><strong>Status</strong><span>SIMULATED</span></div>
              <div className="telemetry">
                {telemetry.map(([key, value, unit]) => (
                  <div className="metric" key={key}>
                    <div className="metric-key">{key}</div>
                    <div className={`metric-value ${key === 'Pose' ? 'pose' : ''}`}>
                      {value}{unit && <span className="metric-unit">{unit}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <section className="card panel">
              <div className="section-title"><strong>Posture</strong><span>QUICK</span></div>
              <div className="control-grid">
                <ActionButton className="action primary" action="Stand">Stand</ActionButton>
                <ActionButton className="action" action="Sit">Sit</ActionButton>
                <ActionButton className="action" action="Lie down">Lie</ActionButton>
                <ActionButton className="action danger" action="Emergency stop">STOP</ActionButton>
              </div>
            </section>
          </div>
        </section>

        <section className="card bottom-sheet">
          <div className="section-title"><strong>Manual control</strong><span>DEMO CONTROLS</span></div>
          <div className="joystick-wrap">
            <DPad label="BODY" prefix="Body " />
            <DPad label="HEAD" prefix="Head " />
          </div>
        </section>

        <section className="card bottom-sheet">
          <div className="section-title"><strong>Brownie actions</strong><span>CUSTOMIZABLE</span></div>
          <div className="quick-row">
            {quickActions.map(([icon, name, description]) => (
              <ActionButton className="quick" action={name} key={name}>
                <b>{icon} {name}</b>
                <span>{description}</span>
              </ActionButton>
            ))}
          </div>
        </section>
      </main>

      <nav className="bottom-nav" aria-label="Brownie app sections">
        {[
          ['⌂', 'Control'],
          ['◉', 'Camera'],
          ['✦', 'Actions'],
          ['⚙', 'Settings'],
        ].map(([icon, name]) => (
          <button
            type="button"
            className={activeNav === name ? 'active' : ''}
            onClick={() => changeNav(name)}
            key={name}
          >
            <span className="nav-icon">{icon}</span>
            {name}
          </button>
        ))}
      </nav>
    </>
  )
}

export default App
