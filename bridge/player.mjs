// Engineering assistance around the connectome. No learning or anatomical claims.
import { clamp, direction, observe } from './control.mjs'

const dangerous = new Set(['lava', 'water', 'fire', 'soul_fire', 'cactus', 'magma_block',
  'campfire', 'soul_campfire', 'sweet_berry_bush', 'powder_snow'])
const solid = b => b?.boundingBox === 'block'
const clear = b => b != null && !solid(b) && !dangerous.has(b.name)
const wrap = angle => Math.atan2(Math.sin(angle), Math.cos(angle))

export function terrain(bot) {
  const p = bot.entity.position
  const d = direction(bot.entity.yaw)
  const footY = Math.floor(p.y + 0.01)
  const at = (distance, side, y) => bot.blockAt(p.offset(
    d.x * distance + d.z * side, y - p.y, d.z * distance - d.x * side))
  let hazard = null, lowerBlocked = false, upperBlocked = false, jumpClear = true
  // Sample the player's width, rather than a single center ray.
  for (const side of [-0.3, 0, 0.3]) {
    const lower = at(0.85, side, footY + 0.1)
    const upper = at(0.85, side, footY + 1.1)
    const floor = at(0.85, side, footY - 0.1)
    const below = at(0.85, side, footY - 1.1)
    const overhead = at(0.85, side, footY + 2.1)
    const ownOverhead = at(0, side, footY + 2.1)
    if ([lower, upper, floor, below, overhead, ownOverhead].some(b => b == null)) hazard = 'unloaded'
    if ([lower, upper, floor, below].some(b => dangerous.has(b?.name))) hazard = 'dangerous-block'
    if (!solid(lower) && !solid(floor) && !solid(below)) hazard ||= 'drop'
    lowerBlocked ||= solid(lower)
    upperBlocked ||= solid(upper)
    jumpClear &&= clear(upper) && clear(overhead) && clear(ownOverhead)
  }
  const groundHazard = dangerous.has(bot.blockAt(p.offset(0, -0.1, 0))?.name)
  if (groundHazard) hazard = 'dangerous-ground'
  return { hazard, lowerBlocked, upperBlocked,
    canJump: !hazard && lowerBlocked && !upperBlocked && jumpClear && bot.entity.onGround === true }
}

export class Player {
  constructor() { this.mode = 'roam'; this.target = null; this.resetMotion() }
  resetMotion() {
    this.anchor = null; this.since = null; this.recoverUntil = 0; this.recoverSign = 1
    this.lastJump = -Infinity; this.lastCommandForward = false; this.lastStatus = null
  }
  command(line) {
    const [cmd, name, ...extra] = line.trim().split(/\s+/)
    if (cmd === 'status') return { changed: false, status: this.lastStatus, mode: this.mode, target: this.target }
    if (cmd === 'help') return { changed: false, help: 'roam | follow <exact player name> | stop | status | quit' }
    if (extra.length || (name && cmd !== 'follow') || !['roam', 'follow', 'stop'].includes(cmd)) {
      throw new Error('Commands: roam | follow <name> | stop | status | quit')
    }
    if (cmd === 'follow' && !/^[A-Za-z0-9_]{1,16}$/.test(name || '')) throw new Error('Use the exact Minecraft player name')
    this.mode = cmd === 'stop' ? 'idle' : cmd
    this.target = cmd === 'follow' ? name : null
    this.resetMotion()
    return { changed: true, mode: this.mode, target: this.target }
  }
  sense(bot) {
    const observation = observe(bot)
    const ground = terrain(bot)
    let hold = this.mode === 'idle' ? 'idle' : null, distance = null, error = 0
    const neural = { ...observation.neural }
    // Suppress a traversable step's obstacle response so it can approach and jump.
    if (ground.canJump) { neural.obstacle_left = 0; neural.obstacle_right = 0 }
    if (this.mode === 'follow') {
      const entity = bot.players?.[this.target]?.entity
      if (!entity || entity === bot.entity) hold = 'target-unavailable'
      else {
        const dx = entity.position.x - bot.entity.position.x
        const dz = entity.position.z - bot.entity.position.z
        distance = Math.hypot(dx, dz)
        error = wrap(Math.atan2(-dx, -dz) - bot.entity.yaw)
        if (distance <= 2.5) hold = 'near-target'
        else if (distance > 24) hold = 'target-too-far'
        else if (Math.abs(entity.position.y - bot.entity.position.y) > 3) hold = 'target-height'
        else {
          // Goal bias travels through input neurons, not directly into yaw.
          const turn = Math.min(1, Math.abs(error) / (Math.PI / 2))
          if (error > 0.08) neural.obstacle_right = Math.max(neural.obstacle_right, turn)
          if (error < -0.08) neural.obstacle_left = Math.max(neural.obstacle_left, turn)
        }
      }
    }
    if (hold) neural.drive = 0
    if (ground.hazard || ground.upperBlocked) neural.drive = 0
    return { ...observation, neural, ground, hold, distance, error }
  }
  decide(bot, action, sense, now = performance.now()) {
    const p = bot.entity.position
    const { ground, hold } = sense
    if (hold) {
      this.resetMotion()
      return this.record({ forward: false, jump: false, yawRate: 0, reason: hold }, sense)
    }
    let reason = 'neural', yawRate = action.yaw_rate
    let forward = action.forward && (!sense.blocked || ground.canJump)
    if (ground.hazard || ground.upperBlocked) { forward = false; reason = ground.hazard || 'wall' }
    if (this.mode === 'follow' && Math.abs(sense.error) > Math.PI / 3) { forward = false; reason = 'face-target' }
    if (!this.anchor || Math.hypot(p.x - this.anchor.x, p.z - this.anchor.z) > 0.25) {
      this.anchor = { x: p.x, z: p.z }; this.since = now
    }
    // Recover only while grounded and trying to travel, or stopped at an obstacle.
    const wantsTravel = action.forward || ground.hazard || ground.upperBlocked || sense.blocked
    if (bot.entity.onGround && wantsTravel && reason !== 'face-target' && now - this.since > 1500 && now >= this.recoverUntil) {
      this.recoverUntil = now + 1100
      this.recoverSign = sense.neural.obstacle_left > sense.neural.obstacle_right ? -1 : 1
      this.since = now
    }
    if (now < this.recoverUntil) { forward = false; yawRate = this.recoverSign * 1.2; reason = 'recovery-turn' }
    // Cooldown makes jump a pulse rather than permanently holding jump.
    const jump = forward && ground.canJump && now - this.lastJump >= 700
    if (jump) { this.lastJump = now; reason = 'step-jump' }
    this.lastCommandForward = forward
    return this.record({ forward, jump, yawRate, reason }, sense)
  }
  record(result, sense) {
    this.lastStatus = { mode: this.mode, target: this.target, distance: sense.distance,
      hazard: sense.ground.hazard, ...result }
    return result
  }
}

export async function actuate(bot, command) {
  bot.setControlState('forward', command.forward)
  bot.setControlState('jump', command.jump)
  await bot.look(bot.entity.yaw + clamp(command.yawRate, -1.5, 1.5) * 0.05, 0, true)
}
