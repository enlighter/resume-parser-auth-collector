const API_BASE = import.meta.env.VITE_API_BASE || '' // '' uses vite proxy in dev

export async function apiGet(path) {
  const res = await fetch(`${API_BASE}${path}`)
  if (!res.ok) throw new Error(`GET ${path} failed: ${res.status}`)
  return res.json()
}

export async function apiPostJson(path, body) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {})
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`POST ${path} failed: ${res.status} ${text}`)
  }
  return res.json()
}

/** Upload with progress using XHR (fetch doesn't give upload progress) */
export function uploadFileWithProgress(path, formData, onProgress) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_BASE}${path}`)
    xhr.upload.onprogress = (evt) => {
      if (evt.lengthComputable && typeof onProgress === 'function') {
        onProgress(Math.round((evt.loaded / evt.total) * 100))
      }
    }
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText))
        } catch {
          resolve({})
        }
      } else {
        reject(new Error(`Upload failed: ${xhr.status} ${xhr.responseText}`))
      }
    }
    xhr.onerror = () => reject(new Error('Network error during upload'))
    xhr.send(formData)
  })
}

/** Submit documents (PAN/Aadhaar) with files and optional numbers */
export function submitDocuments(candidateId, { panFile, aadhaarFile, panNumber, aadhaarNumber }, onProgress) {
  const fd = new FormData()
  if (panFile) fd.append('pan_file', panFile)
  if (aadhaarFile) fd.append('aadhaar_file', aadhaarFile)
  if (panNumber) fd.append('pan_number', panNumber)
  if (aadhaarNumber) fd.append('aadhaar_number', aadhaarNumber)
  return uploadFileWithProgress(`/api/candidates/${candidateId}/submit-documents`, fd, onProgress)
}
