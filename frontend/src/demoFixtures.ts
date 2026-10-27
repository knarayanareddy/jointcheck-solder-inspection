export type DemoScene = {
  id: 'A' | 'B' | 'C';
  title: string;
  referenceClass: number;
  fixtureLabel: 'ACCEPT' | 'REJECT';
  conditionLabel: string;
  exampleInput: string;
  note: string;
};

export const DEMO_FIXTURE_PROFILE = {
  id: 'jointcheck-ui-fixtures.v1',
  scope: 'display-only synthetic test fixtures',
  calibrated: false,
  inspectionVerdictsEnabled: false,
} as const;

export const DEMO_SCENES = [
  {
    id: 'A',
    title: 'Shallow fillet fixture',
    referenceClass: 1,
    fixtureLabel: 'ACCEPT',
    conditionLabel: 'Acceptable wetting',
    exampleInput: 'Authored shallow-fillet vector; unscaled synthetic input',
    note: 'The green label is a scripted fixture expectation, not an inspection result.',
  },
  {
    id: 'B',
    title: 'Bridge-span fixture',
    referenceClass: 2,
    fixtureLabel: 'ACCEPT',
    conditionLabel: 'Acceptable bridging',
    exampleInput: 'Authored bridge-shape vector; unscaled synthetic input',
    note: 'The green label is fixture metadata, not a rule about real solder bridging.',
  },
  {
    id: 'C',
    title: 'Excess-solder fixture',
    referenceClass: 3,
    fixtureLabel: 'REJECT',
    conditionLabel: 'Excess solder',
    exampleInput: 'Authored convex-bead vector; unscaled synthetic input',
    note: 'The red label is a scripted fixture expectation, not an IPC or production reject.',
  },
] as const satisfies readonly DemoScene[];
