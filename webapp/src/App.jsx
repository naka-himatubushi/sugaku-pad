// Excalidraw を土台にした手書き数式 Solve アプリ。
// 描画→PNG化→/solve(ビジョンLLM OCR + SymPy)→ステップ表示。描き味/消しゴム/取消は Excalidraw 標準。
import { useState } from 'react'
import { Excalidraw, exportToBlob } from '@excalidraw/excalidraw'

export default function App() {
  const [api, setApi] = useState(null)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState(false)

  async function solve() {
    if (!api) return
    setBusy(true)
    try {
      const blob = await exportToBlob({
        elements: api.getSceneElements(),
        files: api.getFiles(),
        appState: { exportBackground: true, viewBackgroundColor: '#ffffff' },
        mimeType: 'image/png',
        exportPadding: 24,
      })
      const dataUrl = await new Promise((res) => {
        const fr = new FileReader()
        fr.onload = () => res(fr.result)
        fr.readAsDataURL(blob)
      })
      const r = await fetch('/solve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: dataUrl }),
      })
      setResult(await r.json())
    } catch (e) {
      setResult({ supported: false, latex: '', error: String(e), steps: [], answer: [] })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        <Excalidraw excalidrawAPI={(a) => setApi(a)} />
      </div>
      <div style={panel}>
        <button onClick={solve} disabled={busy} style={btn}>
          {busy ? '認識中…' : '✦ 数式を解く'}
        </button>
        {result && <Result r={result} />}
      </div>
    </div>
  )
}

function Result({ r }) {
  if (r.error) return <p style={{ color: '#b00' }}>エラー: {r.error}</p>
  if (!r.supported)
    return <p>⚠️ 認識: <code>{r.latex || '(空)'}</code> — 対応外/認識失敗。書き直すか整えて再試行してください。</p>
  return (
    <div>
      <div style={{ color: '#666', marginTop: 8 }}>
        認識: <code>{r.latex}</code>（種別: {r.kind}）
      </div>
      <ol style={{ margin: '6px 0 0', paddingLeft: '1.3em' }}>
        {r.steps.map((s, i) => <li key={i}>{s}</li>)}
      </ol>
      <div style={{ fontWeight: 600, fontSize: 18, marginTop: 6 }}>答え: {r.answer.join(', ')}</div>
    </div>
  )
}

const panel = {
  padding: 12,
  borderTop: '1px solid #e0e0e0',
  background: '#fff',
  maxHeight: '42vh',
  overflow: 'auto',
  font: '15px -apple-system, system-ui, sans-serif',
}
const btn = {
  fontSize: 16,
  padding: '10px 18px',
  borderRadius: 11,
  border: 0,
  background: '#007aff',
  color: '#fff',
}
