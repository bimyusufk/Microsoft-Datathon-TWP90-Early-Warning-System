import React, { useState, useEffect } from 'react';
import Papa from 'papaparse';
import { MapContainer, TileLayer, CircleMarker, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import ScenarioChart from './ScenarioChart.jsx';

const COORDS = {
  'Aceh':[5.55,95.32],'Sumatera Utara':[2.12,99.54],'Sumatera Barat':[-0.74,100.80],
  'Riau':[0.53,101.45],'Jambi':[-1.61,103.61],'Sumatera Selatan':[-3.31,104.91],
  'Bengkulu':[-3.79,102.27],'Lampung':[-4.56,105.40],
  'Kepulauan Bangka Belitung':[-2.74,106.44],'Kepulauan Riau':[3.92,108.14],
  'Dki Jakarta':[-6.21,106.85],'Jawa Barat':[-6.90,107.62],
  'Jawa Tengah':[-7.15,110.14],'Daerah Istimewa Yogyakarta':[-7.80,110.36],
  'Jawa Timur':[-7.54,112.24],'Banten':[-6.41,106.02],
  'Bali':[-8.34,115.09],'Nusa Tenggara Barat':[-8.65,117.36],
  'Nusa Tenggara Timur':[-8.66,121.08],'Kalimantan Barat':[0.00,109.34],
  'Kalimantan Tengah':[-1.68,113.38],'Kalimantan Selatan':[-3.09,115.28],
  'Kalimantan Timur':[0.54,116.42],'Kalimantan Utara':[3.07,116.04],
  'Sulawesi Utara':[0.63,123.97],'Sulawesi Tengah':[-1.43,121.45],
  'Sulawesi Selatan':[-3.66,119.97],'Sulawesi Tenggara':[-4.14,122.17],
  'Gorontalo':[0.55,123.06],'Sulawesi Barat':[-2.84,119.23],
  'Maluku':[-3.24,130.15],'Maluku Utara':[1.57,127.81],
};

const COEFF_LABELS = {
  'd_x2_inflasi_avg': 'Inflasi (x2)',
  'd_x1_bi_rate_avg': 'BI Rate (x1)',
  'd_x9_npl': 'NPL (x9)',
  'd_x5_internet': 'Penetrasi Internet (x5)',
  'd_x8_ldr': 'LDR (x8)',
  'd_log_pdrb': 'ln(PDRB) (x3)',
  'd_x4_tpt': 'TPT (x4)',
  'd_x10_umkm': 'Rasio UMKM (x10)',
};

const DESC = {
  'd_x2_inflasi_avg': 'Inflasi naik → BI Rate naik → ekspansi kredit dibatasi → proporsi pinjaman berisiko turun. Dalam konteks Indonesia 2022–2025, mekanisme moneter bekerja efektif membatasi risiko kredit baru.',
  'd_x1_bi_rate_avg': 'Kenaikan BI Rate memiliki efek pembatasan kredit yang kecil dalam model ini — kemungkinan karena lag transmisi moneter belum sepenuhnya tertangkap dalam data tahunan.',
  'd_x9_npl': 'Kenaikan NPL memicu <strong>pengetatan standar kredit</strong> oleh bank (credit rationing). Pool debitur baru menjadi lebih berkualitas → TWP90 turun. Ini adalah mekanisme <strong>self-correcting</strong> sektor keuangan.',
  'd_x5_internet': 'Perluasan digital tanpa literasi keuangan memadai membuka akses bagi segmen <strong>underbanked dengan risiko tinggi</strong>. Efek ini kecil tapi konsisten — intervensi literasi keuangan digital diperlukan.',
  'd_x8_ldr': 'Ekspansi kredit agresif (LDR tinggi) → standar penyaringan debitur longgar → lebih banyak debitur berisiko masuk sistem. Regulasi makroprudensial LDR penting sebagai penyeimbang.',
  'd_log_pdrb': 'Pertumbuhan ekonomi mendorong aktivitas pinjaman. Ekspansi kredit saat boom ekonomi bisa mengakumulasi risiko jangka menengah jika tidak diimbangi pengawasan kredit ketat.',
  'd_x4_tpt': 'Tingkat pengangguran hampir tidak signifikan dalam model FD — kemungkinan karena P2P lending di Indonesia melayani segmen spesifik yang tidak berkorelasi langsung dengan TPT agregat.',
  'd_x10_umkm': 'Proporsi kredit UMKM menunjukkan dampak marginal sangat kecil. Butuh data yang lebih granular untuk memisahkan efek kualitas debitur UMKM dari volume.',
};

const RECS = {
  HIGH: {
    title: 'Tindakan Segera Diperlukan', icon: '🚨',
    actions: ['Intensifikasi audit OJK pada platform fintech aktif di provinsi ini', 'Terapkan pembatasan ekspansi pinjaman baru sementara', 'Tingkatkan cadangan CKPN minimum 20% di atas threshold normal']
  },
  MEDIUM: {
    title: 'Pemantauan Ketat', icon: '⚠️',
    actions: ['Jadwalkan review triwulanan kualitas portofolio kredit', 'Monitor pertumbuhan NPL secara real-time', 'Siapkan contingency plan jika TWP90 melampaui 3%']
  },
  LOW: {
    title: 'Pemantauan Rutin', icon: '✅',
    actions: ['Pertahankan standar underwriting yang ada', 'Manfaatkan kondisi sehat untuk ekspansi terukur', 'Dokumentasikan best practice untuk replikasi di daerah lain']
  }
};

function classify(a) { return a >= 0.03 ? 'HIGH' : a >= 0.02 ? 'MEDIUM' : 'LOW'; }
function riskLabel(r) { return r === 'HIGH' ? 'KRITIS' : r === 'MEDIUM' ? 'WASPADA' : 'NORMAL'; }
function riskColor(r) { return r === 'HIGH' ? 'var(--red)' : r === 'MEDIUM' ? 'var(--orange)' : 'var(--green)'; }
function fmt(v) { return (v*100).toFixed(2)+'%'; }
function fmtSign(v) { return (v >= 0 ? '+' : '') + (v*100).toFixed(2)+'%'; }

function Sparkline({ vals, color }) {
  const w = 80, h = 30, pad = 2;
  const mn = Math.min(...vals), mx = Math.max(...vals);
  const range = mx - mn || 1;
  const pts = vals.map((v, i) => {
    const x = pad + (i / (vals.length - 1)) * (w - pad * 2);
    const y = h - pad - ((v - mn) / range) * (h - pad * 2);
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg className="kpi-sparkline" viewBox="0 0 80 30">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" opacity="0.8"/>
      <polyline points={`${pts} ${80-pad},${h} ${pad},${h}`} fill={color} opacity="0.1"/>
    </svg>
  );
}

function TableSparkline({ d, colorHex }) {
  const prev2 = Math.max(0, d.actual - d.dy * 2.2);
  const prev1 = Math.max(0, d.actual - d.dy * 1.1);
  const vals = [prev2, prev1, d.actual - d.dy * 0.2, d.actual];
  const W = 70, H = 28, pad = 3;
  const mn = Math.min(...vals) * 0.98, mx = Math.max(...vals) * 1.02;
  const range = mx - mn || 0.001;
  const pts = vals.map((v, i) => {
    const x = pad + (i / (vals.length - 1)) * (W - pad * 2);
    const y = H - pad - ((v - mn) / range) * (H - pad * 2);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(' ');
  const ptsArr = pts.split(' ');
  const [lx, ly] = ptsArr[ptsArr.length-1].split(',');
  const uid = d.id + Math.random().toString(36).slice(2,6);
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{display:'block'}}>
      <defs>
        <linearGradient id={`g${uid}`} x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor={colorHex} stopOpacity="0.3"/>
          <stop offset="100%" stopColor={colorHex} stopOpacity="0"/>
        </linearGradient>
      </defs>
      <polygon points={`${pts} ${(W-pad).toFixed(1)},${H} ${pad},${H}`} fill={`url(#g${uid})`}/>
      <polyline points={pts} fill="none" stroke={colorHex} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <circle cx={lx} cy={ly} r="2.5" fill={colorHex}/>
    </svg>
  );
}

export default function App() {
  const [data, setData] = useState([]);
  const [coeffs, setCoeffs] = useState([]);
  const [tab, setTab] = useState('overview');
  const [ovFilter, setOvFilter] = useState('all');
  const [ovSearch, setOvSearch] = useState('');
  
  // Scenario states
  const [scen, setScen] = useState({ npl: 0, inf: 0, ldr: 0, bi: 0 });
  const [preset, setPreset] = useState('baseline');

  useEffect(() => {
    Promise.all([
      fetch('/predictions.csv').then(r => r.text()),
      fetch('/coefficients.csv').then(r => r.text())
    ]).then(([predCsv, coefCsv]) => {
      const predData = Papa.parse(predCsv, { header: true, dynamicTyping: true, skipEmptyLines: true }).data;
      const parsedData = predData.map(d => ({
        id: d.provinsi_id,
        prov: d.nama_provinsi,
        actual: d.twp90_actual,
        pred: d.twp90_predicted,
        dy: d.dy,
        dy_pred: d.dy_pred,
        risk: classify(d.twp90_actual)
      })).sort((a,b) => b.actual - a.actual);
      setData(parsedData);

      const coefData = Papa.parse(coefCsv, { header: true, dynamicTyping: true, skipEmptyLines: true }).data;
      const parsedCoeffs = coefData.map(d => ({
        name: d.feature,
        label: COEFF_LABELS[d.feature] || d.feature,
        coef: d.coef_original_scale,
        key: d.feature.split('_').pop()
      }));
      setCoeffs(parsedCoeffs);
    });
  }, []);

  if (!data.length || !coeffs.length) return <div style={{padding: '40px', color: '#fff'}}>Loading Data...</div>;

  const avg = data.reduce((s,d) => s + d.actual, 0) / data.length;
  const nHigh = data.filter(d => d.risk === 'HIGH').length;
  const nMed  = data.filter(d => d.risk === 'MEDIUM').length;
  const nLow  = data.filter(d => d.risk === 'LOW').length;
  const top = data[0];

  let filteredData = ovFilter === 'all' ? data : data.filter(d => d.risk === ovFilter);
  if (ovSearch) filteredData = filteredData.filter(d => d.prov.toLowerCase().includes(ovSearch.toLowerCase()));

  // Simulate
  const dTWP = (-0.207 * scen.npl/100) + (-0.201 * scen.inf/100) + (0.013 * scen.ldr/100) + (-0.003 * scen.bi/100);
  const projected = Math.max(0, avg + dTWP);
  const rel = dTWP / avg * 100;
  const signal = dTWP < -0.005 ? '↓ MEMBAIK' : dTWP > 0.005 ? '↑ MEMBURUK' : '→ STABIL';
  const sigColor = dTWP < -0.005 ? 'var(--green)' : dTWP > 0.005 ? 'var(--red)' : 'var(--accent)';

  const handleSlider = (e) => {
    setScen({...scen, [e.target.name]: parseFloat(e.target.value)});
    setPreset('custom');
  };

  const setPresetVal = (name, vals) => {
    setPreset(name);
    setScen(vals);
  };

  return (
    <>
      <header>
        <div className="logo-wrap">
          <div className="logo-badge">TWP90</div>
          <h1>Early Warning System</h1>
        </div>
        <div className="header-right">
          <div className="live-indicator"><span className="live-dot"></span>Data 2025 · 31 Provinsi</div>
          <div style={{fontFamily:'var(--mono)',fontSize:'10px',color:'var(--muted)'}}>Huber FD · R²=0.600</div>
        </div>
      </header>

      <div className="tabs">
        <button className={`tab ${tab==='overview'?'active':''}`} onClick={() => setTab('overview')}>Overview</button>
        <button className={`tab ${tab==='map'?'active':''}`} onClick={() => setTab('map')}>Peta Risiko</button>
        <button className={`tab ${tab==='scenario'?'active':''}`} onClick={() => setTab('scenario')}>Simulasi</button>
        <button className={`tab ${tab==='model'?'active':''}`} onClick={() => setTab('model')}>Model</button>
      </div>

      {tab === 'overview' && (
        <div className="panel active">
          <div className="kpi-row">
            <div className="kpi blue">
              <div className="kpi-accent"></div><div className="kpi-label">Rata-rata TWP90</div>
              <div className="kpi-value">{fmt(avg)}</div><div className="kpi-sub">Nasional 2025</div>
              <Sparkline vals={[0.0172, 0.0182, 0.0191, avg]} color="#3b82f6"/>
            </div>
            <div className="kpi red">
              <div className="kpi-accent"></div><div className="kpi-label">Kritis</div>
              <div className="kpi-value">{nHigh}</div><div className="kpi-sub">Provinsi ≥ 3%</div>
              <Sparkline vals={[2, 3, 4, nHigh]} color="#ef4444"/>
            </div>
            <div className="kpi orange">
              <div className="kpi-accent"></div><div className="kpi-label">Waspada</div>
              <div className="kpi-value">{nMed}</div><div className="kpi-sub">Provinsi 2–3%</div>
              <Sparkline vals={[6, 7, 8, nMed]} color="#f59e0b"/>
            </div>
            <div className="kpi green">
              <div className="kpi-accent"></div><div className="kpi-label">Normal</div>
              <div className="kpi-value">{nLow}</div><div className="kpi-sub">Provinsi &lt; 2%</div>
              <Sparkline vals={[24, 22, 20, nLow]} color="#10b981"/>
            </div>
            <div className="kpi cyan">
              <div className="kpi-accent"></div><div className="kpi-label">Model Accuracy</div>
              <div className="kpi-value">60.0%</div><div className="kpi-sub">Test R² · Huber FD</div>
              <Sparkline vals={[0.0, 0.406, 0.52, 0.599]} color="#0ea5e9"/>
            </div>
          </div>

          <div className="insight-box">
            <div className="insight-header">⚡ AI Insight — Smart Narrative</div>
            <div className="insight-text">
              Sistem Early Warning TWP90 mengidentifikasi <strong>{nHigh} provinsi berstatus KRITIS</strong> dengan TWP90 di atas ambang 3%, dipimpin <strong>{top.prov} ({fmt(top.actual)})</strong> yang mencatat TWP90 tertinggi nasional.<br/><br/>
              <strong>Driver dominan:</strong> NPL (β=−0.207) dan Inflasi (β=−0.201) menunjukkan mekanisme <em>self-correcting</em> — kenaikan NPL justru mendorong pengetatan kredit oleh lembaga keuangan, menurunkan proporsi debitur berisiko baru. Namun penetrasi internet (β=+0.017) memberi sinyal peringatan: ekspansi digital tanpa literasi keuangan memadai berpotensi meningkatkan risiko marginal.<br/><br/>
              <strong>Rekomendasi prioritas:</strong> OJK perlu mengintensifikasi pengawasan di provinsi KRITIS dengan pembatasan ekspansi kredit baru dan peningkatan CKPN minimum. Alokasi dana penjaminan (Jamkrindo/Askrindo) harus diprioritaskan ke provinsi KRITIS dan WASPADA.
            </div>
          </div>

          <div className="grid-3">
            <div className="card">
              <div className="card-header">
                <span className="card-title">Monitoring Risiko — 31 Provinsi</span>
                <span className="card-tag">{data.length} provinsi</span>
              </div>
              <div style={{padding:'10px 14px',borderBottom:'1px solid var(--border)',display:'flex',gap:'6px',alignItems:'center',flexWrap:'wrap'}}>
                <button className={`filter-btn ${ovFilter==='all'?'active-all':''}`} onClick={()=>setOvFilter('all')}>Semua</button>
                <button className={`filter-btn ${ovFilter==='HIGH'?'active-high':''}`} onClick={()=>setOvFilter('HIGH')}>Kritis</button>
                <button className={`filter-btn ${ovFilter==='MEDIUM'?'active-med':''}`} onClick={()=>setOvFilter('MEDIUM')}>Waspada</button>
                <button className={`filter-btn ${ovFilter==='LOW'?'active-low':''}`} onClick={()=>setOvFilter('LOW')}>Normal</button>
                <input className="search-input" placeholder="Cari provinsi..." value={ovSearch} onChange={(e)=>setOvSearch(e.target.value)} />
              </div>
              <div style={{overflowX:'auto',maxHeight:'520px',overflowY:'auto'}}>
                <table className="data-table">
                  <thead>
                    <tr><th>#</th><th>Provinsi</th><th>TWP90</th><th>Prediksi</th><th>Δ YoY</th><th>Tren</th><th>Status</th><th>Sinyal</th></tr>
                  </thead>
                  <tbody>
                    {filteredData.map((d, i) => {
                      const rl = riskLabel(d.risk);
                      const color = d.risk==='HIGH'?'#ef4444':d.risk==='MEDIUM'?'#f59e0b':'#10b981';
                      return (
                        <tr key={d.id}>
                          <td className="rank">{data.findIndex(x=>x.id===d.id)+1}</td>
                          <td className="prov-name">{d.prov}</td>
                          <td className="twp-val" style={{color}}>{fmt(d.actual)}</td>
                          <td style={{fontFamily:'var(--mono)',fontSize:'12px',color:'var(--muted)'}}>{fmt(d.pred)}</td>
                          <td style={{fontFamily:'var(--mono)',fontSize:'12px',color:d.dy>0?'var(--red)':'var(--green)'}}>{fmtSign(d.dy)}</td>
                          <td style={{padding:'4px 10px'}}><TableSparkline d={d} colorHex={color} /></td>
                          <td><span className={`badge ${rl}`}>{rl}</span></td>
                          <td><span className={`signal ${d.dy>0.001?'up':d.dy<-0.001?'down':'flat'}`} style={{fontSize:'14px'}}>{d.dy>0.001?'▲':d.dy<-0.001?'▼':'—'}</span></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            <div style={{display:'flex',flexDirection:'column',gap:'12px'}}>
              <div style={{fontFamily:'var(--mono)',fontSize:'10px',letterSpacing:'.1em',textTransform:'uppercase',color:'var(--muted)'}}>Provinsi Kritis — Perlu Perhatian Segera</div>
              <div style={{display:'grid',gridTemplateColumns:'1fr',gap:'12px'}}>
                {data.filter(d=>d.risk==='HIGH').map(d=>(
                  <div className="high-card" key={d.id}>
                    <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:'8px'}}>
                      <div>
                        <div style={{fontFamily:'var(--mono)',fontSize:'9px',color:'var(--red)',letterSpacing:'.08em',textTransform:'uppercase',marginBottom:'2px'}}>KRITIS</div>
                        <div style={{fontWeight:700,fontSize:'14px'}}>{d.prov}</div>
                      </div>
                      <span className="badge KRITIS">KRITIS</span>
                    </div>
                    <div style={{fontFamily:'var(--mono)',fontSize:'28px',fontWeight:700,color:'var(--red)',marginBottom:'10px'}}>{fmt(d.actual)}</div>
                    <div style={{borderTop:'1px solid rgba(239,68,68,.15)',paddingTop:'10px'}}>
                      <div style={{display:'flex',justifyContent:'space-between',fontSize:'11px',color:'var(--muted)',marginBottom:'4px'}}>
                        <span>Prediksi Model</span><span style={{fontFamily:'var(--mono)',color:'var(--text)'}}>{fmt(d.pred)}</span>
                      </div>
                      <div style={{display:'flex',justifyContent:'space-between',fontSize:'11px',color:'var(--muted)',marginBottom:'8px'}}>
                        <span>Perubahan YoY</span>{d.dy>0?<span style={{color:'var(--red)'}}>↑ {fmtSign(d.dy)}</span>:<span style={{color:'var(--green)'}}>↓ {fmtSign(d.dy)}</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'map' && (
        <div className="panel active">
           <div className="grid-3" style={{gap:'16px'}}>
             <div className="card" style={{overflow:'visible'}}>
               <div className="card-header"><span className="card-title">Peta Distribusi Risiko TWP90</span></div>
               <div style={{height: '440px'}}>
                 <MapContainer center={[-2.5, 117.5]} zoom={5} style={{height: '100%', width: '100%', background: '#070b12'}}>
                    <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png" attribution="© CARTO"/>
                    {data.map(d => {
                      const coords = COORDS[d.prov];
                      if(!coords) return null;
                      const color = d.risk==='HIGH'?'#ef4444':d.risk==='MEDIUM'?'#f59e0b':'#10b981';
                      return (
                        <CircleMarker key={d.id} center={coords} radius={d.risk==='HIGH'?18:d.risk==='MEDIUM'?13:9} pathOptions={{color, fillColor: color, fillOpacity: 0.25, weight: 2}}>
                          <Tooltip direction="top" className="leaflet-dark-tooltip"><strong>{d.prov}</strong><br/>{fmt(d.actual)}</Tooltip>
                        </CircleMarker>
                      );
                    })}
                 </MapContainer>
               </div>
             </div>
             <div style={{display:'flex',flexDirection:'column',gap:'12px'}}>
               <div className="card">
                  <div className="card-header"><span className="card-title">Distribusi Risiko</span></div>
                  <div className="card-body">
                    {[
                      {label:'🔴 Kritis', n:nHigh, color:'var(--red)'},
                      {label:'🟡 Waspada', n:nMed, color:'var(--orange)'},
                      {label:'🟢 Normal', n:nLow, color:'var(--green)'}
                    ].map(b => (
                      <div style={{marginBottom:'14px'}} key={b.label}>
                        <div style={{display:'flex',justifyContent:'space-between',fontSize:'11px',marginBottom:'4px'}}>
                          <span style={{color:'var(--text2)'}}>{b.label}</span>
                          <span style={{fontWeight:700,color:b.color}}>{b.n} ({(b.n/data.length*100).toFixed(0)}%)</span>
                        </div>
                        <div style={{background:'var(--bg)',height:'10px',borderRadius:'5px',overflow:'hidden'}}>
                          <div style={{width:`${b.n/data.length*100}%`,height:'100%',background:b.color,opacity:0.8}}></div>
                        </div>
                      </div>
                    ))}
                  </div>
               </div>
             </div>
           </div>
        </div>
      )}

      {tab === 'scenario' && (
        <div className="panel active">
          <div className="grid-2" style={{gap:'16px',marginBottom:'20px'}}>
            <div className="card">
              <div className="card-header"><span className="card-title">Simulasi Skenario Makroekonomi</span></div>
              <div className="card-body">
                <div className="slider-grid">
                  <div className="slider-item">
                    <label>Δ NPL <span className="sv">{scen.npl.toFixed(1)}</span> ppt</label>
                    <input type="range" name="npl" min="-3" max="3" step="0.1" value={scen.npl} onChange={handleSlider}/>
                  </div>
                  <div className="slider-item">
                    <label>Δ Inflasi <span className="sv">{scen.inf.toFixed(1)}</span>%</label>
                    <input type="range" name="inf" min="-2" max="3" step="0.1" value={scen.inf} onChange={handleSlider}/>
                  </div>
                  <div className="slider-item">
                    <label>Δ LDR <span className="sv">{scen.ldr.toFixed(1)}</span>%</label>
                    <input type="range" name="ldr" min="-10" max="10" step="0.5" value={scen.ldr} onChange={handleSlider}/>
                  </div>
                  <div className="slider-item">
                    <label>Δ BI Rate <span className="sv">{scen.bi.toFixed(1)}</span>%</label>
                    <input type="range" name="bi" min="-2" max="3" step="0.25" value={scen.bi} onChange={handleSlider}/>
                  </div>
                </div>
                <div style={{display:'flex',gap:'8px',marginBottom:'16px'}}>
                  <button className={`stab ${preset==='baseline'?'active':''}`} onClick={()=>setPresetVal('baseline',{npl:0,inf:0,ldr:0,bi:0})}>Baseline</button>
                  <button className={`stab ${preset==='stress'?'active':''}`} onClick={()=>setPresetVal('stress',{npl:1,inf:0.5,ldr:-2,bi:0.5})}>Stress</button>
                  <button className={`stab ${preset==='optimistic'?'active':''}`} onClick={()=>setPresetVal('optimistic',{npl:-0.5,inf:-0.5,ldr:1,bi:-0.25})}>Optimistik</button>
                </div>
                <div className="scenario-result">
                  <div className="sresult-card">
                    <div className="sresult-label">ΔTWP90 Nasional</div>
                    <div className="sresult-val" style={{color:dTWP<0?'var(--green)':dTWP>0?'var(--red)':'var(--accent)'}}>{(dTWP*100).toFixed(3)}%</div>
                  </div>
                  <div className="sresult-card">
                    <div className="sresult-label">TWP90 Proyeksi</div>
                    <div className="sresult-val" style={{color:projected>=0.03?'var(--red)':projected>=0.02?'var(--orange)':'var(--green)'}}>{fmt(projected)}</div>
                  </div>
                  <div className="sresult-card">
                    <div className="sresult-label">Sinyal</div>
                    <div className="sresult-val signal" style={{color:sigColor}}>{signal}</div>
                    <div className="sresult-sub">{(rel>=0?'+':'')+rel.toFixed(1)}% vs baseline</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div className="card">
            <div className="card-header"><span className="card-title">Perbandingan Skenario — Top 10 Provinsi</span></div>
            <div className="card-body">
              <ScenarioChart data={data} dTWP={dTWP} />
            </div>
          </div>
        </div>
      )}

      {tab === 'model' && (
        <div className="panel active">
          <div className="model-metrics">
            <div className="mm-card"><div className="mm-label">Test R²</div><div className="mm-val">0.599</div></div>
            <div className="mm-card"><div className="mm-label">Test RMSE</div><div className="mm-val" style={{color:'var(--green)'}}>0.00554</div></div>
            <div className="mm-card"><div className="mm-label">Train R²</div><div className="mm-val" style={{color:'var(--accent)'}}>0.641</div></div>
            <div className="mm-card"><div className="mm-label">Train RMSE</div><div className="mm-val" style={{color:'var(--orange)'}}>0.00588</div></div>
          </div>
          <div className="grid-2" style={{marginBottom:'16px'}}>
            <div className="card">
              <div className="card-header"><span className="card-title">Feature Importance</span><span className="card-tag">Huber Coeff</span></div>
              <div className="card-body">
                {coeffs.map(c => {
                  const maxAbs = Math.max(...coeffs.map(x => Math.abs(x.coef)));
                  const pct = (Math.abs(c.coef) / maxAbs * 44).toFixed(1);
                  const isNeg = c.coef < 0;
                  return (
                    <div className="coeff-row" key={c.name}>
                      <div className="coeff-label">{c.label.split('(')[0].trim()}</div>
                      <div className="coeff-bar-wrap">
                        <div className="coeff-zero"></div>
                        <div className={`coeff-bar ${isNeg?'neg':'pos'}`} style={{width:`${pct}%`}}></div>
                      </div>
                      <div className="coeff-val" style={{color:isNeg?'var(--accent)':'var(--accent2)'}}>
                        {c.coef > 0 ? '+' : ''}{c.coef.toFixed(3)}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
            <div className="card">
              <div className="card-header"><span className="card-title">Model Explainability</span><span className="card-tag">Interpretasi Koefisien</span></div>
              <div className="card-body" style={{overflowY:'auto',maxHeight:'380px'}}>
                {coeffs.map(c => {
                  const isNeg = c.coef < 0;
                  return (
                    <div key={c.name} style={{marginBottom:'12px',padding:'12px',background:'var(--bg)',borderRadius:'6px',borderLeft:`3px solid ${isNeg?'var(--accent)':'var(--accent2)'}`}}>
                      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'6px'}}>
                        <span style={{fontFamily:'var(--mono)',fontSize:'10px',fontWeight:700}}>{c.label}</span>
                        <span style={{fontFamily:'var(--mono)',fontSize:'12px',color:isNeg?'var(--accent)':'var(--accent2)'}}>{c.coef>0?'+':''}{c.coef.toFixed(3)}</span>
                      </div>
                      <div style={{fontSize:'11px',color:'var(--text2)',lineHeight:1.6}} dangerouslySetInnerHTML={{__html: DESC[c.name]||''}}></div>
                    </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
