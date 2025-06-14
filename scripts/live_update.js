// scripts/live_update.js

const fs = require("fs");
const path = require("path");
const dukas = require("dukascopy-js");
const dayjs = require("dayjs");

const symbols = [
  "eurusd", "gbpusd", "usdjpy", "audusd", "usdchf", "nzdusd",
  "usdcad", "eurjpy", "eurnzd", "aedcny", "audcad", "audchf",
  "audnzd", "cadjpy", "chfjpy", "eurgbp"
];

const timeframes = ["m1", "m5", "m15", "m30", "h1", "h4"];

const durationMap = {
  m1: 2,
  m5: 10,
  m15: 30,
  m30: 60,
  h1: 180,
  h4: 720
};

const now = new Date();

function fetchCandles(symbol, tf, from, to) {
  return new Promise((resolve, reject) => {
    dukas.getCandles({
      instrument: symbol.toUpperCase(),
      dates: { from, to },
      timeframe: tf,
      format: "json"
    }, (err, data) => {
      if (err) return reject(err);
      resolve(data);
    });
  });
}

(async () => {
  for (let symbol of symbols) {
    for (let tf of timeframes) {
      const backMinutes = durationMap[tf] || 10;
      const from = dayjs(now).subtract(backMinutes, "minute").toDate();

      try {
        const candles = await fetchCandles(symbol, tf, from, now);

        const file = path.join(__dirname, `../data/${symbol}_${tf}.csv`);
        const rows = candles.map(c => [
          new Date(c.timestamp).toISOString(),
          c.open, c.high, c.low, c.close, c.volume
        ]);

        const exists = fs.existsSync(file);
        if (!exists) fs.writeFileSync(file, "timestamp,open,high,low,close,volume\n");

        const existingLines = exists ? fs.readFileSync(file, "utf8").split("\n") : [];
        const existingTimestamps = new Set(existingLines.map(l => l.split(",")[0]));

        const newRows = rows.filter(r => !existingTimestamps.has(r[0]));
        if (!newRows.length) {
          console.log(`ℹ️ No new candles for ${symbol}_${tf}`);
          continue;
        }

        const csv = newRows.map(r => r.join(",")).join("\n");
        fs.appendFileSync(file, csv + "\n");
        console.log(`✅ Appended ${newRows.length} rows to ${symbol}_${tf}.csv`);

      } catch (e) {
        console.error(`❌ Error ${symbol}@${tf}: ${e.message}`);
      }
    }
  }
})();
      
