export function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

export function control(text, action) {
  const button = element("button", "pg-button", text);
  button.type = "button";
  button.dataset.action = action;
  return button;
}

export function applyPreferences(root, preferences) {
  root.dataset.codeForced = String(preferences.forcedColors);
  root.dataset.codeReduced = String(preferences.reducedMotion);
}
