// scripts/bootstrap_fetch.js

const dukas = require('dukascopy-node');
const fs = require('fs');
const path = require('path');

const symbols = [
  "eurusd", "gbpusd", "usdjpy", "audusd", "usdchf", "nzdusd",
  "usdcad", "eurjpy", "eurnzd", "aedcny", "audcad", "audchf",
  "audnzd", "cadjpy", "chfjpy", "eurgbp"
];

const START = new Date("2021-01-01");
const END = new Date();
const timeframe = 'm1'; // 1-minute candles

(async () => {
  for (const sym of symbols) {
    const output = path.resolve(__dirname, `../data/dukascopy_${sym}.csv`);
    console.log(`⬇️ Downloading ${sym.toUpperCase()} from ${START.toISOString()} to ${END.toISOString()}`);
    await dukas.download({
      instrument: sym,
      dates: { from: START, to: END },
      timeframe,
      format: 'csv',
      csv: { filename: output }
    });
  }

  console.log("✅ All symbol data bootstrapped.");
})();
