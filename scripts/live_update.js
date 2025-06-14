// scripts/live_update.js

const fs = require("fs");
const path = require("path");
const dukas = require("dukascopy-node");
const dayjs = require("dayjs");

const symbols = [
  "eurusd", "gbpusd", "usdjpy", "audusd", "usdchf", "nzdusd",
  "usdcad", "eurjpy", "eurnzd", "aedcny", "audcad", "audchf",
  "audnzd", "cadjpy", "chfjpy", "eurgbp"
];

const timeframes = ["m1", "m5"]; // Only live intervals

const now = new Date();
const fiveMinAgo = dayjs(now).subtract(10, "minute").toDate();

(async () => {
  for (let symbol of symbols) {
    for (let tf of timeframes) {
      try {
        const candles = await dukas.getCandles({
          instrument: symbol.toUpperCase(),
          dates: { from: fiveMinAgo, to: now },
          timeframe: tf
        });

        const file = path.join(__dirname, `../data/${symbol}_${tf}.csv`);
        const rows = candles.map(c => [
          new Date(c.timestamp).toISOString(),
          c.open, c.high, c.low, c.close, c.volume
        ]);

        const exists = fs.existsSync(file);
        if (!exists) fs.writeFileSync(file, "timestamp,open,high,low,close,volume\n");

        const csv = rows.map(r => r.join(",")).join("\n");
        fs.appendFileSync(file, csv + "\n");

        console.log(`✅ Appended ${rows.length} rows to ${symbol}_${tf}.csv`);
      } catch (e) {
        console.error(`❌ Error ${symbol}@${tf}: ${e.message}`);
      }
    }
  }
})();
          
