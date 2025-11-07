import React, { useRef, useState } from 'react'
import { uploadFileWithProgress } from '../api'

export default function Upload() {
  const [progress, setProgress] = useState(0)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const fileInput = useRef(null)

  const onDrop = async (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file) await doUpload(file)
  }

  const onPick = async (e) => {
    const file = e.target.files?.[0]
    if (file) await doUpload(file)
  }

  async function doUpload(file) {
    setMsg('')
    setBusy(true)
    setProgress(0)
    const fd = new FormData()
    fd.append('file', file)
    try {
      const res = await uploadFileWithProgress('/api/candidates/upload', fd, (p) => setProgress(p))
      setMsg(`Uploaded. Candidate #${res.candidate_id} parsing…`)
    } catch (err) {
      setMsg(String(err.message || err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <h3>Upload Resume</h3>
      <div
        className="dropzone"
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
      >
        <p>Drag & drop PDF or DOCX here</p>
        <p>— or —</p>
        <label className="label-file">
          Choose file
          <input
            className="upload-input"
            type="file"
            accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={onPick}
            ref={fileInput}
          />
        </label>
      </div>

      <div style={{ marginTop: 12 }}>
        <div className="progress"><div style={{ width: `${progress}%` }} /></div>
        <div style={{ marginTop: 8, minHeight: 24 }}>{busy ? `Uploading… ${progress}%` : msg}</div>
      </div>
    </div>
  )
}
