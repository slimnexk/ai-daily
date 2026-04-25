const fs = require('fs');
const data = JSON.parse(fs.readFileSync('C:/Users/Administrator/.qclaw/workspace-agent-73f25d14/ai-daily/briefings/_staging_batch1.json', 'utf8'));
const output = JSON.stringify({
  batch: data.batch,
  date: data.date,
  featured: data.featured.length,
  llm: data.llm.length,
  github: data.github.length,
  world: data.world.length,
  trend: data.trend.length
}, null, 2);
fs.writeFileSync('C:/Users/Administrator/.qclaw/workspace-agent-73f25d14/ai-daily/briefings/verify.txt', output, 'utf8');
console.log('OK');