import { useMemo } from 'react'

/** Indonesian number formatting: 1.040 / 12,5 / 63% / Rp 4.500. */
const NUMERIC = /^(?:rp\s*)?[-+]?\d[\d.,]*\s*%?$/i

/** Rows whose label marks a summary line get the emphasised bottom row. */
const TOTAL_LABEL = /^(jumlah|total)\b/i

type PipeTable = { header: string[]; rows: string[][] }

/**
 * `interpretasi_data` stimuli are stored as a pipe-delimited table (header line
 * first). Everything else — reading passages, `analisis_teks` prose — is plain
 * text and must be left alone, so a table is only recognised when every line
 * carries the same number of columns.
 */
export function parsePipeTable(text: string): PipeTable | null {
  const lines = text
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
  if (lines.length < 2 || !lines.every((line) => line.includes('|'))) return null

  const cells = lines.map((line) => line.split('|').map((cell) => cell.trim()))
  const width = cells[0].length
  if (width < 2 || !cells.every((row) => row.length === width)) return null

  return { header: cells[0], rows: cells.slice(1) }
}

export default function Passage({ text }: { text: string }) {
  const table = useMemo(() => parsePipeTable(text), [text])

  if (!table) return <div className="passage">{text}</div>

  // Column 0 holds the row label, so it stays left-aligned even when it looks
  // numeric (years, sizes); the rest are right-aligned once every cell is a number.
  const numeric = table.header.map(
    (_, col) => col > 0 && table.rows.every((row) => NUMERIC.test(row[col])),
  )

  return (
    <div className="passage-table-wrap" role="region" tabIndex={0} aria-label="Tabel data soal">
      <table className="passage-table">
        <thead>
          <tr>
            {table.header.map((cell, col) => (
              <th key={col} scope="col" className={numeric[col] ? 'num' : undefined}>
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, index) => (
            <tr key={index} className={TOTAL_LABEL.test(row[0]) ? 'is-total' : undefined}>
              {row.map((cell, col) =>
                col === 0 ? (
                  <th key={col} scope="row">
                    {cell}
                  </th>
                ) : (
                  <td key={col} className={numeric[col] ? 'num' : undefined}>
                    {cell}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
