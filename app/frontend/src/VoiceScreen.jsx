import { useEffect, useMemo, useRef, useState } from 'react'

const DEVICE_RECORD_MAX_SECONDS = 180

function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 KB'
  if (bytes < 1024 * 1024) return `${Math.max(1, Math.round(bytes / 1024))} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDuration(seconds) {
  const safe = Math.max(0, Math.floor(Number(seconds) || 0))
  const minutes = Math.floor(safe / 60)
  const remainder = safe % 60
  return `${minutes}:${String(remainder).padStart(2, '0')}`
}

function pickDeviceMimeType() {
  if (typeof MediaRecorder === 'undefined') return ''

  const candidates = [
    'audio/webm;codecs=opus',
    'audio/mp4;codecs=mp4a.40.2',
    'audio/mp4',
    'audio/webm',
    'audio/ogg;codecs=opus',
  ]
  return candidates.find((type) => MediaRecorder.isTypeSupported(type)) || ''
}

function RecordingRow({ item, busy, onPreview, onPlay, onKeep, onDelete }) {
  const sourceIcon = item.source === 'device' ? '📱' : item.source === 'brownie' ? '🐕' : '🎤'
  const sourceLabel = item.source === 'device'
    ? 'This device microphone'
    : item.source === 'brownie'
      ? 'Brownie microphone'
      : 'Recording'
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
        <span>{sourceLabel}{duration} · {formatBytes(item.bytes)}</span>
      </div>

      <div style={{ display: 'flex', gap: '7px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
        <button type="button" className="action" onClick={() => onPreview(item)} disabled={busy}>This device ▶</button>
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
  const [recordingActive, setRecordingActive] = useState(false)
  const [recordingSource, setRecordingSource] = useState(null)
  const [recordingElapsed, setRecordingElapsed] = useState(0)
  const [recordingMaxSeconds, setRecordingMaxSeconds] = useState(DEVICE_RECORD_MAX_SECONDS)
  const localAudioRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const mediaStreamRef = useRef(null)
  const deviceChunksRef = useRef([])
  const deviceStopTimerRef = useRef(null)
  const deviceStartedAtRef = useRef(null)
  const discardDeviceRecordingRef = useRef(false)

  const recent = useMemo(() => recordings.filter((item) => !item.saved), [recordings])
  const saved = useMemo(() => recordings.filter((item) => item.saved), [recordings])
  const selectedRecording = useMemo(
    () => recordings.find((item) => item.id === selectedRecordingId) || null,
    [recordings, selectedRecordingId],
  )
  const deviceMicAvailable = window.isSecureContext
    && typeof MediaRecorder !== 'undefined'
    && Boolean(navigator.mediaDevices?.getUserMedia)

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

  const fetchRecordingStatus = async () => {
    try {
      const response = await fetch('/api/voice/recordings/record-status', { cache: 'no-store' })
      if (!response.ok) return null
      return await response.json()
    } catch {
      return null
    }
  }

  const stopDeviceTracks = () => {
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((track) => track.stop())
      mediaStreamRef.current = null
    }
  }

  useEffect(() => {
    let cancelled = false

    const initialize = async () => {
      await refresh()
      const status = await fetchRecordingStatus()
      if (!cancelled && status?.active === true) {
        setMicSource('brownie')
        setRecordingActive(true)
        setRecordingSource('brownie')
        setRecordingElapsed(Number(status.elapsed_seconds) || 0)
        setRecordingMaxSeconds(Number(status.max_seconds) || DEVICE_RECORD_MAX_SECONDS)
      }
    }

    initialize()
    return () => {
      cancelled = true
      if (localAudioRef.current) {
        localAudioRef.current.pause()
        localAudioRef.current = null
      }
      if (deviceStopTimerRef.current) {
        window.clearTimeout(deviceStopTimerRef.current)
        deviceStopTimerRef.current = null
      }
      discardDeviceRecordingRef.current = true
      const recorder = mediaRecorderRef.current
      if (recorder && recorder.state !== 'inactive') {
        recorder.ondataavailable = null
        recorder.onstop = null
        try {
          recorder.stop()
        } catch {
          // Browser capture is best-effort during component teardown.
        }
      }
      mediaRecorderRef.current = null
      stopDeviceTracks()
    }
  }, [])

  useEffect(() => {
    if (!recordingActive || recordingSource !== 'brownie') return undefined

    let cancelled = false

    const pollStatus = async () => {
      const status = await fetchRecordingStatus()
      if (cancelled || !status) return

      setRecordingElapsed(Number(status.elapsed_seconds) || 0)
      setRecordingMaxSeconds(Number(status.max_seconds) || DEVICE_RECORD_MAX_SECONDS)

      if (status.active !== true) {
        setRecordingActive(false)
        setRecordingSource(null)
        setRecordingElapsed(0)
        await refresh()
        if (!cancelled) onToast('Recording saved to Recent')
      }
    }

    const interval = window.setInterval(pollStatus, 1000)
    return () => {
      cancelled = true
      window.clearInterval(interval)
    }
  }, [recordingActive, recordingSource])

  useEffect(() => {
    if (!recordingActive || recordingSource !== 'device') return undefined

    const updateElapsed = () => {
      if (deviceStartedAtRef.current == null) return
      const elapsed = Math.floor((Date.now() - deviceStartedAtRef.current) / 1000)
      setRecordingElapsed(Math.min(DEVICE_RECORD_MAX_SECONDS, Math.max(0, elapsed)))
    }

    updateElapsed()
    const interval = window.setInterval(updateElapsed, 250)
    return () => window.clearInterval(interval)
  }, [recordingActive, recordingSource])

  const playSpeakerSelection = async () => {
    setBusy('play')
    try {
      let response
      if (speakerSource === 'pidog') {
        if (!selectedSound) throw new Error('No default sound selected')
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
      onToast('Brownie speaker playback failed')
    } finally {
      setBusy('')
    }
  }

  const playUrlOnThisDevice = async (url, successMessage = 'Playing on this device') => {
    try {
      if (localAudioRef.current) localAudioRef.current.pause()
      const audio = new Audio(url)
      localAudioRef.current = audio
      await audio.play()
      onToast(successMessage)
    } catch {
      onToast('Playback unavailable on this device')
    }
  }

  const playSpeakerSelectionOnThisDevice = async () => {
    if (speakerSource === 'pidog') {
      if (!selectedSound) {
        onToast('Choose a Default Sound first')
        return
      }
      await playUrlOnThisDevice(`/api/voice/sounds/file/${encodeURIComponent(selectedSound)}`)
      return
    }

    if (!selectedRecording) {
      onToast('Choose a recording first')
      return
    }
    await playUrlOnThisDevice(selectedRecording.preview_url)
  }

  const startBrownieRecording = async () => {
    setBusy('record')
    try {
      const response = await fetch('/api/voice/recordings/record-brownie/start', {
        method: 'POST',
        cache: 'no-store',
      })
      if (!response.ok) throw new Error(`Record ${response.status}`)
      const data = await response.json()
      setRecordingActive(true)
      setRecordingSource('brownie')
      setRecordingElapsed(0)
      setRecordingMaxSeconds(Number(data.max_seconds) || DEVICE_RECORD_MAX_SECONDS)
      onToast('Brownie microphone recording started')
    } catch {
      onToast('Brownie microphone recording failed to start')
    } finally {
      setBusy('')
    }
  }

  const stopBrownieRecording = async () => {
    setBusy('record')
    try {
      const response = await fetch('/api/voice/recordings/record-brownie/stop', {
        method: 'POST',
        cache: 'no-store',
      })
      if (!response.ok) throw new Error(`Stop ${response.status}`)
      setRecordingActive(false)
      setRecordingSource(null)
      setRecordingElapsed(0)
      await refresh()
      onToast('Recording saved to Recent')
    } catch {
      onToast('Could not stop Brownie microphone recording')
    } finally {
      setBusy('')
    }
  }

  const uploadDeviceRecording = async (blob) => {
    setBusy('record')
    try {
      const response = await fetch('/api/voice/recordings/upload-device', {
        method: 'POST',
        headers: {
          'Content-Type': blob.type || 'application/octet-stream',
        },
        body: blob,
        cache: 'no-store',
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => null)
        throw new Error(errorData?.detail || `Upload ${response.status}`)
      }

      await refresh()
      onToast('This device recording saved to Recent')
    } catch (error) {
      onToast(error?.message || 'This device recording upload failed')
    } finally {
      setBusy('')
    }
  }

  const startDeviceRecording = async () => {
    if (!deviceMicAvailable) {
      onToast('This device microphone requires HTTPS and browser microphone support')
      return
    }

    setBusy('record')
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      })
      mediaStreamRef.current = stream

      const mimeType = pickDeviceMimeType()
      const options = mimeType
        ? { mimeType, audioBitsPerSecond: 128000 }
        : { audioBitsPerSecond: 128000 }
      const recorder = new MediaRecorder(stream, options)

      mediaRecorderRef.current = recorder
      deviceChunksRef.current = []
      discardDeviceRecordingRef.current = false

      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) deviceChunksRef.current.push(event.data)
      }

      recorder.onerror = () => {
        onToast('This device microphone recording failed')
      }

      recorder.onstop = async () => {
        if (deviceStopTimerRef.current) {
          window.clearTimeout(deviceStopTimerRef.current)
          deviceStopTimerRef.current = null
        }

        const chunks = deviceChunksRef.current
        deviceChunksRef.current = []
        mediaRecorderRef.current = null
        deviceStartedAtRef.current = null
        stopDeviceTracks()
        setRecordingActive(false)
        setRecordingSource(null)
        setRecordingElapsed(0)

        if (discardDeviceRecordingRef.current) return

        const blobType = recorder.mimeType || chunks[0]?.type || mimeType || 'audio/webm'
        const blob = new Blob(chunks, { type: blobType })
        if (blob.size === 0) {
          setBusy('')
          onToast('This device recording was empty')
          return
        }

        await uploadDeviceRecording(blob)
      }

      recorder.start(1000)
      deviceStartedAtRef.current = Date.now()
      setRecordingActive(true)
      setRecordingSource('device')
      setRecordingElapsed(0)
      setRecordingMaxSeconds(DEVICE_RECORD_MAX_SECONDS)
      setBusy('')
      onToast('This device microphone recording started')

      deviceStopTimerRef.current = window.setTimeout(() => {
        if (recorder.state !== 'inactive') {
          setBusy('record')
          recorder.stop()
        }
      }, DEVICE_RECORD_MAX_SECONDS * 1000)
    } catch (error) {
      stopDeviceTracks()
      mediaRecorderRef.current = null
      setBusy('')
      if (error?.name === 'NotAllowedError') {
        onToast('Microphone permission was denied')
      } else {
        onToast('Could not start this device microphone')
      }
    }
  }

  const stopDeviceRecording = () => {
    const recorder = mediaRecorderRef.current
    if (!recorder || recorder.state === 'inactive') return
    setBusy('record')
    recorder.stop()
  }

  const toggleRecording = async () => {
    if (recordingActive) {
      if (recordingSource === 'device') {
        stopDeviceRecording()
      } else {
        await stopBrownieRecording()
      }
      return
    }

    if (micSource === 'device') {
      await startDeviceRecording()
    } else {
      await startBrownieRecording()
    }
  }

  const previewRecording = (item) => {
    const source = item.source === 'brownie' ? 'Brownie mic' : item.source === 'device' ? 'this device mic' : 'recording'
    playUrlOnThisDevice(item.preview_url, `Playing ${source} on this device`)
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
          <p>Play Default Sounds, record from Brownie or this device, and manage recordings without cluttering Control.</p>
        </div>
        <span className="sim-badge">AUDIO LIVE</span>
      </div>

      <section className="card panel">
        <div className="section-title"><strong>Speaker</strong><span>SOUNDBOARD</span></div>

        <div style={{ display: 'grid', gridTemplateColumns: 'minmax(160px, 0.7fr) minmax(240px, 1.3fr)', gap: '12px' }}>
          <div>
            <span className="metric-key">Sound source</span>
            <select value={speakerSource} onChange={(event) => setSpeakerSource(event.target.value)} style={selectStyle}>
              <option value="pidog">Default Sounds</option>
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
                    {item.saved ? 'Saved' : 'Recent'} · {item.source === 'brownie' ? 'Brownie mic' : item.source === 'device' ? 'This device' : 'Recording'} · {item.name}
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

        <div className="control-grid" style={{ marginTop: '16px' }}>
          <button
            type="button"
            className="action primary"
            onClick={playSpeakerSelection}
            disabled={busy === 'play' || (speakerSource === 'recordings' && !selectedRecordingId)}
          >
            {busy === 'play' ? 'Playing…' : '▶ Play on Brownie'}
          </button>
          <button
            type="button"
            className="action"
            onClick={playSpeakerSelectionOnThisDevice}
            disabled={(speakerSource === 'pidog' && !selectedSound) || (speakerSource === 'recordings' && !selectedRecordingId)}
          >
            ▶ Play on this device
          </button>
        </div>
      </section>

      <section className="card panel">
        <div className="section-title">
          <strong>Microphone</strong>
          <span>{recordingActive ? `${formatDuration(recordingElapsed)} / ${formatDuration(recordingMaxSeconds)}` : 'RECORDING SOURCE'}</span>
        </div>

        <div className="control-grid">
          <button
            type="button"
            className={`action ${micSource === 'brownie' ? 'primary' : ''}`}
            onClick={() => setMicSource('brownie')}
            disabled={recordingActive}
          >
            🐕 Brownie microphone
          </button>
          <button
            type="button"
            className={`action ${micSource === 'device' ? 'primary' : ''}`}
            onClick={() => setMicSource('device')}
            disabled={recordingActive}
          >
            📱 This device microphone
          </button>
        </div>

        <button
          type="button"
          className={`action ${recordingActive ? 'danger' : 'primary'}`}
          onClick={toggleRecording}
          disabled={busy === 'record' || (!recordingActive && micSource === 'device' && !deviceMicAvailable)}
          title={micSource === 'device' && !deviceMicAvailable ? 'This device microphone requires HTTPS and browser microphone support' : undefined}
          style={{ marginTop: '16px', width: '100%' }}
        >
          {busy === 'record'
            ? 'Working…'
            : recordingActive
              ? `■ Stop · ${formatDuration(recordingElapsed)}`
              : micSource === 'brownie'
                ? '● Record'
                : '● Record on this device'}
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
