import React from 'react'
import { Routes, Route, Link } from 'react-router-dom'
import Upload from './components/Upload.jsx'
import Dashboard from './components/Dashboard.jsx'
import CandidateDetail from './components/CandidateDetail.jsx'

export default function App() {
  return (
    <>
      <header>
        <div className="container row" style={{ justifyContent: 'space-between' }}>
          <h3 style={{ margin: 0 }}><Link to="/" style={{ color: 'white', textDecoration: 'none' }}>Resume Agent</Link></h3>
          <nav className="row">
            <Link to="/" style={{ color: '#fff' }}>Dashboard</Link>
            <span style={{ color: '#64748b' }}>&nbsp;|&nbsp;</span>
            <Link to="/upload" style={{ color: '#fff' }}>Upload Resume</Link>
          </nav>
        </div>
      </header>

      <div className="container grid">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/candidates/:id" element={<CandidateDetail />} />
        </Routes>
      </div>
    </>
  )
}
