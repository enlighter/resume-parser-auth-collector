import React, { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiGet } from '../api'

export default function Dashboard() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState('')

  useEffect(() => {
    let cancel = false
    async function load() {
      try {
        const data = await apiGet('/api/candidates')
        if (!cancel) {
          setRows(data.results || data)
        }
      } catch (e) {
        if (!cancel) setErr(String(e.message || e))
      } finally {
        if (!cancel) setLoading(false)
      }
    }
    load()
    const id = setInterval(load, 4000) // gentle poll to see parsed updates
    return () => { cancel = true; clearInterval(id) }
  }, [])

  return (
    <div className="card">
      <div className="row" style={{ justifyContent: 'space-between' }}>
        <h3>Candidates</h3>
        <Link className="btn" to="/upload">+ Upload Resume</Link>
      </div>
      {loading && <p>Loading…</p>}
      {err && <p style={{ color: 'crimson' }}>{err}</p>}
      {!loading && (
        <table className="table">
          <thead>
            <tr>
              <th>ID</th><th>Name</th><th>Email (masked)</th><th>Company</th><th>Status</th><th></th>
            </tr>
          </thead>
          <tbody>
            {(rows || []).map(c => (
              <tr key={c.id}>
                <td>{c.id}</td>
                <td>{c.name || '-'}</td>
                <td>{c.email || '-'}</td>
                <td>{c.latest_company || '-'}</td>
                <td><span className="badge">{c.extraction_status}</span></td>
                <td><Link to={`/candidates/${c.id}`}>View</Link></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
