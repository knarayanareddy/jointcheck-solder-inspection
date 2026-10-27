import assert from 'node:assert/strict';
import test from 'node:test';
import { DEMO_FIXTURE_PROFILE, DEMO_SCENES } from '../frontend/src/demoFixtures.ts';

test('demo fixture profile is synthetic, display-only, and not calibrated', () => {
  assert.equal(DEMO_FIXTURE_PROFILE.id, 'jointcheck-ui-fixtures.v1');
  assert.match(DEMO_FIXTURE_PROFILE.scope, /synthetic test fixtures/);
  assert.equal(DEMO_FIXTURE_PROFILE.calibrated, false);
  assert.equal(DEMO_FIXTURE_PROFILE.inspectionVerdictsEnabled, false);
});

test('the three scripted expected labels match the named synthetic fixture cases', () => {
  assert.deepEqual(
    DEMO_SCENES.map(({ id, referenceClass, conditionLabel, fixtureLabel }) => ({
      id, referenceClass, conditionLabel, fixtureLabel,
    })),
    [
      { id: 'A', referenceClass: 1, conditionLabel: 'Acceptable wetting', fixtureLabel: 'ACCEPT' },
      { id: 'B', referenceClass: 2, conditionLabel: 'Acceptable bridging', fixtureLabel: 'ACCEPT' },
      { id: 'C', referenceClass: 3, conditionLabel: 'Excess solder', fixtureLabel: 'REJECT' },
    ],
  );
  assert.ok(DEMO_SCENES.every((scene) => scene.exampleInput.includes('synthetic input')));
  assert.ok(DEMO_SCENES.every((scene) => scene.note.includes('fixture')));
});
