import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import JSZip from 'jszip'
import { createReportZip, generateFilename } from '../DownloadManager'

/**
 * Feature: aws-infra-sizing-tool, Property 11: ZIP bundle contains all report artifacts
 * Validates: Requirements 6.3
 */
describe('Property 11: ZIP bundle contains all report artifacts', () => {
  const dateArb = fc.tuple(
    fc.integer({ min: 2000, max: 2099 }),
    fc.integer({ min: 1, max: 12 }),
    fc.integer({ min: 1, max: 28 })
  ).map(([year, month, day]) =>
    `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  )

  const artifactArb = fc.string({ minLength: 0, maxLength: 500 })

  it('ZIP contains exactly 3 entries and each matches the original content byte-for-byte', async () => {
    await fc.assert(
      fc.asyncProperty(
        artifactArb,
        artifactArb,
        artifactArb,
        dateArb,
        async (sizingMd, bomMd, htmlReport, date) => {
          const blob = await createReportZip(sizingMd, bomMd, htmlReport, date)
          const zip = await JSZip.loadAsync(blob)

          const entries = Object.keys(zip.files)
          expect(entries).toHaveLength(3)

          const expectedSizingName = generateFilename('AWS_Infrastructure_Sizing', date, 'md')
          const expectedBomName = generateFilename('AWS_Bill_of_Materials', date, 'md')
          const expectedHtmlName = generateFilename('AWS_InfraSizing_Report', date, 'html')

          expect(entries).toContain(expectedSizingName)
          expect(entries).toContain(expectedBomName)
          expect(entries).toContain(expectedHtmlName)

          const sizingContent = await zip.file(expectedSizingName)!.async('string')
          const bomContent = await zip.file(expectedBomName)!.async('string')
          const htmlContent = await zip.file(expectedHtmlName)!.async('string')

          expect(sizingContent).toBe(sizingMd)
          expect(bomContent).toBe(bomMd)
          expect(htmlContent).toBe(htmlReport)
        }
      ),
      { numRuns: 50 }
    )
  })
})
