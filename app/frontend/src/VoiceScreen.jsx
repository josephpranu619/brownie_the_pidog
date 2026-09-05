import { useEffect, useMemo, useState } from 'react'

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 KB'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function RecordingRow({ item, busy, onPreview, onPlay, onKeep, onDelete }) {
  const sourceIcon = item.source === 'device' ? '📱' : item.source === 'brownie' ? '🐕' : '🎤'
  const duration = item.duration_seconds == null ? '' : ` · ${item.duration_seconds.toFixed(1)}s`

  return (
    <div
      className="setting-row"
      style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 1fr) auto',
        gap: '12px',
        alignItems: 'center',
      }}
    >
      <div style={{ minWidth: 0 }}>
        <b style={{ display: 'block', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {sourceIcon} {item.name}
        </b>
        <span>
          {item.source === 'device' ? 'This device' : item.source === 'brownie' ? 'Brownie microphone' : 'Recording'}
          {duration} · {formatBytes(item.bytes)}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '7px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
        <button type="button" className="action" onClick={() => onPreview(item)} disabled={busy}>Preview</button>
        <button type="button" className="action primary" onClick={() => onPlay(item)} disabled={busy}>Brownie ▶</button>
        {!item.saved && (
          <button type="button" className="action" onClick={() => onKeep(item)} disabled={busy}>☆ Keep</button>
        )}
        <button type="button" className="action danger" onClick={() => onDelete(item)} disabled={busy}>Delete</button>
      </div>
    </div>
  )
}

function VoiceScreen({ onToast }) {
  const [sounds, setSounds] = useState([])
  const [recordings, setRecordings] = useState([])
  const [recentPolicy, setRecentPolicy] = useState(null)
  const [speakerSource, setSpeakerSource] = useState('pidog')
  const [selectedSound, setSelectedSound] = useState('')
  const [selectedRecordingId, setSelectedRecordingId] = useState('')
  const [volume, setVolume] = useState(80)
  const [micSource, setMicSource] = useState('brownie')
  const [busy, setBusy] = useState('')

  const recent = useMemo(() => recordings.filter((item) => !item.saved), [recordings])
  const saved = useMemo(() => recordings.filter((item) => item.saved), [recordings])
  const deviceMicAvailable = window.isSecureContext && Boolean(navigator.mediaDevices?.getUserMedia)

  const refresh = async () => {
    try {
      const [soundResponse, recordingResponse] = await Promise.all([
        fetch('/api/voice/sounds', { cache: 'no-store' }),
        fetch('/api/voice/recordings', { cache: 'no-store' }),
      ])

      if (soundResponse.ok) {
        const soundData = await soundResponse.json()
        const nextSounds = Array.isArray(soundData.sounds) ? soundData.sounds : []
        setSounds(nextSounds)
        setSelectedSound((current) => current || nextSounds[0] || '')
      }

      if (recordingResponse.ok) {
        const recordingData = await recordingResponse.json()
        const nextRecordings = Array.isArray(recordingData.recordings) ? recordingData.recordings : []
        setRecordings(nextRecordings)
        setRecentPolicy(recordingData.recent_policy || null)
        setSelectedRecordingId((current) => (
          nextRecordings.some((item) => item.id === current) ? current : nextRecordings[0]?.id || ''
        ))
      }
    } catch {
      onToast('Voice library unavailable')
    }
  }

  useEffect(() => {
    refresh()
  }, [])

  const playSpeakerSelection = async () => {
    setBusy('play')
    try {
      let response
      if (speakerSource === 'pidog') {
        if (!selectedSound) throw new Error('No PiDog sound selected')
        response = await fetch(
          `/api/voice/sounds/play?name=${encodeURIComponent(selectedSound)}&volume=${volume}`,
          { method: 'POST', cache: 'no-store' },
        )
      } else {
        if (!selectedRecordingId) throw new Error('No recording selected')
        response = await fetch(
          `/api/voice/recordings/play?recording_id=${encodeURIComponent(selectedRecordingId)}&volume=${volume}`,
          { method: 'POST', cache: 'no-store' },
        )
      }

      if (!response.ok) throw new Error(`Play ${response.status}`)
      onToast('Playing on Brownie')
    } catch {
      onToast('Speaker playback failed')
    } finally {
      setBusy('')
    }
  }

  const recordBrownie = async () => {
    if (micSource === 'device') {
      onToast(deviceMicAvailable ? 'Device microphone upload comes next' : 'This device microphone requires HTTPS')
      return
    }

    setBusy('record')
    onToast('Recording Brownie microphone for 5 seconds…')
    try {
      const response = await fetch('/api/voice/recordings/record-brownie', {
        method: 'POST',
        cache: 'no-store',
      })
      if (!response.ok) throw new Error(`Record ${response.status}`)
      await refresh()
      onToast('Recording added to Recent')
    } catch {
      onToast('Brownie microphone recording failed')
    } finally {
      setBusy('')
    }
  }

  const previewRecording = (item) => {
    const audio = new Audio(item.preview_url)
    audio.play().catch(() => onToast('Preview unavailable on this device'))
  }

  const playRecording = async (item) => {
    setBusy(item.id)
    try {
      const response = await fetch(
        `/api/voice/recordings/play?recording_id=${encodeURIComponent(item.id)}&volume=${volume}`,
        { method: 'POST', cache: 'no-store' },
      )
      if (!response.ok) throw new Error(`Play ${response.status}`)
      onToast('Playing recording on Brownie')
    } catch {
      onToast('Recording playback failed')
    } finally {
      setBusy('')
    }
  }

  const keepRecording = async (item) => {
    setBusy(item.id)
    try {
      const response = await fetch(
        `/api/voice/recordings/keep?recording_id=${encodeURIComponent(item.id)}`,
        { method: 'POST', cache: 'no-store' },
      )
      if (!response.ok) throw new Error(`Keep ${response.status}`)
      await refresh()
      onToast('Recording moved to Saved')
    } catch {
      onToast('Could not keep recording')
    } finally {
      setBusy('')
    }
  }

  const deleteRecording = async (item) => {
    if (!window.confirm(`Delete ${item.name}?`)) return

    setBusy(item.id)
    try {
      const response = await fetch(
        `/api/voice/recordings?recording_id=${encodeURIComponent(item.id)}`,
        { method: 'DELETE', cache: 'no-store' },
      )
      if (!response.ok) throw new Error(`Delete ${response.status}`)
      await refresh()
      onToast('Recording deleted')
    } catch {
      onToast('Could not delete recording')
    } finally {
      setBusy('')
    }
  }

  const selectStyle = {
    width: '100%',
    minHeight: '44px',
    borderRadius: '10px',
    border: '1px solid rgba(255,255,255,0.09)',
    background: '#151b24',
    color: '#f4f7fb',
    padding: '0 12px',
  }

  return (
    <div className="screen-stack">
      <div className="screen-heading">
        <div>
          <span className="eyebrow">VOICE</span>
          <h1>Brownie's audio center</h1>
          <p>Play PiDog sounds, record from Brownie, and manage recordings without cluttering Control.</p>
        </div>
        <span className="sim-badge">AUDIO LIVE</span>
      </div>

      <section className="card panel">
        <div className="section-title"><strong>Speaker</strong><span>SOUNDBOARD</span></div>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(160px, 0.7fr) minmax(240px, 1.3fr)', gap: '12px' }}>
          <div>
            <span className="metric-key">Sound source</span>
            <select value={speakerSource} onChange={(event) => setSpeakerSource(event.target.value)} style={selectStyle}>
              <option value="pidog">PiDog sounds</option>
              <option value="recordings">Recordings</option>
            </select>
          </div>

          <div>
            <span className="metric-key">Selection</span>
            {speakerSource === 'pidog' ? (
              <select value={selectedSound} onChange={(event) => setSelectedSound(event.target.value)} style={selectStyle}>
                {sounds.map((sound) => <option value={sound} key={sound}>{sound}</option>)}
              </select>
            ) : (
              <select value={selectedRecordingId} onChange={(event) => setSelectedRecordingId(event.target.value)} style={selectStyle}>
                {recordings.length === 0 && <option value="">No recordings yet</option>}
                {recordings.map((item) => (
                  <option value={item.id} key={item.id}>
                    {item.saved ? 'Saved' : 'Recent'} · {item.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        <div style={{ marginTop: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', marginBottom: '8px' }}>
            <b>Brownie speaker volume</b>
            <span className="setting-value">{volume}%</span>
          </div>
          <input
            type="range"
            min="0"
            max="100"
            step="1"
            value={volume}
            onChange={(event) => setVolume(Number(event.target.value))}
            style={{ width: '100%', accentColor: '#e8a75d' }}
          />
        </div>

        <button
          type="button"
          className="action primary"
          onClick={playSpeakerSelection}
          disabled={busy === 'play' || (speakerSource === 'recordings' && !selectedRecordingId)}
          style={{ marginTop: '16px', width: '100%' }}
        >
          {busy === 'play' ? 'Playing…' : '▶ Play on Brownie'}
        </button>
      </section>

      <section className="card panel">
        <div className="section-title"><strong>Microphone</strong><span>RECORDING SOURCE</span></div>

        <div className="control-grid">
          <button
            type="button"
            className={`action ${micSource === 'brownie' ? 'primary' : ''}`}
            onClick={() => setMicSource('brownie')}
          >
            🐕 Brownie microphone
          </button>
          <button
            type="button"
            className={`action ${micSource === 'device' ? 'primary' : ''}`}
            onClick={() => setMicSource('device')}
          >
            📱 This device microphone
          </button>
        </div>

        <div style={{ marginTop: '14px', lineHeight: 1.55, color: '#9da8b6' }}>
          {micSource === 'brownie'
            ? 'Secret-agent mode: capture audio using Brownie’s physical microphone. First pass records a 5-second clip directly into Recent.'
            : deviceMicAvailable
              ? 'Your browser can access this device microphone. Upload/record support is the next Voice step.'
              : 'Browser microphone capture needs HTTPS. It will become available when Brownie moves to the secure Tailscale/HTTPS connection.'}
        </div>

        <button
          type="button"
          className="action primary"
          onClick={recordBrownie}
          disabled={busy === 'record' || micSource === 'device'}
          style={{ marginTop: '16px', width: '100%' }}
        >
          {busy === 'record' ? '● Recording…' : micSource === 'brownie' ? '● Record 5s' : '● Record on this device'}
        </button>
      </section>

      <section className="card panel">
        <div className="section-title">
          <strong>Recordings</strong>
          <span>
            {recentPolicy
              ? `RECENT ${recent.length}/${recentPolicy.max_files} · ${formatBytes(recentPolicy.current_bytes)}`
              : 'RECENT + SAVED'}
          </span>
        </div>

        <div style={{ display: 'grid', gap: '20px' }}>
          <div>
            <div className="metric-key" style={{ marginBottom: '6px' }}>▾ Recent · auto-managed</div>
            {recent.length === 0
              ? <div className="metric-detail">No recent recordings yet.</div>
              : recent.map((item) => (
                  <RecordingRow
                    item={item}
                    busy={Boolean(busy)}
                    onPreview={previewRecording}
                    onPlay={playRecording}
                    onKeep={keepRecording}
                    onDelete={deleteRecording}
                    key={item.id}
                  />
                ))}
          </div>

          <div>
            <div className="metric-key" style={{ marginBottom: '6px' }}>▾ Saved · never auto-deleted</div>
            {saved.length === 0
              ? <div className="metric-detail">Keep a Recent recording and it will appear here.</div>
              : saved.map((item) => (
                  <RecordingRow
                    item={item}
                    busy={Boolean(busy)}
                    onPreview={previewRecording}
                    onPlay={playRecording}
                    onKeep={keepRecording}
                    onDelete={deleteRecording}
                    key={item.id}
                  />
                ))}
          </div>
        </div>
      </section>
    </div>
  )
}

export default VoiceScreen
