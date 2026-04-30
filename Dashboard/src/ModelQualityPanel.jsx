import React from 'react';

// Drift assessment logic
function assessDrift(r2Train, r2Test) {
  const gap = Math.abs(r2Train - r2Test);
  const pct = (gap / r2Train * 100);
  if (pct < 10) return { status: 'STABIL', color: 'var(--green)', dot: 'ok', desc: 'Tidak terdeteksi overfitting' };
  if (pct < 30) return { status: 'MONITOR', color: 'var(--orange)', dot: 'warn', desc: 'Gap moderat — perlu pengawasan' };
  return { status: 'OVERFITTING', color: 'var(--red)', dot: 'danger', desc: 'Gap besar antara train & test' };
}

export default function ModelQualityPanel({ metricsC, comparisonData }) {
  // Pipeline A metrics from comparison CSV
  const pA = comparisonData.find(d => d.pipeline && d.pipeline.includes('Huber'));
  const pC = comparisonData.find(d => d.pipeline && d.pipeline.includes('XGBoost'));
  // Pipeline C detailed metrics
  const cTrain = metricsC.find(d => d.label && d.label.includes('Train'));
  const cTest = metricsC.find(d => d.label && d.label.includes('Test') && !d.label.includes('Naive'));
  const naive = metricsC.find(d => d.label && d.label.includes('Naive'));

  const driftC = cTrain && cTest ? assessDrift(cTrain.r2, cTest.r2) : null;
  const driftA = pA ? assessDrift(0.641, 0.5999) : null; // from hardcoded A2 metrics

  // Beat naive?
  const cBeatsNaive = cTest && naive && cTest.rmse < naive.rmse;

  return (
    <div>
      {/* Pipeline Comparison Cards */}
      <div className="model-metrics">
        <div className="mm-card pipeline-a">
          <div className="mm-label">Pipeline A — R²</div>
          <div className="mm-val">{pA ? (pA.r2 * 100).toFixed(1) : '60.0'}%</div>
          <div className="mm-sub">Huber FD Regression</div>
        </div>
        <div className="mm-card pipeline-a">
          <div className="mm-label">Pipeline A — RMSE</div>
          <div className="mm-val" style={{color:'var(--green)', fontSize: 18}}>{pA ? pA.rmse.toFixed(5) : '0.00554'}</div>
          <div className="mm-sub">Annual Level</div>
        </div>
        <div className="mm-card pipeline-c">
          <div className="mm-label">Pipeline C — R² Test</div>
          <div className="mm-val">{cTest ? (cTest.r2 * 100).toFixed(1) : '74.7'}%</div>
          <div className="mm-sub">XGBoost Pseudo-MIDAS</div>
        </div>
        <div className="mm-card pipeline-c">
          <div className="mm-label">Pipeline C — RMSE Test</div>
          <div className="mm-val" style={{color:'var(--green)', fontSize: 18}}>{cTest ? cTest.rmse.toFixed(5) : '0.00544'}</div>
          <div className="mm-sub">Monthly Level</div>
        </div>
        <div className="mm-card pipeline-c">
          <div className="mm-label">Pipeline C — R² Train</div>
          <div className="mm-val" style={{color:'var(--purple)'}}>{cTrain ? (cTrain.r2 * 100).toFixed(1) : '96.8'}%</div>
          <div className="mm-sub">n={cTrain ? cTrain.n : 744}</div>
        </div>
        <div className="mm-card pipeline-c">
          <div className="mm-label">Pipeline C — MAE Test</div>
          <div className="mm-val" style={{color:'var(--cyan)', fontSize: 18}}>{cTest ? cTest.mae.toFixed(5) : '0.00162'}</div>
          <div className="mm-sub">Mean Absolute Error</div>
        </div>
        <div className="mm-card naive">
          <div className="mm-label">Naive Benchmark — R²</div>
          <div className="mm-val" style={{color:'var(--muted)'}}>{naive ? (naive.r2 * 100).toFixed(1) : '79.2'}%</div>
          <div className="mm-sub">y = y<sub>t-1</sub></div>
        </div>
        <div className="mm-card" style={{borderLeft: cBeatsNaive ? '3px solid var(--green)' : '3px solid var(--red)'}}>
          <div className="mm-label">XGBoost vs Naive</div>
          <div className="mm-val" style={{color: cBeatsNaive ? 'var(--green)' : 'var(--red)', fontSize: 16}}>
            {cBeatsNaive ? '✓ BEATS NAIVE' : '✗ BELOW NAIVE'}
          </div>
          <div className="mm-sub">RMSE comparison</div>
        </div>
      </div>

      {/* Drift Monitoring */}
      <div className="drift-panel">
        <div style={{fontFamily:'var(--mono)', fontSize:10, fontWeight:700, letterSpacing:'.08em', textTransform:'uppercase', color:'var(--muted)', marginBottom: 12}}>
          ⚡ Model Drift Monitoring
        </div>
        {driftA && (
          <div className="drift-row">
            <div className={`drift-dot ${driftA.dot}`}></div>
            <div className="drift-label">Pipeline A (Huber FD) — Train/Test Gap</div>
            <div className="drift-value" style={{color: driftA.color}}>
              {((0.641 - 0.5999) / 0.641 * 100).toFixed(1)}%
            </div>
            <div className="drift-status" style={{background: `${driftA.color}15`, color: driftA.color}}>
              {driftA.status}
            </div>
          </div>
        )}
        {driftC && (
          <div className="drift-row">
            <div className={`drift-dot ${driftC.dot}`}></div>
            <div className="drift-label">Pipeline C (XGBoost) — Train/Test Gap</div>
            <div className="drift-value" style={{color: driftC.color}}>
              {((cTrain.r2 - cTest.r2) / cTrain.r2 * 100).toFixed(1)}%
            </div>
            <div className="drift-status" style={{background: `${driftC.color}15`, color: driftC.color}}>
              {driftC.status}
            </div>
          </div>
        )}
        <div className="drift-row">
          <div className={`drift-dot ${cBeatsNaive ? 'ok' : 'danger'}`}></div>
          <div className="drift-label">Pipeline C vs Naive Forecast — Sanity Check</div>
          <div className="drift-value" style={{color: cBeatsNaive ? 'var(--green)' : 'var(--red)'}}>
            {cTest && naive ? ((naive.rmse - cTest.rmse) / naive.rmse * 100).toFixed(1) : '—'}%
          </div>
          <div className="drift-status" style={{
            background: cBeatsNaive ? 'rgba(16,185,129,.1)' : 'rgba(239,68,68,.1)',
            color: cBeatsNaive ? 'var(--green)' : 'var(--red)'
          }}>
            {cBeatsNaive ? 'PASSED' : 'FAILED'}
          </div>
        </div>
      </div>
    </div>
  );
}
