import mineflayer from 'mineflayer'
import { validAction, Lease } from './control.mjs'
import { Player, actuate } from './player.mjs'
import readline from 'node:readline'

const neuralUrl = process.env.NEURAL_URL || 'http://127.0.0.1:8765'
const endpoint = new URL(neuralUrl)
if (endpoint.protocol !== 'http:' || endpoint.hostname !== '127.0.0.1') throw new Error('Neural service must be loopback HTTP')
const host = process.env.MC_HOST || '127.0.0.1'
const auth = process.env.MC_AUTH || 'offline'
if (!['offline', 'microsoft'].includes(auth)) throw new Error('MC_AUTH must be offline or microsoft')
const port = Number(process.env.MC_PORT || 25565)
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid MC_PORT')
const bot = mineflayer.createBot({ host, port, auth,
  username: process.env.MC_USERNAME || 'FlyConnectome',
  version: process.env.MC_VERSION || '1.21.9', profilesFolder: './auth-cache' })
let alive = false, busy = false, epoch = 0, session, seq = 0, stopped = false
const player = new Player()
const terminal = readline.createInterface({ input: process.stdin, terminal: false })
terminal.on('line', line => {
  if (line.trim() === 'quit') return shutdown('Stopped by user')
  try {
    const result = player.command(line)
    if (result.changed) { epoch++; session = undefined; stop() }
    console.log(JSON.stringify(result))
  } catch (error) { console.error(error.message) }
})
console.log('Player controls: roam | follow <name> | stop | status | quit')
const stop = () => bot.clearControlStates()
const lease = new Lease(stop)
const watchdog = setInterval(() => lease.check(), 50)
async function post(path, body) {
  const response = await fetch(neuralUrl + path, { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    signal: AbortSignal.timeout(300) })
  if (!response.ok) throw new Error(`neural service: HTTP ${response.status}`)
  return response.json()
}
function invalidate() { alive = false; epoch++; session = undefined; player.resetMotion(); stop() }
bot.on('spawn', () => { invalidate(); alive = true })
bot.on('death', invalidate)
bot.on('physicsTick', async () => {
  if (!alive || stopped) return
  // Safety runs even while a neural HTTP request is in flight.
  const latest = player.sense(bot)
  if (latest.hold || latest.ground.hazard || latest.ground.upperBlocked) stop()
  if (busy) return
  busy = true
  const generation = epoch
  try {
    if (!session) {
      const reply = await post('/session', { protocol: 1 })
      if (generation !== epoch || stopped) return
      if (typeof reply.session !== 'string') throw new Error('Invalid session')
      session = reply.session; seq = 0
    }
    const observation = player.sense(bot)
    const current = ++seq
    const action = await post('/step', { protocol: 1, session, seq: current, observation: observation.neural })
    if (generation !== epoch || !alive || stopped) return
    if (!validAction(action, session, current)) throw new Error('Invalid or stale neural action')
    // Recheck geometry at actuation time, since the request may have taken time.
    const command = player.decide(bot, action, player.sense(bot))
    await actuate(bot, command)
    lease.renew()
    if (current % 20 === 0) console.log(JSON.stringify({ seq: current, ...action, player: player.lastStatus }))
  } catch (error) {
    stop(); session = undefined
    console.error(error.message)
  } finally { busy = false }
})
function shutdown(reason) {
  if (stopped) return
  stopped = true; invalidate(); clearInterval(watchdog); terminal.close()
  console.error(String(reason)); bot.quit()
}
bot.on('kicked', reason => shutdown(JSON.stringify(reason)))
bot.on('error', error => shutdown(error.message))
bot.on('end', () => { stopped = true; invalidate(); clearInterval(watchdog); terminal.close() })
process.on('SIGINT', () => shutdown('Stopped by user'))
process.on('SIGTERM', () => shutdown('Stopped by user'))
