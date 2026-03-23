import { describe, it, expect } from 'vitest'
import * as fc from 'fast-check'
import { generateFilename } from '../DownloadManager'

/**
 * Feature: aws-infra-sizing-tool, Property 10: Download filenames include generation date
 * Validates: Requirements 6.2
 */
describe('Property 10: Download filenames include generation date', () => {
  const alphaUnderscore = fc.string({ unit: fc.constantFrom(...'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_'), minLength: 1, maxLength: 30 })
  const lowerAlpha = fc.string({ unit: fc.constantFrom(...'abcdefghijklmnopqrstuvwxyz'), minLength: 1, maxLength: 5 })

  const dateArb = fc.tuple(
    fc.integer({ min: 2000, max: 2099 }),
    fc.integer({ min: 1, max: 12 }),
    fc.integer({ min: 1, max: 28 })
  ).map(([year, month, day]) =>
    `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`
  )

  it('filename contains the YYYY-MM-DD date string', () => {
    fc.assert(
      fc.property(
        dateArb,
        alphaUnderscore,
        lowerAlpha,
        (date, baseName, extension) => {
          const filename = generateFilename(baseName, date, extension)
          expect(filename).toContain(date)
        }
      ),
      { numRuns: 200 }
    )
  })

  it('filename matches the pattern {baseName}_{date}.{extension}', () => {
    fc.assert(
      fc.property(
        dateArb,
        alphaUnderscore,
        lowerAlpha,
        (date, baseName, extension) => {
          const filename = generateFilename(baseName, date, extension)
          expect(filename).toBe(`${baseName}_${date}.${extension}`)
        }
      ),
      { numRuns: 200 }
    )
  })
})
