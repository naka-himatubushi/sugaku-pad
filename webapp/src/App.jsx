// Excalidraw を土台にした手書き数式 Solve アプリ。
// フロー: 描画 → 認識(/recognize) → 確認カード(編集可+KaTeXプレビュー) → 解く(/solve) → ステップ表示。
// ローカル LLM の認識は完璧でないので「人が確認・修正してから解く」= 滑らかな UX の核。
import { useState } from 'react'
import { Excalidraw, exportToBlob } from '@excalidraw/excalidraw'
import katex from 'katex'
import 'katex/dist/katex.min.css'

function Tex({ tex, display }) {
  let html = tex || ''
  try {
    html = katex.renderToString(tex || '', { throwOnError: false, displayMode: !!display })
  } catch (_) { /* 不正な LaTeX はそのまま文字表示 */ }
  return <span dangerouslySetInnerHTML={{ __html: html }} />
}

export default function App() {
  const [api, setApi] = useState(null)
  const [latex, setLatex] = useState('')
  const [recognized, setRecognized] = useState(false)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState('')

  async function exportPng() {
    const blob = await exportToBlob({
      elements: api.getSceneElements(),
      files: api.getFiles(),
      appState: { exportBackground: true, viewBackgroundColor: '#ffffff' },
      mimeType: 'image/png',
      exportPadding: 24,
    })
    return await new Promise((res) => {
      const fr = new FileReader()
      fr.onload = () => res(fr.result)
      fr.readAsDataURL(blob)
    })
  }

  async function recognize() {
    if (!api) return
    setBusy('認識中…'); setResult(null)
    try {
      const r = await fetch('/recognize', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: await exportPng() }),
      })
      const d = await r.json()
      setLatex(d.latex || ''); setRecognized(true)
    } catch (e) {
      setLatex(''); setRecognized(true)
    } finally { setBusy('') }
  }

  async function solve() {
    setBusy('計算中…')
    try {
      const r = await fetch('/solve', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ latex }),
      })
      setResult(await r.json())
    } finally { setBusy('') }
  }

  function reset() { setRecognized(false); setLatex(''); setResult(null) }

  return (
    <div style={{ position: 'fixed', inset: 0, display: 'flex', flexDirection: 'column' }}>
      <div style={{ flex: 1, minHeight: 0 }}>
        <Excalidraw excalidrawAPI={(a) => setApi(a)} />
      </div>
      <div style={panel}>
        {!recognized ? (
          <button onClick={recognize} disabled={!!busy} style={primary}>{busy || '✦ 認識する'}</button>
        ) : (
          <div>
            <div style={label}>認識結果（確認・修正できます）</div>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap', margin: '6px 0' }}>
              <input value={latex} onChange={(e) => setLatex(e.target.value)} style={input} placeholder="LaTeX" />
              <button onClick={solve} disabled={!!busy} style={primary}>{busy || '解く'}</button>
              <button onClick={recognize} disabled={!!busy} style={sec}>再認識</button>
              <button onClick={reset} disabled={!!busy} style={sec}>描き直す</button>
            </div>
            <div style={{ fontSize: 22, margin: '6px 0', minHeight: 28 }}><Tex tex={latex} /></div>
            {result && <Result r={result} />}
          </div>
        )}
      </div>
    </div>
  )
}

function Result({ r }) {
  if (!r.supported)
    return <p style={{ color: '#b00020' }}>⚠️ この式は解けません（対応外/認識ミス）。上の欄で直して「解く」を押してください。</p>
  const steps = r.steps_latex && r.steps_latex.length ? r.steps_latex : null
  const ans = r.answer_latex && r.answer_latex.length ? r.answer_latex : null
  return (
    <div style={{ marginTop: 6 }}>
      <div style={label}>種別: {r.kind}</div>
      <ol style={{ margin: '6px 0', paddingLeft: '1.3em', lineHeight: 2 }}>
        {steps
          ? steps.map((s, i) => (
              <li key={i}>{s.label}{s.latex ? <>: <Tex tex={s.latex} /></> : null}</li>
            ))
          : r.steps.map((s, i) => <li key={i}>{s}</li>)}
      </ol>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 8, flexWrap: 'wrap' }}>
        <span style={{ fontWeight: 700, fontSize: 18 }}>答え</span>
        <span style={{ fontSize: 24 }}>
          {ans
            ? ans.map((a, i) => <span key={i} style={{ marginRight: 14 }}><Tex tex={a} /></span>)
            : r.answer.join(', ')}
        </span>
      </div>
    </div>
  )
}

const panel = { padding: 12, borderTop: '1px solid #e0e0e0', background: '#fff', maxHeight: '46vh', overflow: 'auto', font: '15px -apple-system, system-ui, sans-serif' }
const label = { color: '#6e6e73', fontSize: 13 }
const input = { flex: 1, minWidth: 200, fontSize: 16, padding: '9px 11px', border: '1px solid #c7c7cc', borderRadius: 10 }
const primary = { fontSize: 16, padding: '10px 18px', borderRadius: 11, border: 0, background: '#007aff', color: '#fff' }
const sec = { fontSize: 15, padding: '9px 14px', borderRadius: 11, border: 0, background: '#e5e5ea', color: '#1d1d1f' }
