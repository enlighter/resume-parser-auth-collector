import React, { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiGet, apiPostJson, submitDocuments } from '../api'

export default function CandidateDetail() {
  const { id } = useParams()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')
  const [reqMsg, setReqMsg] = useState('')
  const [uploadMsg, setUploadMsg] = useState('')
  const [upProgress, setUpProgress] = useState(0)

  const panRef = useRef(null)
  const aadRef = useRef(null)
  const [panNumber, setPanNumber] = useState('')
  const [aadhaarNumber, setAadhaarNumber] = useState('')

  async function load() {
    try {
      const res = await apiGet(`/api/candidates/${id}`)
      setData(res)
    } catch (e) {
      setErr(String(e.message || e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [id])

  async function requestDocs(channel = 'EMAIL') {
    setReqMsg('Sending request…')
    try {
      const res = await apiPostJson(`/api/candidates/${id}/request-documents`, { channel })
      setReqMsg(`Request sent via ${res.channel}. Link: ${res.link}`)
    } catch (e) {
      setReqMsg(`Failed: ${String(e.message || e)}`)
    }
  }

  async function doSubmit() {
    setUploadMsg('Uploading…')
    setUpProgress(0)
    const panFile = panRef.current?.files?.[0]
    const aadFile = aadRef.current?.files?.[0]
    if (!panFile && !aadFile) {
      setUploadMsg('Select at least one file (PAN or Aadhaar) before uploading.')
      return
    }
    try {
      const res = await submitDocuments(
        id,
        {
          panFile: panFile,
          aadhaarFile: aadFile,
          panNumber,
          aadhaarNumber
        },
        (p) => setUpProgress(p)
      )
      setUploadMsg(`Submitted. Submission #${res.submission_id}`)
      await load()
    } catch (e) {
      setUploadMsg(`Failed: ${String(e.message || e)}`)
    }
  }

  if (loading) return <div className="card"><p>Loading…</p></div>
  if (err) return <div className="card"><p style={{ color: 'crimson' }}>{err}</p></div>
  if (!data) return null

  const p = data.profile || {}
  const skillItems = (p.skills || []).map(s => (
    <li key={s.name}>{s.name} <span className="badge">{(s.confidence * 100).toFixed(0)}%</span></li>
  ))

  return (
    <div className="grid">
      <div className="card">
        <h3>Candidate #{data.id}</h3>
        <div className="grid grid-2">
          <div className="field">
            <label>Name</label>
            <div>{p.name?.value || '-' } <span className="badge">{((p.name?.confidence || 0) * 100).toFixed(0)}%</span></div>
          </div>
          <div className="field">
            <label>Email</label>
            <div>{p.email?.value || '-'} <span className="badge">{((p.email?.confidence || 0) * 100).toFixed(0)}%</span></div>
            <div style={{ color: '#64748b', fontSize: 12 }}>masked: {p.email?.masked || '-'}</div>
          </div>
          <div className="field">
            <label>Phone</label>
            <div>{p.phone?.value || '-'} <span className="badge">{((p.phone?.confidence || 0) * 100).toFixed(0)}%</span></div>
            <div style={{ color: '#64748b', fontSize: 12 }}>masked: {p.phone?.masked || '-'}</div>
          </div>
          <div className="field">
            <label>Company</label>
            <div>{p.company?.value || '-'} <span className="badge">{((p.company?.confidence || 0) * 100).toFixed(0)}%</span></div>
          </div>
          <div className="field">
            <label>Designation</label>
            <div>{p.designation?.value || '-'} <span className="badge">{((p.designation?.confidence || 0) * 100).toFixed(0)}%</span></div>
          </div>
        </div>

        <div className="field" style={{ marginTop: 10 }}>
          <label>Skills</label>
          <ul>{skillItems}</ul>
        </div>

        <div className="row" style={{ gap: 8, marginTop: 16 }}>
          <button className="btn" onClick={() => requestDocs('EMAIL')}>Request docs via Email</button>
          <button className="btn secondary" onClick={() => requestDocs('SMS')}>Request via SMS</button>
          <div style={{ marginLeft: 8 }}>{reqMsg}</div>
        </div>
      </div>

      <div className="card">
        <h3>Submit Documents (staff or candidate)</h3>

        <div className="grid grid-2">
          <div className="field">
            <label>PAN image / PDF</label>
            <input type="file" ref={panRef} accept="image/*,application/pdf" />
          </div>
          <div className="field">
            <label>PAN Number (optional)</label>
            <input type="text" value={panNumber} onChange={(e) => setPanNumber(e.target.value.toUpperCase())} placeholder="ABCDE1234F" />
          </div>

          <div className="field">
            <label>Aadhaar image / PDF</label>
            <input type="file" ref={aadRef} accept="image/*,application/pdf" />
          </div>
          <div className="field">
            <label>Aadhaar Number (optional)</label>
            <input type="text" value={aadhaarNumber} onChange={(e) => setAadhaarNumber(e.target.value)} placeholder="1234 5678 9012" />
          </div>
        </div>

        <div className="row" style={{ marginTop: 12 }}>
          <button className="btn" onClick={doSubmit}>Upload</button>
          <div className="progress" style={{ flex: 1, maxWidth: 260, marginLeft: 10 }}>
            <div style={{ width: `${upProgress}%` }} />
          </div>
          <div style={{ marginLeft: 10 }}>{uploadMsg}</div>
        </div>

        <div style={{ marginTop: 12, color: '#64748b', fontSize: 13 }}>
          Uploaded files are accessible at <code>/media/</code> in DEBUG; do not expose in production.
        </div>
      </div>
    </div>
  )
}
