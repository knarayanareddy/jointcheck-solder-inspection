#!/usr/bin/env node

// Records the static Pages demo. Run with `node scripts/record-demo.ts` after
// starting `npm run preview -- --host 0.0.0.0 --port 4173` in frontend/.
import { createRequire } from 'node:module';
import { execFileSync } from 'node:child_process';
import { mkdtemp, mkdir, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(resolve(root, 'frontend/package.json'));
const { chromium } = require('playwright');
const outputDirectory = resolve(root, 'docs/media');
const outputFile = resolve(outputDirectory, 'jointcheck-demo.mp4');
const demoUrl = process.env.JOINTCHECK_DEMO_URL ?? 'http://127.0.0.1:4173/jointcheck-solder-inspection/';
const totalSeconds = 165;
const frameCount = totalSeconds * 30;

const shots = [
  { name: 'hook', locator: '[data-demo-shot="hook"]', seconds: 20 },
  { name: 'inspection', locator: '[data-demo-scene="A"]', seconds: 25 },
  { name: 'geometry-overlay', locator: '[data-demo-scene="C"]', seconds: 25 },
  { name: 'audit', locator: '[data-demo-export]', seconds: 25 },
  { name: 'fail-closed', locator: '[data-demo-shot="fail-closed"]', seconds: 25 },
  { name: 'limitations', locator: '[data-demo-shot="limitations"]', seconds: 25 },
  { name: 'close', locator: '[data-demo-shot="close"]', seconds: 20 },
];

if (shots.reduce((sum, shot) => sum + shot.seconds, 0) !== totalSeconds) {
  throw new Error('Demo shot schedule must total exactly 165 seconds.');
}

const temporaryDirectory = await mkdtemp(resolve(tmpdir(), 'jointcheck-recording-'));
let browser;
let context;
try {
  await mkdir(outputDirectory, { recursive: true });
  browser = await chromium.launch({ headless: true });
  context = await browser.newContext({
    acceptDownloads: true,
    viewport: { width: 1440, height: 900 },
    recordVideo: { dir: temporaryDirectory, size: { width: 1440, height: 900 } },
  });
  const page = await context.newPage();
  const browserErrors = [];
  page.on('pageerror', (error) => browserErrors.push(error.message));
  await page.goto(demoUrl, { waitUntil: 'networkidle', timeout: 30_000 });
  await page.locator('[data-demo-shot="hook"]').waitFor({ state: 'visible' });
  await page.getByRole('heading', { name: 'Three illustrative joint geometries' }).waitFor();

  for (const shot of shots) {
    const target = page.locator(shot.locator).first();
    await target.scrollIntoViewIfNeeded();
    if (shot.name === 'inspection') {
      await page.getByLabel('Class example').selectOption('1');
    } else if (shot.name === 'defect-example') {
      await page.getByLabel('Class example').selectOption('3');
    } else if (shot.name === 'audit') {
      await page.getByRole('button', { name: 'Generate illustrative HTML report' }).click();
      await page.getByText(/SHA-256 of downloaded report bytes/).waitFor({ state: 'visible' });
    }
    console.log(`Recording ${shot.name} (${shot.seconds}s)`);
    await page.waitForTimeout(shot.seconds * 1000);
  }

  if (browserErrors.length) throw new Error(`Browser page error: ${browserErrors.join('; ')}`);
  const recording = page.video();
  await context.close();
  context = undefined;
  const webmFile = await recording.path();
  await browser.close();
  browser = undefined;

  const sourceDuration = Number(execFileSync('ffprobe', [
    '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', webmFile,
  ], { encoding: 'utf8' }).trim());
  if (!Number.isFinite(sourceDuration) || sourceDuration <= 0) {
    throw new Error('ffprobe could not read the Playwright WebM recording duration.');
  }
  // Page setup is included in Playwright's recording. Normalize the entire capture
  // to the timed 165-second narration, keeping every shot and its relative timing.
  const ptsScale = (totalSeconds / sourceDuration).toPrecision(12);
  execFileSync('ffmpeg', [
    '-y', '-i', webmFile,
    '-vf', `setpts=${ptsScale}*PTS,fps=30`,
    '-frames:v', String(frameCount),
    '-an', '-c:v', 'libx264', '-preset', 'medium', '-crf', '23',
    '-pix_fmt', 'yuv420p', '-movflags', '+faststart', outputFile,
  ], { stdio: 'inherit' });

  const finalDuration = Number(execFileSync('ffprobe', [
    '-v', 'error', '-show_entries', 'format=duration', '-of', 'default=noprint_wrappers=1:nokey=1', outputFile,
  ], { encoding: 'utf8' }).trim());
  if (Math.abs(finalDuration - totalSeconds) > 0.05) {
    throw new Error(`MP4 duration is ${finalDuration.toFixed(3)}s, expected 165.000s.`);
  }
  console.log(`Saved ${outputFile} (${finalDuration.toFixed(3)} seconds).`);
} catch (error) {
  const message = error instanceof Error ? error.message : String(error);
  if (message.includes('Executable doesn\'t exist') || message.includes('browserType.launch')) {
    console.error('Playwright Chromium is not installed. Install it with `cd frontend && npx playwright install chromium`.');
  } else if (message.includes('ENOENT') && (message.includes('ffmpeg') || message.includes('ffprobe'))) {
    console.error('ffmpeg and ffprobe are required for MP4 encoding; install ffmpeg and rerun the recorder.');
  }
  console.error(message);
  process.exitCode = 1;
} finally {
  if (context) await context.close().catch(() => {});
  if (browser) await browser.close().catch(() => {});
  await rm(temporaryDirectory, { recursive: true, force: true });
}
