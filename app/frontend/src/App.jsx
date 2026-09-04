import { useEffect, useState } from 'react'
import './App.css'

const quickActions = [
  ['😊', 'Happy', 'Tail + head gesture'],
  ['👀', 'Curious', 'Look + head tilt'],
  ['🤝', 'Handshake', 'Front paw action'],
  ['🐾', 'Come here', 'Custom macro'],
]

const navItems = [
  ['⌂', 'Control'],
  ['◉', 'Camera'],
  ['✦', 'Actions'],
  ['⌁', 'Tune'],
  ['⚙', 'Settings'],
]

function sendDemoAction(action) {
  window.dispatchEvent(new CustomEvent('brownie-demo-action', { detail: action }))
}

function ActionButton({ children, action, className = '', ...props }) {
  return (
    <button
      type="button"
      className={className}
      onClick={() => sendDemoAction(action)}
      {...props}
    >
      {children}
    </button>
  )
}

function CameraPreview({ large = false }) {
  return (
    <div className={`card camera ${large ? 'camera-large' : ''}`}>
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

function ControlScreen({ cpuTemp }) {
  const telemetry = [
    ['Battery', '86', '%'],
    ['Distance', '74', 'cm'],
    ['CPU', cpuTemp == null ? '—' : cpuTemp.toFixed(1), '°C'],
    ['Pose', 'Stand', ''],
  ]

  return (
    <>
      <section className="main-grid">
        <CameraPreview />

        <div className="side-column">
          <section className="card panel">
            <div className="section-title"><strong>Status</strong><span>CPU LIVE · OTHERS SIMULATED</span></div>
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
    </>
  )
}

function CameraScreen() {
  return (
    <div className="screen-stack">
      <div className="screen-heading">
        <div>
          <span className="eyebrow">CAMERA</span>
          <h1>Brownie's view</h1>
          <p>Dedicated camera controls will live here without crowding the main controller.</p>
        </div>
        <span className="sim-badge">SIMULATED</span>
      </div>

      <CameraPreview large />

      <section className="camera-tools">
        <div className="card panel tool-card">
          <div className="section-title"><strong>View</strong><span>PREVIEW</span></div>
          <div className="control-grid">
            <ActionButton className="action primary" action="Take snapshot">Snapshot</ActionButton>
            <ActionButton className="action" action="Fullscreen camera">Fullscreen</ActionButton>
          </div>
        </div>

        <div className="card panel tool-card">
          <div className="section-title"><strong>Head camera</strong><span>POSITION</span></div>
          <div className="mini-actions">
            <ActionButton className="action" action="Center head">Center head</ActionButton>
            <ActionButton className="action" action="Follow mode">Follow mode</ActionButton>
          </div>
        </div>
      </section>
    </div>
  )
}

function ActionsScreen() {
  return (
    <div className="screen-stack">
      <div className="screen-heading">
        <div>
          <span className="eyebrow">ACTIONS</span>
          <h1>Brownie's behaviors</h1>
          <p>This will become the home for built-in actions and your own reusable macros.</p>
        </div>
        <span className="sim-badge">SIMULATED</span>
      </div>

      <section className="actions-library">
        {quickActions.map(([icon, name, description]) => (
          <ActionButton className="card behavior-card" action={name} key={name}>
            <span className="behavior-icon">{icon}</span>
            <span className="behavior-copy">
              <b>{name}</b>
              <small>{description}</small>
            </span>
            <span className="behavior-play">▶</span>
          </ActionButton>
        ))}

        <ActionButton className="card behavior-card add-behavior" action="Create custom action">
          <span className="behavior-icon">＋</span>
          <span className="behavior-copy">
            <b>New custom action</b>
            <small>Combine movement, head, tail and sound later</small>
          </span>
        </ActionButton>
      </section>
    </div>
  )
}

function TuneScreen() {
  const [silenceDuration, setSilenceDuration] = useState(3.0)
  const [silenceThreshold, setSilenceThreshold] = useState(1800)
  const [speakerVolume, setSpeakerVolume] = useState(60)

  const sliderStyle = { width: 'min(360px, 48vw)', accentColor: '#e8a75d' }
  const numberStyle = { width: '82px', textAlign: 'right' }

  return (
    <div className="screen-stack">
      <div className="screen-heading">
        <div>
          <span className="eyebrow">TUNE</span>
          <h1>Brownie tuning</h1>
          <p>A friendlier interface for the parameters currently exposed by <code>brownie-tuning</code>. Changes are simulated for now.</p>
        </div>
        <span className="sim-badge">SIMULATED</span>
      </div>

      <section className="card settings-card">
        <div className="setting-row">
          <div>
            <b>Voice silence duration</b>
            <span>How long audio must stay quiet before Hermes stops listening.</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <input
              aria-label="Voice silence duration"
              type="range"
              min="0.5"
              max="6"
              step="0.1"
              value={silenceDuration}
              onChange={(event) => setSilenceDuration(Number(event.target.value))}
              style={sliderStyle}
            />
            <input
              aria-label="Voice silence duration value"
              className="setting-value"
              type="number"
              min="0.5"
              max="6"
              step="0.1"
              value={silenceDuration}
              onChange={(event) => setSilenceDuration(Number(event.target.value))}
              style={numberStyle}
            />
            <span>s</span>
          </div>
        </div>

        <div className="setting-row">
          <div>
            <b>Voice silence threshold</b>
            <span>RMS level below which Hermes treats audio as silence. Higher values tolerate more background noise, but too high can cut off quiet speech.</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <input
              aria-label="Voice silence threshold"
              type="range"
              min="500"
              max="4000"
              step="50"
              value={silenceThreshold}
              onChange={(event) => setSilenceThreshold(Number(event.target.value))}
              style={sliderStyle}
            />
            <input
              aria-label="Voice silence threshold value"
              className="setting-value"
              type="number"
              min="500"
              max="4000"
              step="50"
              value={silenceThreshold}
              onChange={(event) => setSilenceThreshold(Number(event.target.value))}
              style={numberStyle}
            />
          </div>
        </div>

        <div className="setting-row">
          <div>
            <b>Speaker volume</b>
            <span>Robot HAT hardware speaker output. 0% is silent; 100% is maximum hardware volume.</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <input
              aria-label="Speaker volume"
              type="range"
              min="0"
              max="100"
              step="1"
              value={speakerVolume}
              onChange={(event) => setSpeakerVolume(Number(event.target.value))}
              style={sliderStyle}
            />
            <input
              aria-label="Speaker volume value"
              className="setting-value"
              type="number"
              min="0"
              max="100"
              step="1"
              value={speakerVolume}
              onChange={(event) => setSpeakerVolume(Number(event.target.value))}
              style={numberStyle}
            />
            <span>%</span>
          </div>
        </div>

        <div className="setting-row">
          <div>
            <b>Microphone source</b>
            <span>Will show Brownie's PulseAudio default source and available input devices.</span>
          </div>
          <button type="button" className="setting-value" onClick={() => sendDemoAction('Inspect microphone source')}>Inspect</button>
        </div>
      </section>

      <section className="card panel">
        <div className="section-title"><strong>Pending changes</strong><span>NOT SENT TO BROWNIE</span></div>
        <div className="telemetry">
          <div className="metric">
            <div className="metric-key">Silence duration</div>
            <div className="metric-value">{silenceDuration.toFixed(1)}<span className="metric-unit">s</span></div>
          </div>
          <div className="metric">
            <div className="metric-key">Silence threshold</div>
            <div className="metric-value">{silenceThreshold}</div>
          </div>
          <div className="metric">
            <div className="metric-key">Speaker</div>
            <div className="metric-value">{speakerVolume}<span className="metric-unit">%</span></div>
          </div>
          <ActionButton className="action primary" action="Apply tuning settings">Apply later</ActionButton>
        </div>
      </section>
    </div>
  )
}

function SettingsScreen() {
  return (
    <div className="screen-stack">
      <div className="screen-heading">
        <div>
          <span className="eyebrow">SETTINGS</span>
          <h1>App preferences</h1>
          <p>These controls are visual placeholders until the backend and real device state exist.</p>
        </div>
        <span className="sim-badge">SIMULATED</span>
      </div>

      <section className="card settings-card">
        <div className="setting-row">
          <div><b>Camera quality</b><span>720p · balanced for Raspberry Pi 4</span></div>
          <button type="button" className="setting-value" onClick={() => sendDemoAction('Camera quality')}>720p</button>
        </div>
        <div className="setting-row">
          <div><b>Movement speed</b><span>Default manual-control speed</span></div>
          <button type="button" className="setting-value" onClick={() => sendDemoAction('Movement speed')}>Normal</button>
        </div>
        <div className="setting-row">
          <div><b>Low-bandwidth mode</b><span>Future option for slower connections</span></div>
          <button type="button" className="toggle-demo" onClick={() => sendDemoAction('Low-bandwidth mode')} aria-label="Low-bandwidth mode demo toggle"><span /></button>
        </div>
        <div className="setting-row">
          <div><b>Haptic feedback</b><span>Phone feedback for control presses</span></div>
          <button type="button" className="toggle-demo on" onClick={() => sendDemoAction('Haptic feedback')} aria-label="Haptic feedback demo toggle"><span /></button>
        </div>
      </section>
    </div>
  )
}

function App() {
  const [toast, setToast] = useState('')
  const [activeNav, setActiveNav] = useState('Control')
  const [systemStatus, setSystemStatus] = useState(null)

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

  useEffect(() => {
    let cancelled = false

    const refreshStatus = async () => {
      try {
        const response = await fetch('/api/status', { cache: 'no-store' })
        if (!response.ok) throw new Error(`Status ${response.status}`)

        const data = await response.json()
        const cpuTemp = Number(data.cpu_temp_c)

        if (!cancelled) {
          setSystemStatus({
            online: data.online === true,
            cpuTemp: Number.isFinite(cpuTemp) ? cpuTemp : null,
          })
        }
      } catch {
        if (!cancelled) setSystemStatus({ online: false, cpuTemp: null })
      }
    }

    refreshStatus()
    const interval = window.setInterval(refreshStatus, 5000)

    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [])

  const isOnline = systemStatus?.online === true
  const connectionLabel = systemStatus == null ? 'Connecting' : isOnline ? 'Online' : 'Offline'
  const dotStyle = systemStatus == null
    ? { background: '#8d98a8', boxShadow: 'none' }
    : !isOnline
      ? { background: '#ff6b6b', boxShadow: 'none' }
      : undefined

  const screens = {
    Control: <ControlScreen cpuTemp={systemStatus?.cpuTemp ?? null} />,
    Camera: <CameraScreen />,
    Actions: <ActionsScreen />,
    Tune: <TuneScreen />,
    Settings: <SettingsScreen />,
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
          <div className="online"><span className="dot" style={dotStyle} /> {connectionLabel}</div>
        </header>

        {screens[activeNav]}
      </main>

      <nav
        className="bottom-nav"
        aria-label="Brownie app sections"
        style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}
      >
        {navItems.map(([icon, name]) => (
          <button
            type="button"
            className={activeNav === name ? 'active' : ''}
            onClick={() => setActiveNav(name)}
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
