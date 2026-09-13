export const normalize = value => value.toLowerCase().replaceAll("’", "'");
export const tokenPattern = () => /[A-Za-z0-9]+(?:[’'\-][A-Za-z0-9]+)*/g;

export function markedText(text, term) {
  const fragment = document.createDocumentFragment();
  let cursor = 0;
  for (const match of text.matchAll(tokenPattern())) {
    if (normalize(match[0]) !== term) continue;
    fragment.append(document.createTextNode(text.slice(cursor, match.index)));
    const mark = document.createElement("mark");
    mark.textContent = match[0];
    fragment.append(mark);
    cursor = match.index + match[0].length;
  }
  fragment.append(document.createTextNode(text.slice(cursor)));
  return fragment;
}
