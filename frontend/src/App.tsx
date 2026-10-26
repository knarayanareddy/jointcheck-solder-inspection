import { FormEvent, useEffect, useRef, useState } from 'react';

type ApiInfo = {
  status: string;
  inspection_available: boolean;
  production_grading_available: boolean;
  capabilities: string[];
  model_assistance_configured: boolean;
};

type Region = {
  region_id: string;
  bbox_px: { x: number; y: number; width: number; height: number };
  features: Record<string, number>;
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
  const requestRef = useRef<AbortController | null>(null);

  useEffect(() => {
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

  async function submitInspection(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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
        product_class: String(productClass),
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

  return (
    <main className="shell">
      <header className="topbar">
        <a className="wordmark" href="/" aria-label="JointCheck home">
          <span className="mark" aria-hidden="true">JC</span>
          <span>JointCheck</span>
        </a>
        <span className="prototype-label">EXPERIMENTAL PROTOTYPE</span>
      </header>

      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">SOLDER WORKMANSHIP · PROOF-FIRST TOOLING</p>
        <h1 id="page-title">Explore the image. Withhold the verdict.</h1>
        <p className="intro">
          Upload a macro photo to calculate basic image-quality metrics and propose
          contour regions. The CV stage is not a trained joint detector, and this
          prototype deliberately does not make production grading decisions.
        </p>
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
              ? 'Could not reach the backend. Start it with make demo, then refresh this page.'
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
          <p>JPEG or PNG · maximum 10 MiB · image is processed locally by the CV stage.</p>
        </div>
        <form onSubmit={submitInspection}>
          <label className="file-picker" htmlFor="photo-input">
            <span className="upload-icon" aria-hidden="true">＋</span>
            <span>{file ? file.name : 'Choose a macro photo'}</span>
            <span className="file-hint">{file ? `${(file.size / 1024).toFixed(0)} KB` : 'JPEG or PNG'}</span>
          </label>
          <input
            id="photo-input"
            className="visually-hidden"
            type="file"
            accept="image/jpeg,image/png"
            onChange={(event) => chooseFile(event.currentTarget.files?.[0])}
          />
          <div className="form-row">
            <label className="select-label" htmlFor="product-class">Reference class</label>
            <select id="product-class" value={productClass} onChange={(event) => setProductClass(Number(event.target.value))}>
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
            <button className="primary-button" type="submit" disabled={!file || busy || connection !== 'online'}>
              {busy ? 'Analyzing photo…' : 'Run experimental analysis'}
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
            <span className="verdict-badge">UNDETERMINED</span>
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
                <thead><tr><th>Region</th><th>Box (px)</th><th>Contour area</th><th>Interpretation</th></tr></thead>
                <tbody>{inspection.candidate_regions.map((region) => (
                  <tr key={region.region_id}>
                    <td><code>{region.region_id}</code></td>
                    <td>{region.bbox_px.x}, {region.bbox_px.y} · {region.bbox_px.width}×{region.bbox_px.height}</td>
                    <td>{region.features.contour_area_px.toFixed(0)} px²</td>
                    <td>{region.interpretation.replaceAll('_', ' ')}</td>
                  </tr>
                ))}</tbody>
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
          </div>
        </section>
      )}

      <section className="notice" aria-labelledby="safety-title">
        <h2 id="safety-title">Not for production decisions</h2>
        <p>
          Contour proposals are not joint detections. Model suggestions, when
          explicitly enabled, are unverified and advisory only. Workmanship
          thresholds remain provisional; the system never issues a production
          accept/reject grade. No image is sent to a model unless the opt-in is selected.
        </p>
      </section>

      <footer>JointCheck · Prototype scope and API status are available at <code>/v1/info</code>.</footer>
    </main>
  );
}
