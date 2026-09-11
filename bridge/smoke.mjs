// Real HTTP + real Python neural service; simulated bot methods (no Minecraft server).
import assert from 'node:assert/strict'
import { applyAction, validAction } from './control.mjs'
const url = process.env.NEURAL_URL || 'http://127.0.0.1:8765'
async function post(path, data) {
  const r = await fetch(url + path, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data), signal: AbortSignal.timeout(5000) })
  assert.equal(r.status, 200)
  return r.json()
}
let seq = 0
let { session } = await post('/session', { protocol: 1 })
const bot = { entity: { yaw: 0 }, forward: false,
  setControlState: (_key, value) => { bot.forward = value },
  look: async yaw => { bot.entity.yaw = yaw } }
let moved = false
for (let i=0; i<30; i++) {
  const action = await post('/step', { protocol: 1, session, seq: ++seq,
    observation: { drive: 1, obstacle_left: 1, obstacle_right: 0 } })
  assert.ok(validAction(action, session, seq))
  await applyAction(bot, action, false)
  moved ||= bot.forward
}
assert.ok(moved, 'downstream spikes must enable movement')
assert.ok(bot.entity.yaw < -0.2, 'left stimulus must produce downstream right turn')
console.log(JSON.stringify({ test: 'http-neural-adapter', moved, yaw: bot.entity.yaw, minecraft_server: false }))
