// scripts/live_update.js

const dukas = require('dukascopy-node');
const fs = require('fs');
const path = require('path');

const symbols = [
  "eurusd", "gbpusd", "usdjpy", "audusd", "usdchf", "nzdusd",
  "usdcad", "eurjpy", "eurnzd", "aedcny", "audcad", "audchf",
  "audnzd", "cadjpy", "chfjpy", "eurgbp"
];

const END = new Date();
const START = new Date(END.getTime() - 1000 * 60 * 30); // last 30 minutes
const timeframe = 'm1';

(async () => {
  for (const sym of symbols) {
    const tempFile = path.resolve(__dirname, `../data/temp_${sym}.csv`);
    const finalFile = path.resolve(__dirname, `../data/dukascopy_${sym}.csv`);
    console.log(`🔁 Updating ${sym.toUpperCase()} from ${START.toISOString()} to ${END.toISOString()}`);

    await dukas.download({
      instrument: sym,
      dates: { from: START, to: END },
      timeframe,
      format: 'csv',
      csv: { filename: tempFile }
    });

    // Append new data to existing file
    if (fs.existsSync(finalFile)) {
      const newLines = fs.readFileSync(tempFile, 'utf8').split('\n').slice(1).join('\n');
      fs.appendFileSync(finalFile, `\n${newLines}`);
      fs.unlinkSync(tempFile);
    } else {
      fs.renameSync(tempFile, finalFile);
    }
  }

  // Trigger auto retrain
  const { exec } = require('child_process');
  exec('python3 strategy/train_model_historic.py', (err, stdout, stderr) => {
    if (err) {
      console.error(`❌ Retrain error: ${err.message}`);
    } else {
      console.log("✅ Retrain triggered.");
      console.log(stdout);
    }
  });
})();
