import { afterEach, describe, expect, it, vi } from 'vitest'
import { downloadAsWord, exportAsPdf } from './exportDraft'

function stubBlobDownload() {
  const createObjectURL = vi.fn().mockReturnValue('blob:mock-url')
  const revokeObjectURL = vi.fn()
  vi.stubGlobal('URL', { ...URL, createObjectURL, revokeObjectURL })
  vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})
  return { createObjectURL, revokeObjectURL }
}

afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})

describe('downloadAsWord', () => {
  it('creates a Word-compatible blob download and cleans up the object URL', () => {
    const { createObjectURL, revokeObjectURL } = stubBlobDownload()
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click')

    downloadAsWord('Hello staff', 'newsletter-draft')

    expect(createObjectURL).toHaveBeenCalledTimes(1)
    const blob = createObjectURL.mock.calls[0]?.[0] as Blob
    expect(blob.type).toBe('application/msword')
    expect(clickSpy).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-url')
  })

  it('names the downloaded file after the given stem', () => {
    stubBlobDownload()
    const appendSpy = vi.spyOn(document.body, 'appendChild')

    downloadAsWord('text', 'linkedin_post-draft')

    const anchor = appendSpy.mock.calls[0]?.[0] as HTMLAnchorElement
    expect(anchor.download).toBe('linkedin_post-draft.doc')
  })

  it('escapes HTML-significant characters so a generated draft cannot corrupt the document', async () => {
    const { createObjectURL } = stubBlobDownload()

    downloadAsWord('Q&A: <script>alert(1)</script>', 'draft')

    const blob = createObjectURL.mock.calls[0]?.[0] as Blob
    const text = await blob.text()
    expect(text).toContain('Q&amp;A: &lt;script&gt;alert(1)&lt;/script&gt;')
    expect(text).not.toContain('<script>alert(1)</script>')
  })
})

describe('exportAsPdf', () => {
  it('delegates to the browser print dialog rather than a bundled PDF renderer', () => {
    const printSpy = vi.spyOn(window, 'print').mockImplementation(() => {})
    exportAsPdf()
    expect(printSpy).toHaveBeenCalledTimes(1)
  })
})
