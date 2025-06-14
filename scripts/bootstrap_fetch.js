// scripts/bootstrap_fetch.js

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
const from = new Date()
from.setFullYear(to.getFullYear() - 3)

async function fetchAll() {
  for (const symbol of symbols) {
    const candles = await dukas.getCandles({
      instrument: symbol,
      timeframe: 'm30',
      from,
      to
    })

    if (!candles || !candles.length) {
      console.log(`❌ No data for ${symbol}`)
      continue
    }

    const filePath = path.join('data', `dukascopy_${symbol}.csv`)
    const writer = createObjectCsvWriter({
      path: filePath,
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
    console.log(`✅ Wrote ${candles.length} records to ${filePath}`)
  }
}

fetchAll()
      
