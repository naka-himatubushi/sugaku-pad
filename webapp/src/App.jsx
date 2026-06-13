// Excalidraw を土台にした手書き数式 Solve アプリ。
// フロー: 描画 → 認識(/recognize) → 確認カード(編集可) → 解く(/solve) → ステップ表示。
// 結果は Goodnotes AI 風に「サイドから開閉するドロワー」に、各数式/手順を独立した灰色カードで表示。
import { useState } from 'react'
import { Excalidraw, exportToBlob } from '@excalidraw/excalidraw'
import katex from 'katex'
import 'katex/dist/katex.min.css'

function Tex({ tex }) {
  let html = tex || ''
  try {
    html = katex.renderToString(tex || '', { throwOnError: false })
  } catch (_) { /* 不正な LaTeX はそのまま文字表示 */ }
  return <span dangerouslySetInnerHTML={{ __html: html }} />
}

// 各数式/行を囲う独立した灰色カード
function Card({ children, accent }) {
  return (
    <div style={{
      background: accent ? '#eef4ff' : '#fff',
      border: `1px solid ${accent ? '#bcd3ff' : '#e2e2e6'}`,
      borderRadius: 12, padding: '10px 12px', marginBottom: 10,
    }}>{children}</div>
  )
}

// 検算結果を表す簡易バッジアイコン（緑チェックのシール / 未検証は注意マーク）
function VerifiedMark({ ok }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" role="img" aria-label={ok ? '検算済み' : '未検証'}>
      <title>{ok ? '検算済み' : '未検証'}</title>
      <circle cx="12" cy="12" r="11" fill={ok ? '#1aa64b' : '#c99a00'} />
      {ok ? (
        <path d="M6.8 12.4l3.3 3.3L17.3 8.8" fill="none" stroke="#fff"
              strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" />
      ) : (
        <text x="12" y="17" textAnchor="middle" fontSize="15" fontWeight="700" fill="#fff">!</text>
      )}
    </svg>
  )
}

export default function App() {
  const [api, setApi] = useState(null)
  const [latex, setLatex] = useState('')
  const [recognized, setRecognized] = useState(false)
  const [result, setResult] = useState(null)
  const [busy, setBusy] = useState('')
  const [open, setOpen] = useState(false)

  async function exportPng() {
    const blob = await exportToBlob({
      elements: api.getSceneElements(),
      files: api.getFiles(),
      appState: { exportBackground: true, viewBackgroundColor: '#ffffff' },
      mimeType: 'image/png', exportPadding: 24,
    })
    return await new Promise((res) => {
      const fr = new FileReader()
      fr.onload = () => res(fr.result)
      fr.readAsDataURL(blob)
    })
  }

  async function recognize() {
    if (!api) return
    setBusy('認識中…'); setResult(null); setOpen(true)
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

  const steps = result && result.steps_latex && result.steps_latex.length ? result.steps_latex : null
  const ans = result && result.answer_latex && result.answer_latex.length ? result.answer_latex : null

  return (
    <div style={{ position: 'fixed', inset: 0 }}>
      <Excalidraw excalidrawAPI={(a) => setApi(a)} />

      {/* 開閉ハンドル（常時表示） */}
      <button onClick={() => setOpen((o) => !o)} style={handle(open)}>
        {open ? '✕ 閉じる' : '◀ 解答パネル'}
      </button>

      {/* サイドドロワー */}
      <div style={drawer(open)}>
        <Card>
          {!recognized ? (
            <button onClick={recognize} disabled={!!busy} style={primary}>{busy || '✦ 認識する'}</button>
          ) : (
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
              <button onClick={solve} disabled={!!busy} style={primary}>{busy || '解く'}</button>
              <button onClick={recognize} disabled={!!busy} style={sec}>再認識</button>
              <button onClick={reset} disabled={!!busy} style={sec}>描き直す</button>
            </div>
          )}
        </Card>

        {recognized && (
          <Card>
            <div style={label}>認識結果（修正できます）</div>
            <input value={latex} onChange={(e) => setLatex(e.target.value)} style={input} placeholder="LaTeX" />
            <div style={center(22)}><Tex tex={latex} /></div>
          </Card>
        )}

        {result && !result.supported && (
          <Card><p style={{ color: '#b00020', margin: 0 }}>⚠️ この式は解けません（対応外/認識ミス）。上で直して「解く」を。</p></Card>
        )}

        {result && result.supported && (
          <>
            <div style={{ ...label, margin: '2px 4px 6px' }}>種別: {result.kind}</div>
            {steps
              ? steps.map((s, i) => (
                  <Card key={i}>
                    <div style={label}>{i + 1}. {s.label}</div>
                    {s.latex ? <div style={center(18)}><Tex tex={s.latex} /></div> : null}
                  </Card>
                ))
              : result.steps.map((s, i) => <Card key={i}>{s}</Card>)}
            <Card accent>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={label}>答え</span>
                <VerifiedMark ok={result.verified} />
              </div>
              <div style={center(26)}>
                {ans
                  ? ans.map((a, i) => <span key={i} style={{ margin: '0 10px' }}><Tex tex={a} /></span>)
                  : result.answer.join(', ')}
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  )
}

const DW = 'min(420px, 92vw)'
const drawer = (open) => ({
  position: 'fixed', top: 0, right: 0, bottom: 0, width: DW,
  background: '#f4f4f7', boxShadow: '-2px 0 14px rgba(0,0,0,.14)',
  transform: open ? 'translateX(0)' : 'translateX(101%)',
  transition: 'transform .28s ease', overflowY: 'auto',
  padding: '60px 14px 24px', zIndex: 900,
  font: '15px -apple-system, system-ui, sans-serif', boxSizing: 'border-box',
})
const handle = (open) => ({
  position: 'fixed', top: 14, right: open ? `calc(${DW} - 4px)` : '14px',
  transform: open ? 'translateX(calc(-100% - 10px))' : 'none',
  transition: 'right .28s ease', zIndex: 1000,
  fontSize: 14, padding: '8px 12px', borderRadius: 10, border: 0,
  background: '#1d1d1f', color: '#fff',
})
const label = { color: '#6e6e73', fontSize: 13 }
const center = (size) => ({ fontSize: size, margin: '6px 0', textAlign: 'center' })
const input = { width: '100%', boxSizing: 'border-box', fontSize: 16, padding: '9px 11px', border: '1px solid #c7c7cc', borderRadius: 10, margin: '6px 0' }
const primary = { fontSize: 16, padding: '10px 18px', borderRadius: 11, border: 0, background: '#007aff', color: '#fff' }
const sec = { fontSize: 15, padding: '9px 14px', borderRadius: 11, border: 0, background: '#e5e5ea', color: '#1d1d1f' }
