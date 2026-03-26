import { useState, useEffect, useCallback } from 'react'
import {
  LayoutDashboard, Database, TrendingUp, Calculator,
  Settings, History, Calendar, RefreshCw, Download
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, RadarChart, Radar, PolarGrid,
  PolarAngleAxis, PolarRadiusAxis, BarChart, Bar, Cell
} from 'recharts'
import {
  predictJornada, optimizeColumns, getKelly, getRoi,
  demoMatches, type PredictResult, type KellyResult, type OptimizeResult
} from './api'

type Tab = 'dashboard' | 'predictor' | 'optimizer' | 'financiero'

function App() {
  const [activeTab, setActiveTab] = useState<Tab>('dashboard')
  const [loading, setLoading] = useState(false)
  
  // State
  const [predictions, setPredictions] = useState<PredictResult[]>([])
  const [optimized, setOptimized] = useState<OptimizeResult | null>(null)
  const [kelly, setKelly] = useState<KellyResult | null>(null)
  const [roi10, setRoi10] = useState<any>(null)
  const [roi60, setRoi60] = useState<any>(null)
  const [selectedReduction, setSelectedReduction] = useState('R1')
  const [bankroll, setBankroll] = useState(500)

  const loadDashboard = useCallback(async () => {
    setLoading(true)
    try {
      const matches = demoMatches()
      const [preds, r10, r60] = await Promise.all([
        predictJornada(matches),
        getRoi(10),
        getRoi(60)
      ])
      setPredictions(preds)
      setRoi10(r10)
      setRoi60(r60)

      // Kelly usando la prob media más alta de la jornada
      const avgWin = preds.reduce((acc, p) => acc + Math.max(p.prob_1, p.prob_X, p.prob_2), 0) / preds.length
      const k = await getKelly(avgWin, 40000, bankroll)
      setKelly(k)
    } catch (e) {
      console.error('Error cargando datos de la API:', e)
    }
    setLoading(false)
  }, [bankroll])

  const runOptimizer = async () => {
    setLoading(true)
    try {
      const matches = demoMatches()
      const result = await optimizeColumns(matches, selectedReduction)
      setOptimized(result)
    } catch (e) {
      console.error('Error optimizando:', e)
    }
    setLoading(false)
  }

  useEffect(() => { loadDashboard() }, [loadDashboard])

  const roiChartData = roi10 ? [
    { name: '10 J.', roi: roi10['roi_%'] ?? 0, color: (roi10['roi_%'] ?? 0) >= 0 ? '#22c55e' : '#ef4444' },
    { name: '60 J.', roi: roi60?.['roi_%'] ?? 0, color: (roi60?.['roi_%'] ?? 0) >= 0 ? '#22c55e' : '#ef4444' },
  ] : []

  const signChartData = predictions.slice(0, 8).map((p, i) => ({
    name: `P${i + 1}`,
    '1': Math.round(p.prob_1 * 100),
    X: Math.round(p.prob_X * 100),
    '2': Math.round(p.prob_2 * 100),
  }))

  return (
    <div className="flex min-h-screen w-full bg-[#0f172a] text-slate-200 font-sans antialiased">
      {/* Sidebar */}
      <aside className="w-60 border-r border-slate-800 bg-[#1e293b]/60 backdrop-blur-xl p-5 flex flex-col gap-6 shrink-0">
        <div className="flex items-center gap-2.5 px-1">
          <div className="p-2 bg-indigo-600 rounded-lg shadow-lg shadow-indigo-600/30">
            <TrendingUp size={20} className="text-white" />
          </div>
          <h1 className="font-bold text-lg tracking-tight text-white">
            Quiniela<span className="text-indigo-400">Pro</span>
          </h1>
        </div>

        <nav className="flex flex-col gap-1">
          <NavItem icon={<LayoutDashboard size={17} />} label="Dashboard" active={activeTab === 'dashboard'} onClick={() => setActiveTab('dashboard')} />
          <NavItem icon={<Calendar size={17} />} label="Predictor" active={activeTab === 'predictor'} onClick={() => setActiveTab('predictor')} />
          <NavItem icon={<Calculator size={17} />} label="Optimizador" active={activeTab === 'optimizer'} onClick={() => setActiveTab('optimizer')} />
          <NavItem icon={<History size={17} />} label="Financiero" active={activeTab === 'financiero'} onClick={() => setActiveTab('financiero')} />
        </nav>

        <div className="mt-auto p-3.5 bg-indigo-950/50 border border-indigo-500/20 rounded-xl">
          <div className="flex items-center gap-2 mb-1.5">
            <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse" />
            <span className="text-[11px] font-semibold text-indigo-300 uppercase tracking-wider">API Activa</span>
          </div>
          <p className="text-[11px] text-indigo-200/50 leading-relaxed">
            Motor PCA + Logit entrenado · Puerto 8000
          </p>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 p-7 overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-2xl font-bold text-white mb-1">
              {activeTab === 'dashboard' && 'Resumen de Jornada'}
              {activeTab === 'predictor' && 'Predictor 1X2'}
              {activeTab === 'optimizer' && 'Optimizador de Columnas'}
              {activeTab === 'financiero' && 'Análisis Financiero'}
            </h2>
            <p className="text-slate-400 text-sm">Motor estadístico · Temporada 24/25</p>
          </div>
          <button
            onClick={loadDashboard}
            disabled={loading}
            id="sync-btn"
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl font-medium text-sm shadow-lg shadow-indigo-500/25 transition-all cursor-pointer"
          >
            <RefreshCw size={15} className={loading ? 'animate-spin' : ''} />
            {loading ? 'Cargando...' : 'Sincronizar'}
          </button>
        </div>

        {/* ─── DASHBOARD ────────────────────────────────────────────────────── */}
        {activeTab === 'dashboard' && (
          <>
            {/* Stat cards */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-7">
              <StatCard title="Prob. Media" value={predictions.length ? `${(predictions.reduce((a,p) => a + Math.max(p.prob_1,p.prob_X,p.prob_2),0)/predictions.length*100).toFixed(1)}%` : '–'} sub="Signo más probable" color="text-indigo-400" />
              <StatCard title="ROI (10 J.)" value={roi10 ? `${roi10['roi_%']}%` : '–'} sub="Últimas 10 jornadas" color={roi10?.['roi_%'] >= 0 ? 'text-green-400' : 'text-red-400'} />
              <StatCard title="ROI (60 J.)" value={roi60 ? `${roi60['roi_%']}%` : '–'} sub="Últimas 60 jornadas" color={roi60?.['roi_%'] >= 0 ? 'text-green-400' : 'text-red-400'} />
              <StatCard title="Kelly Apuesta" value={kelly ? `€${kelly.apuesta_euros}` : '–'} sub={kelly?.riesgo ?? ''} color="text-amber-400" />
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Prob chart */}
              <div className="lg:col-span-2 bg-[#1e293b]/60 border border-slate-800 p-5 rounded-2xl">
                <h3 className="text-sm font-semibold mb-4 flex items-center gap-2">
                  <TrendingUp size={15} className="text-indigo-400" /> Probabilidades 1X2 · Partidos 1–8
                </h3>
                <div className="h-[260px]">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={signChartData} barSize={8}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                      <XAxis dataKey="name" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} unit="%" />
                      <Tooltip contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 10 }} itemStyle={{ color: '#e2e8f0' }} />
                      <Bar dataKey="1" fill="#6366f1" radius={[4,4,0,0]} />
                      <Bar dataKey="X" fill="#94a3b8" radius={[4,4,0,0]} />
                      <Bar dataKey="2" fill="#f43f5e" radius={[4,4,0,0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* ROI panel */}
              <div className="bg-[#1e293b]/60 border border-slate-800 p-5 rounded-2xl flex flex-col gap-4">
                <h3 className="text-sm font-semibold flex items-center gap-2">
                  <History size={15} className="text-indigo-400" /> ROI por Período
                </h3>
                {roiChartData.map(d => (
                  <div key={d.name} className="bg-slate-800/50 rounded-xl p-4">
                    <div className="flex justify-between mb-1">
                      <span className="text-xs text-slate-400">{d.name}</span>
                      <span className={`text-sm font-bold ${d.roi >= 0 ? 'text-green-400' : 'text-red-400'}`}>{d.roi}%</span>
                    </div>
                    <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${d.roi >= 0 ? 'bg-green-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(Math.abs(d.roi), 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
                {kelly && (
                  <div className="bg-indigo-950/40 border border-indigo-500/20 rounded-xl p-4">
                    <p className="text-xs text-indigo-300 mb-1">Kelly Edge</p>
                    <p className="text-xl font-bold text-white">{kelly.edge.toFixed(2)}</p>
                    <p className="text-xs text-slate-500 mt-1">E[X] = {kelly.esperanza_matematica.toFixed(2)} €</p>
                  </div>
                )}
              </div>
            </div>
          </>
        )}

        {/* ─── PREDICTOR ────────────────────────────────────────────────────── */}
        {activeTab === 'predictor' && (
          <div className="space-y-3">
            {predictions.length === 0 && (
              <p className="text-slate-500">Haz clic en "Sincronizar" para cargar las predicciones.</p>
            )}
            {predictions.map(p => (
              <div key={p.partido} className="bg-[#1e293b]/60 border border-slate-700/50 p-4 rounded-xl flex items-center gap-6">
                <span className="w-8 text-xs font-bold text-indigo-400">#P{p.partido}</span>
                <div className="flex-1 flex gap-2">
                  {['1', 'X', '2'].map(signo => {
                    const prob = signo === '1' ? p.prob_1 : signo === 'X' ? p.prob_X : p.prob_2
                    const isMax = p.signo_mas_probable === signo
                    return (
                      <div key={signo} className={`flex-1 flex flex-col items-center p-2 rounded-lg ${isMax ? 'bg-indigo-600/20 border border-indigo-500/30' : 'bg-slate-800/40'}`}>
                        <span className={`text-xs font-bold ${isMax ? 'text-indigo-300' : 'text-slate-400'}`}>{signo}</span>
                        <span className={`text-sm font-bold ${isMax ? 'text-white' : 'text-slate-300'}`}>{(prob * 100).toFixed(1)}%</span>
                      </div>
                    )
                  })}
                </div>
                <div className="text-right">
                  <p className="text-[10px] text-slate-500">P15</p>
                  <p className="text-xs font-mono font-bold text-amber-400">{p.pleno15_resultado}</p>
                  <p className="text-[10px] text-slate-500">{(p.pleno15_prob*100).toFixed(1)}%</p>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ─── OPTIMIZADOR ──────────────────────────────────────────────────── */}
        {activeTab === 'optimizer' && (
          <div className="space-y-5">
            <div className="flex gap-3 flex-wrap">
              {['R1','R2','R3','R4','R5','R6'].map(r => (
                <button
                  key={r} id={`reduction-${r}`}
                  onClick={() => setSelectedReduction(r)}
                  className={`px-5 py-2 rounded-xl text-sm font-bold transition-all cursor-pointer ${selectedReduction === r ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-600/30' : 'bg-slate-800 text-slate-400 hover:text-white'}`}
                >{r}</button>
              ))}
              <button
                id="run-optimizer-btn"
                onClick={runOptimizer}
                disabled={loading}
                className="ml-auto flex items-center gap-2 px-5 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white rounded-xl text-sm font-bold shadow-lg shadow-green-600/20 transition-all cursor-pointer"
              >
                <Calculator size={15} />
                Generar Columnas
              </button>
            </div>

            {optimized && (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <StatCard title="Columnas Generadas" value={`${optimized.columnas_generadas}`} sub={`Reducción ${optimized.reduccion}`} color="text-indigo-400" />
                  <StatCard title="Tras Megaquin" value={`${optimized.columnas_filtradas_megaquin}`} sub="Filtros aplicados" color="text-amber-400" />
                  <StatCard title="Finales (Hamming)" value={`${optimized.columnas_finales}`} sub="Diversidad garantizada" color="text-green-400" />
                  <StatCard title="Garantía Aciertos" value={`≥${optimized.garantia_aciertos}`} sub="Si pronósticos entran" color="text-indigo-400" />
                </div>
                <div className="bg-[#1e293b]/60 border border-slate-800 rounded-2xl p-5">
                  <div className="flex justify-between items-center mb-4">
                    <h3 className="text-sm font-semibold">Columnas Generadas</h3>
                    <button id="download-qui-btn" onClick={() => { const url = `${import.meta.env.VITE_API_URL ?? 'http://localhost:8000'}/download-qui`; window.open(url, '_blank') }} className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded-lg text-xs font-medium transition-all cursor-pointer">
                      <Download size={13} /> Descargar .qui
                    </button>
                  </div>
                  <div className="space-y-2 font-mono text-sm">
                    {optimized.columnas.map((col, i) => (
                      <div key={i} className="flex gap-1.5 items-center">
                        <span className="text-[10px] text-slate-600 w-5">{i+1}</span>
                        {col.split(' ').map((s, j) => (
                          <span key={j} className={`w-7 h-7 flex items-center justify-center rounded-lg text-xs font-bold ${s === '1' ? 'bg-indigo-600/30 text-indigo-300' : s === 'X' ? 'bg-slate-700 text-slate-300' : 'bg-rose-600/30 text-rose-300'}`}>
                            {s}
                          </span>
                        ))}
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}

        {/* ─── FINANCIERO ───────────────────────────────────────────────────── */}
        {activeTab === 'financiero' && (
          <div className="space-y-5">
            <div className="flex items-center gap-4 bg-[#1e293b]/60 border border-slate-800 p-5 rounded-2xl">
              <label className="text-sm text-slate-400 shrink-0">Bankroll (€)</label>
              <input
                id="bankroll-input"
                type="number" value={bankroll}
                onChange={e => setBankroll(Number(e.target.value))}
                className="flex-1 bg-slate-800 border border-slate-700 rounded-xl px-4 py-2 text-white text-sm focus:outline-none focus:border-indigo-500"
              />
              <button id="recalculate-kelly-btn" onClick={loadDashboard} disabled={loading} className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white rounded-xl text-sm font-medium transition-all cursor-pointer">Recalcular</button>
            </div>

            {kelly && (
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <StatCard title="Esperanza E[X]" value={`€${kelly.esperanza_matematica.toFixed(2)}`} sub="Por columna" color="text-indigo-400" />
                <StatCard title="Edge" value={`${kelly.edge.toFixed(2)}`} sub="Ventaja sobre mercado" color="text-green-400" />
                <StatCard title="Kelly Apuesta" value={`€${kelly.apuesta_euros}`} sub={kelly.riesgo} color="text-amber-400" />
                <StatCard title="f* completo" value={`${(kelly.f_star_full * 100).toFixed(2)}%`} sub="Fracción Kelly teórica" color="text-indigo-400" />
                <StatCard title="f* fraccional" value={`${(kelly.f_star_frac * 100).toFixed(2)}%`} sub="Fracción conservadora (25%)" color="text-indigo-400" />
              </div>
            )}

            {roi10 && roi60 && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[{ data: roi10, label: '10 Jornadas' }, { data: roi60, label: '60 Jornadas' }].map(({ data, label }) => (
                  <div key={label} className="bg-[#1e293b]/60 border border-slate-800 p-5 rounded-2xl">
                    <h3 className="text-sm font-semibold mb-4">{label}</h3>
                    <div className="space-y-2 text-sm">
                      <Row label="Invertido" value={`€${data.invertido}`} />
                      <Row label="Recuperado" value={`€${data.recuperado}`} />
                      <Row label="Beneficio" value={`€${data.beneficio}`} color={data.beneficio >= 0 ? 'text-green-400' : 'text-red-400'} />
                      <Row label="ROI" value={`${data['roi_%']}%`} color={data['roi_%'] >= 0 ? 'text-green-400' : 'text-red-400'} />
                      <Row label="Aciertos Medios" value={`${data.aciertos_medios}/14`} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

function NavItem({ icon, label, active, onClick }: { icon: React.ReactNode, label: string, active?: boolean, onClick: () => void }) {
  return (
    <button onClick={onClick} className={`flex items-center gap-2.5 px-3 py-2.5 rounded-xl text-sm font-medium transition-all cursor-pointer text-left w-full ${active ? 'bg-indigo-600/15 text-indigo-300 border border-indigo-500/20' : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'}`}>
      {icon}<span>{label}</span>
      {active && <div className="ml-auto w-1.5 h-1.5 bg-indigo-400 rounded-full" />}
    </button>
  )
}

function StatCard({ title, value, sub, color }: { title: string, value: string, sub: string, color: string }) {
  return (
    <div className="bg-[#1e293b]/60 border border-slate-800 p-4 rounded-2xl hover:border-slate-700 transition-all">
      <p className="text-[11px] font-medium text-slate-500 mb-1 uppercase tracking-wider">{title}</p>
      <p className={`text-xl font-bold text-white`}>{value}</p>
      <p className={`text-[11px] mt-0.5 ${color}`}>{sub}</p>
    </div>
  )
}

function Row({ label, value, color = 'text-white' }: { label: string, value: string, color?: string }) {
  return (
    <div className="flex justify-between items-center">
      <span className="text-slate-400">{label}</span>
      <span className={`font-semibold ${color}`}>{value}</span>
    </div>
  )
}

export default App
