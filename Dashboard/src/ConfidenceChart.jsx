import React from 'react';

export default function ConfidenceChart({ data, pipelineCData }) {
  const top10 = data.slice(0, 10);
  const W = 900, H = 320, padL = 140, padR = 30, padT = 40, padB = 70;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;
  const n = top10.length;
  const groupW = chartW / n;
  const maxVal = 0.06;
  const RMSE_A = 0.00554;
  const RMSE_C = 0.00544;
  const Z90 = 1.645, Z95 = 1.960;

  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
      {/* Grid lines */}
      {[0,1,2,3,4,5,6].map(i => {
        const y = padT + chartH - (i / 6) * chartH;
        const val = (i / 6 * maxVal * 100).toFixed(1);
        return (
          <g key={i}>
            <line x1={padL} y1={y} x2={W-padR} y2={y} stroke="#1f2937" strokeWidth="1"/>
            <text x={padL-8} y={y+4} fill="#475569" fontSize="9" textAnchor="end" fontFamily="IBM Plex Mono">{val}%</text>
          </g>
        );
      })}
      {/* Warning threshold line at 3% */}
      <line x1={padL} y1={padT + chartH - (0.03/maxVal)*chartH} x2={W-padR} y2={padT + chartH - (0.03/maxVal)*chartH} stroke="#ef4444" strokeWidth="1" strokeDasharray="6,4" opacity="0.5"/>
      <text x={W-padR+4} y={padT + chartH - (0.03/maxVal)*chartH + 3} fill="#ef4444" fontSize="8" fontFamily="IBM Plex Mono" opacity="0.7">3%</text>

      {top10.map((d, i) => {
        const cx = padL + i * groupW + groupW / 2;
        const cMatch = pipelineCData.find(c => c.id === d.id);
        const predC = cMatch ? cMatch.pred : d.pred;
        const actY = padT + chartH - (d.actual / maxVal) * chartH;
        const predAY = padT + chartH - (d.pred / maxVal) * chartH;
        const predCY = padT + chartH - (predC / maxVal) * chartH;
        // CI bands for Pipeline C
        const ci95U = padT + chartH - (Math.min(predC + Z95 * RMSE_C, maxVal) / maxVal) * chartH;
        const ci95L = padT + chartH - (Math.max(predC - Z95 * RMSE_C, 0) / maxVal) * chartH;
        const ci90U = padT + chartH - (Math.min(predC + Z90 * RMSE_C, maxVal) / maxVal) * chartH;
        const ci90L = padT + chartH - (Math.max(predC - Z90 * RMSE_C, 0) / maxVal) * chartH;
        const shortName = d.prov.replace('Nusa Tenggara Barat','NTB').replace('Nusa Tenggara Timur','NTT').replace('Kepulauan ','Kep. ').replace('Sumatera ','Sum. ').replace('Kalimantan ','Kal. ').replace('Sulawesi ','Sul. ').replace('Daerah Istimewa ','DI ');
        const bw = 6;
        return (
          <g key={d.id}>
            {/* 95% CI band */}
            <rect x={cx-14} y={ci95U} width={28} height={ci95L-ci95U} fill="#3b82f6" opacity="0.06" rx="2"/>
            {/* 90% CI band */}
            <rect x={cx-10} y={ci90U} width={20} height={ci90L-ci90U} fill="#3b82f6" opacity="0.12" rx="2"/>
            {/* Actual */}
            <circle cx={cx} cy={actY} r="4" fill="#10b981" stroke="#10b981" strokeWidth="1"/>
            {/* Pipeline A prediction */}
            <rect x={cx-bw-2} y={predAY-2} width={bw} height={4} fill="#3b82f6" rx="1"/>
            {/* Pipeline C prediction */}
            <rect x={cx+2} y={predCY-2} width={bw} height={4} fill="#a78bfa" rx="1"/>
            {/* Province label */}
            <text x={cx} y={H-14} fill="#64748b" fontSize="8" textAnchor="middle" fontFamily="IBM Plex Mono" transform={`rotate(-25,${cx},${H-14})`}>{shortName}</text>
          </g>
        );
      })}
      {/* Legend */}
      {[
        { color:'#10b981', label:'Aktual 2025', shape:'circle' },
        { color:'#3b82f6', label:'Prediksi Pipeline A', shape:'rect' },
        { color:'#a78bfa', label:'Prediksi Pipeline C', shape:'rect' },
        { color:'rgba(59,130,246,.15)', label:'CI 90%', shape:'band' },
        { color:'rgba(59,130,246,.08)', label:'CI 95%', shape:'band' },
      ].map((item, i) => (
        <g key={i}>
          {item.shape==='circle' ? <circle cx={padL + i*150 + 5} cy={padT-18} r="4" fill={item.color}/> :
           item.shape==='rect' ? <rect x={padL + i*150} y={padT-22} width="10" height="8" fill={item.color} rx="1"/> :
           <rect x={padL + i*150} y={padT-24} width="10" height="12" fill={item.color} rx="1" stroke="#3b82f6" strokeWidth="0.5" opacity="0.6"/>}
          <text x={padL + i*150 + 14} y={padT-15} fill="#94a3b8" fontSize="8" fontFamily="IBM Plex Mono">{item.label}</text>
        </g>
      ))}
    </svg>
  );
}
