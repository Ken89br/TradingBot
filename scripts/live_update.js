// scripts/live_update.js

import dukas from 'dukascopy-node'
import fs from 'fs'
import path from 'path'
import { createObjectCsvWriter } from 'csv-writer'

const symbols = [
  "EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCHF", "NZDUSD",
  "USDCAD", "EURJPY", "EURNZD", "AEDCNY", "AUDCAD", "AUDCHF",
  "AUDNZD", "CADJPY", "CHFJPY", "EURGBP"
]

const to = new Date()
const from = new Date(to.getTime() - 60 * 60 * 1000) // last 60 minutes

async function updateLive() {
  for (const symbol of symbols) {
    const candles = await dukas.getCandles({
      instrument: symbol,
      timeframe: 'm30',
      from,
      to
    })

    if (!candles || !candles.length) {
      console.log(`⚠️ No live candles for ${symbol}`)
      continue
    }

    const filePath = path.join('data', `dukascopy_${symbol}.csv`)
    const existing = fs.existsSync(filePath)
      ? fs.readFileSync(filePath, 'utf-8').trim().split('\n').slice(1)
      : []

    const writer = createObjectCsvWriter({
      path: filePath,
      append: true,
      header: [
        { id: 'timestamp', title: 'timestamp' },
        { id: 'open', title: 'open' },
        { id: 'high', title: 'high' },
        { id: 'low', title: 'low' },
        { id: 'close', title: 'close' },
        { id: 'volume', title: 'volume' }
      ]
    })

    await writer.writeRecords(candles)
    console.log(`🟢 Appended ${candles.length} live candles to ${filePath}`)
  }
}

updateLive()
      
