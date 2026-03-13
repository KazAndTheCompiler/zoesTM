function escapeHtml(input: string) {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function inlineFormat(text: string) {
  let out = escapeHtml(text);
  out = out.replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>');
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  out = out.replace(/\*([^*]+)\*/g, '<em>$1</em>');
  return out;
}

export function renderMarkdown(markdown: string) {
  const lines = (markdown || '').split(/\r?\n/);
  const html: string[] = [];
  let inList = false;

  const closeList = () => {
    if (inList) {
      html.push('</ul>');
      inList = false;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trimEnd();
    const trimmed = line.trim();
    if (!trimmed) {
      closeList();
      html.push('<div class="md-gap"></div>');
      continue;
    }
    const heading = trimmed.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      closeList();
      const level = heading[1].length;
      html.push(`<h${level}>${inlineFormat(heading[2])}</h${level}>`);
      continue;
    }
    if (/^[-*]\s+/.test(trimmed)) {
      if (!inList) {
        html.push('<ul>');
        inList = true;
      }
      html.push(`<li>${inlineFormat(trimmed.replace(/^[-*]\s+/, ''))}</li>`);
      continue;
    }
    closeList();
    html.push(`<p>${inlineFormat(trimmed)}</p>`);
  }

  closeList();
  return html.join('');
}
