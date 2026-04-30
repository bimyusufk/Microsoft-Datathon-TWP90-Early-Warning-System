import React from 'react';

export default function ScenarioChart({ data, dTWP }) {
  const top10 = data.slice(0, 10);
  const W = 900, H = 280, padL = 140, padR = 20, padT = 20, padB = 60;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;
  const n = top10.length;
  const groupW = chartW / n;
  const barW = groupW * 0.25;
  const maxVal = 0.055;

  const dStress = (-0.207 * 1.0/100) + (-0.201 * 0.5/100) + (0.013 * -2.0/100);
  const dOpt    = (-0.207 * -0.5/100) + (-0.201 * -0.5/100) + (0.013 * 1.0/100);

  return (
    <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`}>
      {[0,1,2,3,4,5].map(i => {
        const y = padT + chartH - (i / 5) * chartH;
        const val = (i / 5 * maxVal * 100).toFixed(1);
        return (
          <g key={i}>
            <line x1={padL} y1={y} x2={W-padR} y2={y} stroke="#1f2937" strokeWidth="1"/>
            <text x={padL-6} y={y+4} fill="#475569" fontSize="9" textAnchor="end" fontFamily="IBM Plex Mono">{val}%</text>
          </g>
        );
      })}
      
      {top10.map((d, i) => {
        const cx = padL + i * groupW + groupW / 2;
        const stress2026 = Math.max(0, d.actual + dStress);
        const opt2026    = Math.max(0, d.actual + dOpt);
        
        const barData = [
          { v: d.actual,  color: '#3b82f6', label:'2025' },
          { v: Math.max(0, d.actual + dTWP), color: '#10b981', label:'Baseline/Custom' },
          { v: stress2026,color: '#ef4444', label:'Stress' },
          { v: opt2026,   color: '#f59e0b', label:'Optimis' },
        ];
        
        const shortName = d.prov.replace('Nusa Tenggara Barat', 'NTB').replace('Nusa Tenggara Timur', 'NTT').replace('Kepulauan ', 'Kep. ').replace('Sumatera ', 'Sum. ').replace('Kalimantan ', 'Kal. ').replace('Sulawesi ', 'Sul. ');
        
        return (
          <g key={d.id}>
            {barData.map((b, j) => {
              const bx = cx - (barW * 1.5) + j * (barW + 2);
              const bh = (b.v / maxVal) * chartH;
              const by = padT + chartH - bh;
              return <rect key={j} x={bx} y={by} width={barW} height={bh} fill={b.color} opacity="0.8" rx="1"/>;
            })}
            <text x={cx} y={H-10} fill="#64748b" fontSize="8" textAnchor="middle" fontFamily="IBM Plex Mono">{shortName}</text>
          </g>
        );
      })}

      {[
        { color:'#3b82f6', label:'Aktual 2025', desc:'Data historis' },
        { color:'#10b981', label:'Proyeksi (Custom)', desc:'Hasil simulasi' },
        { color:'#ef4444', label:'Stress 2026', desc:'Kondisi memburuk' },
        { color:'#f59e0b', label:'Optimistik 2026', desc:'Kondisi membaik' },
      ].map((item, i) => (
        <g key={i}>
          <rect x={padL + i * 180} y={padT} width="10" height="10" fill={item.color} rx="1" opacity="0.8"/>
          <text x={padL + i * 180 + 14} y={padT+4} fill="#e2e8f0" fontSize="9" fontFamily="IBM Plex Mono" fontWeight="bold">{item.label}</text>
          <text x={padL + i * 180 + 14} y={padT+14} fill="#94a3b8" fontSize="8" fontFamily="IBM Plex Mono">{item.desc}</text>
        </g>
      ))}
    </svg>
  );
}
