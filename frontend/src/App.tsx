import { FormEvent, useEffect, useRef, useState } from 'react';
import { DEMO_FIXTURE_PROFILE, DEMO_SCENES, type DemoScene } from './demoFixtures';

type ApiInfo = {
  status: string;
  inspection_available: boolean;
  production_grading_available: boolean;
  capabilities: string[];
  model_assistance_configured: boolean;
};

type GeometryMeasurement = {
  quantity: string;
  value: number | null;
  unit: string | null;
  computable: boolean;
  not_computable_reason?: string | null;
};

type RegionVerdict = {
  verdict: 'ACCEPT' | 'REJECT' | 'PROCESS_INDICATOR' | 'UNDETERMINED';
  rule_id?: string;
  reason?: string;
  quantity?: string;
};

type Region = {
  region_id: string;
  bbox_px: { x: number; y: number; width: number; height: number };
  features: Record<string, number>;
  measurements?: GeometryMeasurement[];
  geometry_diagnostics?: Array<{
    name: string;
    curvature_px_inv: number | null;
    computable: boolean;
    not_computable_reason?: string | null;
  }>;
  rule_verdicts?: RegionVerdict[];
  interpretation: string;
};

type Inspection = {
  image: { sha256: string; width: number; height: number; calibrated: boolean };
  quality: {
    blur_laplacian_var: number;
    exposure_clipped_pct: number;
    prototype_quality_checks_passed: boolean;
    thresholds_validated: boolean;
  };
  candidate_regions: Region[];
  candidate_count: number;
  model_assistance: {
    status: string;
    observations: Array<{
      region_id: string;
      joint_type: string;
      condition_codes: string[];
      confidence: number;
      note: string;
      review_required: boolean;
    }>;
    message?: string;
  };
  grading: { verdict: string; reason_codes: string[]; actionable: boolean };
  disclaimer: string;
};

type Connection = 'checking' | 'online' | 'offline';
const MAX_FILE_BYTES = 10 * 1024 * 1024;

function verdictColor(verdict: string): string {
  if (verdict === 'ACCEPT') return 'var(--color-pass)';
  if (verdict === 'REJECT') return 'var(--color-defect)';
  return 'var(--color-text-muted)';
}

const IS_GITHUB_PAGES_DEMO = typeof window !== 'undefined' && window.location.pathname.startsWith('/jointcheck-solder-inspection/');

function DemoIllustration({ sceneId }: { sceneId: DemoScene['id'] }) {
  return (
    <svg className="demo-illustration" viewBox="0 0 280 180" role="img" aria-label={`Synthetic vector schematic for Joint ${sceneId}`}>
      <rect x="1" y="1" width="278" height="178" rx="9" fill="var(--color-bg-secondary)" stroke="var(--color-border)" />
      {sceneId === 'A' && (
        <g>
          <rect x="32" y="145" width="208" height="18" rx="3" fill="var(--color-warning)" opacity="0.45" />
          <path d="M58 145 Q82 134 98 115 L130 112 L130 145 Z" fill="var(--color-cyan)" opacity="0.35" stroke="var(--color-cyan)" strokeWidth="2" />
          <path d="M58 145 Q82 134 98 115 L130 112" fill="none" stroke="var(--color-cyan)" strokeWidth="3" />
          <line x1="58" y1="145" x2="128" y2="110" stroke="var(--color-text-primary)" strokeDasharray="5 4" />
          <path d="M84 145 A26 26 0 0 0 81 133" fill="none" stroke="var(--color-cyan)" strokeWidth="2" />
          <text x="86" y="128" fill="var(--color-cyan)" fontSize="12">angle arc</text>
        </g>
      )}
      {sceneId === 'B' && (
        <g>
          <rect x="20" y="145" width="104" height="18" rx="3" fill="var(--color-warning)" opacity="0.45" />
          <rect x="156" y="145" width="104" height="18" rx="3" fill="var(--color-warning)" opacity="0.45" />
          <path d="M74 145 Q91 112 115 128 C130 141 150 141 165 128 Q189 112 206 145 Z" fill="var(--color-cyan)" opacity="0.38" stroke="var(--color-cyan)" strokeWidth="2" />
          <line x1="124" y1="169" x2="156" y2="169" stroke="var(--color-text-primary)" strokeDasharray="4 3" />
          <text x="78" y="103" fill="var(--color-text-secondary)" fontSize="11">bridge outline · not scaled</text>
        </g>
      )}
      {sceneId === 'C' && (
        <g>
          <rect x="32" y="145" width="208" height="18" rx="3" fill="var(--color-warning)" opacity="0.45" />
          <path d="M70 145 C72 95 100 61 142 68 C178 74 198 111 207 145 Z" fill="var(--color-cyan)" opacity="0.2" stroke="var(--color-cyan)" strokeWidth="2" />
          <path d="M70 145 C72 95 100 61 142 68 C178 74 198 111 207 145" fill="none" stroke="var(--color-cyan)" strokeWidth="3" />
          <line x1="70" y1="145" x2="70" y2="103" stroke="var(--color-text-primary)" strokeDasharray="5 4" />
          <text x="92" y="50" fill="var(--color-cyan)" fontSize="12">convex outline</text>
        </g>
      )}
      <text x="14" y="22" fill="var(--color-text-muted)" fontSize="10" letterSpacing="1">SYNTHETIC VECTOR · NOT A PHOTO</text>
    </svg>
  );
}

export default function App() {
  const [connection, setConnection] = useState<Connection>('checking');
  const [info, setInfo] = useState<ApiInfo | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [productClass, setProductClass] = useState(2);
  const [modelAssist, setModelAssist] = useState(false);
  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [demoReportHash, setDemoReportHash] = useState<string | null>(null);
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => {
    if (IS_GITHUB_PAGES_DEMO) {
      setConnection('offline');
      return;
    }
    const controller = new AbortController();
    Promise.all([
      fetch('/health', { signal: controller.signal }).then((response) => {
        if (!response.ok) throw new Error('Health check failed');
        return response.json() as Promise<{ status: string }>;
      }),
      fetch('/v1/info', { signal: controller.signal }).then((response) => {
        if (!response.ok) throw new Error('Runtime information unavailable');
        return response.json() as Promise<ApiInfo>;
      }),
    ])
      .then(([, runtimeInfo]) => {
        setInfo(runtimeInfo);
        setConnection('online');
      })
      .catch((caught: unknown) => {
        if (caught instanceof DOMException && caught.name === 'AbortError') return;
        setConnection('offline');
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!file) {
      setPreviewUrl(null);
      return;
    }
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  useEffect(() => () => requestRef.current?.abort(), []);

  function chooseFile(selected: File | undefined) {
    setInspection(null);
    setError(null);
    if (!selected) {
      setFile(null);
      return;
    }
    if (!['image/jpeg', 'image/png'].includes(selected.type)) {
      setFile(null);
      setError('Choose a JPEG or PNG photo.');
      return;
    }
    if (selected.size > MAX_FILE_BYTES) {
      setFile(null);
      setError('The image must be 10 MiB or smaller.');
      return;
    }
    setFile(selected);
  }

  async function runInspection(selectedClass: number) {
    if (!file) {
      setError('Choose a photo before starting analysis.');
      return;
    }
    requestRef.current?.abort();
    const controller = new AbortController();
    requestRef.current = controller;
    setBusy(true);
    setError(null);
    setInspection(null);
    try {
      const params = new URLSearchParams({
        product_class: String(selectedClass),
        model_assist: String(modelAssist),
      });
      const response = await fetch(`/v1/inspect?${params}`, {
        method: 'POST',
        headers: { 'Content-Type': file.type },
        body: file,
        signal: controller.signal,
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? 'Photo analysis failed.');
      setInspection(result as Inspection);
    } catch (caught) {
      if (caught instanceof DOMException && caught.name === 'AbortError') return;
      setError(caught instanceof Error ? caught.message : 'Photo analysis failed.');
    } finally {
      if (requestRef.current === controller) {
        requestRef.current = null;
        setBusy(false);
      }
    }
  }

  function submitInspection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void runInspection(productClass);
  }

  function changeProductClass(value: string) {
    const nextClass = Number(value);
    setProductClass(nextClass);
    if (inspection && file) void runInspection(nextClass);
  }

  async function downloadIllustrativeReport() {
    const scenarioRows = DEMO_SCENES.map((scene) => (
      `<li><strong>Joint ${scene.id}: Class ${scene.referenceClass} ${scene.conditionLabel}</strong> — ${scene.exampleInput}. Scripted UI fixture expectation: ${scene.fixtureLabel}. <em>This is fixture metadata only; not measured, inspected, or graded.</em></li>`
    )).join('');
    const htmlReport = `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>JointCheck illustrative evidence</title><style>body{font:16px/1.5 system-ui,sans-serif;max-width:800px;margin:40px auto;padding:0 20px;color:#17202a} .notice{border:2px solid #9b3b16;padding:16px;background:#fff4ed} footer{border-top:1px solid #aaa;margin-top:24px;padding-top:12px;overflow-wrap:anywhere}</style></head><body><h1>JointCheck — illustrative demo report</h1><div class="notice"><strong>SYNTHETIC UI FIXTURES — NOT AN INSPECTION CERTIFICATE.</strong><p>The ACCEPT/REJECT strings listed here are scripted test-fixture expectations only. These synthetic vectors are not photographs or measurements and do not represent CV results, IPC-A-610 determinations, or production verdicts. No calibration or inspection grading was performed.</p></div><p>Illustrative class example selected in the UI: Class ${productClass}. No calibration or grading was performed.</p><h2>Illustrative scenario inputs</h2><ul>${scenarioRows}</ul><footer><strong>Integrity note:</strong> a SHA-256 checksum can detect a byte change only when compared with a separately trusted copy. It is not a digital signature or tamper-proof certification.</footer></body></html>`;
    try {
      const reportBytes = new TextEncoder().encode(htmlReport);
      const digest = await crypto.subtle.digest('SHA-256', reportBytes);
      const checksum = Array.from(new Uint8Array(digest), (byte) => byte.toString(16).padStart(2, '0')).join('');
      setDemoReportHash(checksum);
      const url = URL.createObjectURL(new Blob([reportBytes], { type: 'text/html;charset=utf-8' }));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'jointcheck-illustrative-demo-report.html';
      link.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      setError('Browser SHA-256 support is unavailable; no report was downloaded.');
    }
  }

  return (
    <main className="shell">
      <header className="topbar">
        <a className="wordmark" href={IS_GITHUB_PAGES_DEMO ? '/jointcheck-solder-inspection/' : '/'} aria-label="JointCheck home">
          <span className="mark" aria-hidden="true">JC</span>
          <span>JointCheck</span>
        </a>
        <span className="prototype-label">EXPERIMENTAL PROTOTYPE</span>
      </header>

      <section className="hero" aria-labelledby="page-title" data-demo-shot="hook">
        <p className="eyebrow">SOLDER WORKMANSHIP · PROOF-FIRST TOOLING</p>
        <h1 id="page-title">Explore the image. Withhold the verdict.</h1>
        <p className="intro">
          {IS_GITHUB_PAGES_DEMO
            ? 'Explore three offline synthetic vector schematics and generate a local illustrative HTML report. GitHub Pages has no analysis backend; photo inspection is unavailable in this static demo.'
            : 'Upload a macro photo to calculate basic image-quality metrics and propose contour regions. The CV stage is not a trained joint detector, and this prototype deliberately does not make production grading decisions.'}
        </p>
      </section>

      <section className="results" id="demo-scenes" aria-labelledby="demo-title" data-demo-shot="inspection">
        <div className="results-title-row">
          <div>
            <p className="eyebrow">STATIC CANVAS · OFFLINE</p>
            <h2 id="demo-title">Three illustrative joint geometries</h2>
          </div>
          <label className="demo-selector" htmlFor="demo-class-selector">Class example
            <select id="demo-class-selector" value={productClass} onChange={(event) => changeProductClass(event.target.value)}>
              <option value={1}>Class 1</option>
              <option value={2}>Class 2</option>
              <option value={3}>Class 3</option>
            </select>
          </label>
          <span className="verdict-badge" style={{ color: 'var(--color-text-muted)', borderColor: 'var(--color-text-muted)' }}>NOT GRADED</span>
        </div>
        <p className="fixture-disclaimer" role="note">{DEMO_FIXTURE_PROFILE.id} · {DEMO_FIXTURE_PROFILE.scope}. The green/red labels below are scripted fixture expectations only—not CV outputs, measured inspection results, IPC judgments, or production grades. Calibration: {DEMO_FIXTURE_PROFILE.calibrated ? 'enabled' : 'not performed'}; inspection grading: {DEMO_FIXTURE_PROFILE.inspectionVerdictsEnabled ? 'enabled' : 'disabled'}.</p>
        <div className="result-grid">
          {DEMO_SCENES.map((scene) => (
            <article className="result-panel" key={scene.id} data-demo-scene={scene.id} data-demo-shot={scene.id === 'C' ? 'geometry-overlay' : undefined}>
              <h3>Joint {scene.id} · Class {scene.referenceClass} · {scene.conditionLabel}</h3>
              <DemoIllustration sceneId={scene.id} />
              <p><strong>{scene.exampleInput}</strong></p>
              <p className="muted">Current class selector: Class {productClass}. {scene.note}</p>
              <span className="fixture-scope">SYNTHETIC FIXTURE · NOT AN INSPECTION RESULT</span>
              <span className="verdict-badge fixture-label" style={{ color: verdictColor(scene.fixtureLabel), borderColor: verdictColor(scene.fixtureLabel) }}>EXPECTED UI LABEL · {scene.fixtureLabel}</span>
            </article>
          ))}
        </div>
        <div className="button-row" data-demo-shot="audit">
          <button className="secondary-button" type="button" data-demo-export onClick={() => void downloadIllustrativeReport()}>
            Generate illustrative HTML report
          </button>
          <span className="muted">Local-only checksum; not a signature or verified certificate.</span>
        </div>
        {demoReportHash && <p className="muted" role="status">SHA-256 of downloaded report bytes: <code>{demoReportHash}</code> · recomputable checksum, not proof of measurement truth.</p>}
      </section>

      <section className="status-card service-card" aria-labelledby="service-title">
        <div className="status-heading">
          <div>
            <p className="eyebrow">RUNTIME</p>
            <h2 id="service-title">Service connection</h2>
          </div>
          <span className={`connection connection-${connection}`} role="status">
            <span className="connection-dot" />
            {connection === 'checking' ? 'Checking' : connection === 'online' ? 'Online' : 'Offline'}
          </span>
        </div>
        <p className="status-copy">
          {connection === 'online'
            ? 'Image quality and experimental contour proposals are available.'
            : connection === 'offline'
              ? IS_GITHUB_PAGES_DEMO
                ? 'Static GitHub Pages demo: the backend is not hosted here. Illustrative scenarios and local report generation work offline; live photo inspection is unavailable.'
                : 'Could not reach the backend. Start it with make demo, then refresh this page.'
              : 'Checking backend health and capabilities…'}
        </p>
        {info && (
          <dl className="details">
            <div><dt>Production grading</dt><dd>{info.production_grading_available ? 'Available' : 'Disabled'}</dd></div>
            <div><dt>Optional model</dt><dd>{info.model_assistance_configured ? 'Configured' : 'Not configured'}</dd></div>
          </dl>
        )}
      </section>

      <section className="inspection-card" aria-labelledby="upload-title">
        <div className="section-heading">
          <p className="eyebrow">01 / IMAGE INTAKE</p>
          <h2 id="upload-title">Analyze one photo</h2>
          <p>{IS_GITHUB_PAGES_DEMO ? 'Photo analysis is unavailable on this static GitHub Pages demo.' : 'JPEG or PNG · maximum 10 MiB · image is processed by the backend CV stage.'}</p>
        </div>
        <form onSubmit={submitInspection}>
          <label className="file-picker" htmlFor="photo-input" aria-disabled={IS_GITHUB_PAGES_DEMO}>
            <span className="upload-icon" aria-hidden="true">＋</span>
            <span>{file ? file.name : 'Choose a macro photo'}</span>
            <span className="file-hint">{IS_GITHUB_PAGES_DEMO ? 'Unavailable on Pages' : file ? `${(file.size / 1024).toFixed(0)} KB` : 'JPEG or PNG'}</span>
          </label>
          <input
            id="photo-input"
            className="visually-hidden"
            type="file"
            accept="image/jpeg,image/png"
            disabled={IS_GITHUB_PAGES_DEMO}
            onChange={(event) => chooseFile(event.currentTarget.files?.[0])}
          />
          <div className="form-row">
            <label className="select-label" htmlFor="product-class">Reference class</label>
            <select id="product-class" value={productClass} onChange={(event) => changeProductClass(event.target.value)}>
              <option value={1}>Class 1</option>
              <option value={2}>Class 2</option>
              <option value={3}>Class 3</option>
            </select>
          </div>
          <label className={`consent-toggle ${!info?.model_assistance_configured ? 'is-disabled' : ''}`}>
            <input
              type="checkbox"
              checked={modelAssist}
              disabled={!info?.model_assistance_configured || busy}
              onChange={(event) => setModelAssist(event.target.checked)}
            />
            <span>
              <strong>Request optional model suggestions</strong>
              <small>
                {info?.model_assistance_configured
                  ? 'When enabled, the photo is sent to the configured vision API. Suggestions are unverified and never grade.'
                  : 'Configure NEBIUS_API_KEY on the backend to enable this explicit opt-in. No image is sent otherwise.'}
              </small>
            </span>
          </label>
          <div className="button-row">
            <button className="primary-button" type="submit" disabled={IS_GITHUB_PAGES_DEMO || !file || busy || connection !== 'online'}>
              {IS_GITHUB_PAGES_DEMO ? 'Photo analysis unavailable on Pages' : busy ? 'Analyzing photo…' : 'Run experimental analysis'}
            </button>
            {busy && <button className="secondary-button" type="button" onClick={() => requestRef.current?.abort()}>Cancel</button>}
          </div>
          {error && <p className="error-message" role="alert">{error}</p>}
        </form>
      </section>

      {inspection && (
        <section className="results" aria-labelledby="results-title" aria-live="polite">
          <div className="results-title-row">
            <div>
              <p className="eyebrow">02 / EXPERIMENTAL ANALYSIS</p>
              <h2 id="results-title">Inspection evidence</h2>
            </div>
            <span
              className="verdict-badge"
              role="status"
              style={{ color: verdictColor(inspection.grading.verdict), borderColor: verdictColor(inspection.grading.verdict) }}
            >
              {inspection.grading.verdict}
            </span>
          </div>
          <div className="result-grid">
            <div className="result-panel image-panel">
              {previewUrl && <img src={previewUrl} alt="Uploaded solder-joint board photo" />}
              <p>{inspection.image.width} × {inspection.image.height}px · not calibrated</p>
              <code>SHA-256 {inspection.image.sha256.slice(0, 18)}…</code>
            </div>
            <div className="result-panel">
              <h3>Basic quality checks <span className="unvalidated">UNVALIDATED FLOORS</span></h3>
              <dl className="metrics">
                <div><dt>Laplacian variance</dt><dd>{inspection.quality.blur_laplacian_var.toFixed(2)}</dd></div>
                <div><dt>Clipped exposure</dt><dd>{inspection.quality.exposure_clipped_pct.toFixed(2)}%</dd></div>
                <div><dt>CV contour candidates</dt><dd>{inspection.candidate_count}</dd></div>
                <div><dt>Production verdict</dt><dd className="undetermined">{inspection.grading.verdict}</dd></div>
              </dl>
            </div>
          </div>

          <div className="result-panel regions-panel">
            <h3>Candidate regions <span>heuristic boxes, not confirmed joints</span></h3>
            {inspection.candidate_regions.length === 0
              ? <p className="muted">No contour candidates passed the experimental size filters.</p>
              : <div className="table-wrap"><table>
                <thead><tr><th>Region / box (px)</th><th>Contour area</th><th>Wetting angle</th><th>Fillet concavity (px⁻¹)</th><th>Wetting rule</th></tr></thead>
                <tbody>{inspection.candidate_regions.map((region) => {
                  const angle = region.measurements?.find((item) => item.quantity === 'wetting_angle_deg');
                  const concavity = region.geometry_diagnostics?.find((item) => item.name === 'fillet_concavity');
                  const wettingVerdict = region.rule_verdicts?.find((item) => item.rule_id === 'JC-WET-001');
                  const rowVerdict = wettingVerdict?.verdict ?? 'UNDETERMINED';
                  return (
                    <tr key={region.region_id}>
                      <td><code>{region.region_id}</code><br />{region.bbox_px.x}, {region.bbox_px.y} · {region.bbox_px.width}×{region.bbox_px.height}</td>
                      <td>{region.features.contour_area_px.toFixed(0)} px²</td>
                      <td>{angle?.computable && angle.value !== null ? `${angle.value.toFixed(0)}°` : 'UNDETERMINED'}{angle?.not_computable_reason && <small>{angle.not_computable_reason.replaceAll('_', ' ')}</small>}</td>
                      <td>{concavity?.computable && concavity.curvature_px_inv !== null ? `${concavity.curvature_px_inv.toPrecision(3)} px⁻¹` : 'UNDETERMINED'}{concavity?.not_computable_reason && <small>{concavity.not_computable_reason.replaceAll('_', ' ')}</small>}</td>
                      <td><span className="verdict-badge" style={{ color: verdictColor(rowVerdict), borderColor: verdictColor(rowVerdict) }}>{rowVerdict}</span></td>
                    </tr>
                  );
                })}</tbody>
              </table></div>}
          </div>

          <div className="result-panel model-panel">
            <h3>Optional model assistance <span>{inspection.model_assistance.status.replaceAll('_', ' ')}</span></h3>
            {inspection.model_assistance.observations.length === 0
              ? <p className="muted">{inspection.model_assistance.message ?? 'No model suggestions were requested or returned.'}</p>
              : inspection.model_assistance.observations.map((observation) => (
                <article className="observation" key={observation.region_id}>
                  <strong>{observation.region_id} · {observation.joint_type.replaceAll('_', ' ')}</strong>
                  <span>{observation.condition_codes.length ? observation.condition_codes.join(', ') : 'No condition code suggested'}</span>
                  <small>{observation.note} · confidence {Math.round(observation.confidence * 100)}% · human review required</small>
                </article>
              ))}
          </div>

          <div className="safety-callout">
            <h3>Why the result abstains</h3>
            <ul>{inspection.grading.reason_codes.map((reason) => <li key={reason}>{reason.replaceAll('_', ' ')}</li>)}</ul>
            <p>{inspection.disclaimer}</p>
            <button
              className="secondary-button"
              type="button"
              disabled
              title="A verified report endpoint and network-disabled Sandbox validation are not available."
            >
              Download Verified Inspection Pack
            </button>
            <p className="muted">Unavailable until calibrated rules, trusted measurements, and Sandbox validation are implemented.</p>
          </div>
        </section>
      )}

      <section className="notice" aria-labelledby="safety-title" data-demo-shot="fail-closed">
        <h2 id="safety-title">Not for production decisions</h2>
        <p>
          If trusted calibration, segmentation, or measurement evidence is missing,
          the safe result is UNDETERMINED. This photo route currently has no pad/solder
          segmentation or calibration source and never issues production ACCEPT/REJECT.
          Optional model suggestions remain unverified and advisory only.
        </p>
      </section>

      <section className="notice" aria-labelledby="limitations-title" id="calibration-status" data-demo-shot="limitations">
        <h2 id="limitations-title">Honest limitations</h2>
        <p>
          The three diagrams above are synthetic and are not a training set. The repository
          has no labelled evaluation images, no reviewed numeric workmanship rules, and no
          edge-hardware latency benchmark. Do not infer performance or standards compliance
          from this canvas.
        </p>
      </section>

      <footer data-demo-shot="close">JointCheck · Experimental geometry and a fail-closed gate; no validated performance claim. API status is at <code>/v1/info</code>.</footer>
    </main>
  );
}
