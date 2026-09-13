export const SCENARIOS = Object.freeze([
  { name: "Shared work", cost: 20, automation: 60, supervision: 50 },
  { name: "Cheap, lightly watched", cost: 5, automation: 80, supervision: 20 },
  { name: "Hands on", cost: 20, automation: 60, supervision: 90 },
  { name: "Expensive automation", cost: 100, automation: 90, supervision: 100 },
]);

// Authored accounting for 100 tasks; one manual task costs one human hour.
export function calculateModel({ cost, automation, supervision }) {
  if (![cost, automation, supervision].every(Number.isFinite)
    || cost < 1 || cost > 100 || automation < 0 || automation > 100 || supervision < 0 || supervision > 100) {
    throw new RangeError("Cost must be 1-100%; automation and supervision must be 0-100%.");
  }
  const automated = automation;
  const reviewed = automated * supervision / 100;
  const manual = 100 - automated;
  const reviewHours = reviewed * 0.25;
  const humanHours = manual + reviewHours;
  const machineCost = automated * cost / 100;
  const totalCost = humanHours + machineCost;
  const unreviewed = automated - reviewed;
  const defects = unreviewed * 0.20 + reviewed * 0.04;
  return { manual, automated, reviewed, unreviewed, reviewHours, humanHours, machineCost, totalCost, defects, savings: 100 - totalCost };
}
