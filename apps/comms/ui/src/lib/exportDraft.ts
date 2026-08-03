function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

/**
 * Downloads the draft as a `.doc` file Word can open, entirely client-side.
 *
 * This is a Word-compatible HTML document (the "MHTML trick"), not a real `.docx` — there is no
 * DOCX-writer dependency in this package, and this staff tool has no server round-trip to do the
 * conversion elsewhere. Escaping the draft text matters here specifically: it comes back from the
 * model gateway, not from a trusted template, so an unescaped `<` or `&` in a generated draft
 * would corrupt the exported document's markup.
 */
export function downloadAsWord(draft: string, filenameStem: string): void {
  const html = `<!doctype html><html><head><meta charset="utf-8"></head><body><pre style="white-space:pre-wrap;font-family:Calibri,sans-serif;">${escapeHtml(draft)}</pre></body></html>`
  const blob = new Blob([html], { type: 'application/msword' })
  const url = URL.createObjectURL(blob)
  try {
    const link = document.createElement('a')
    link.href = url
    link.download = `${filenameStem}.doc`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } finally {
    URL.revokeObjectURL(url)
  }
}

/**
 * Exports the draft as a PDF via the browser's own print-to-PDF, scoped to just the draft by the
 * `.print-draft` rule in `index.css`. No PDF-generation library: `window.print()` is the standard
 * dependency-free route to a PDF in the browser, and "Save as PDF" is universally available in
 * print destinations — adding a client-side PDF renderer for one staff tool isn't worth the
 * dependency weight.
 */
export function exportAsPdf(): void {
  window.print()
}
