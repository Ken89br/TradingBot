// scripts/bootstrap_fetch.js
import fs from "fs";
import path from "path";
import { getCandles } from "dukascopy-node";
import dayjs from "dayjs";
import { fileURLToPath } from "url";
import { dirname } from "path";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const symbols = [
  "eurusd", "gbpusd", "usdjpy", "audusd", "usdchf", "nzdusd",
  "usdcad", "eurjpy", "eurnzd", "aedcny", "audcad", "audchf",
  "audnzd", "cadjpy", "chfjpy", "eurgbp"
];

const timeframes = ["m1", "m5", "m15", "m30", "h1", "h4"];
const fromDate = dayjs().subtract(3, "year").toDate();
const toDate = new Date();

(async () => {
  for (let symbol of symbols) {
    for (let tf of timeframes) {
      console.log(`📥 Fetching ${symbol.toUpperCase()} @ ${tf}...`);
      try {
        const candles = await getCandles({
          instrument: symbol.toLowerCase(),
          dates: { from: fromDate, to: toDate },
          timeframe: tf
        });

        const rows = candles.map(c => [
          new Date(c.timestamp).toISOString(),
          c.open, c.high, c.low, c.close, c.volume
        ]);

        const file = path.join(__dirname, `../data/${symbol}_${tf}.csv`);
        const header = "timestamp,open,high,low,close,volume\n";
        fs.writeFileSync(file, header + rows.map(r => r.join(",")).join("\n"));
        console.log(`✅ Saved to ${file}`);
      } catch (err) {
        console.error(`❌ Error for ${symbol}@${tf}:`, err.message);
      }
    }
  }
})();
                                                 
