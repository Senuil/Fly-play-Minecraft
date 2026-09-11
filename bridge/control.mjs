export const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x))

export function direction(yaw) {
  // Mineflayer: yaw=0 faces -Z; positive yaw turns left toward -X.
  return { x: -Math.sin(yaw), z: -Math.cos(yaw) }
}

export function observe(bot) {
  const origin = bot.entity.position
  const proximity = offset => {
    const d = direction(bot.entity.yaw + offset)
    for (let distance = 0.5; distance <= 4; distance += 0.5) {
      for (const height of [0.1, 1.1]) {
        const block = bot.blockAt(origin.offset(d.x * distance, height, d.z * distance))
        // Unloaded chunks count as blocked.
        if (!block || block.boundingBox === 'block') return 1 - (distance - 0.5) / 4
      }
    }
    return 0
  }
  const front = proximity(0)
  return {
    neural: { drive: 1, obstacle_left: proximity(Math.PI / 4), obstacle_right: proximity(-Math.PI / 4) },
    blocked: front > 0.75
  }
}

export function validAction(a, session, seq) {
  return a && a.protocol === 1 && a.session === session && a.seq === seq &&
    typeof a.forward === 'boolean' && Number.isFinite(a.yaw_rate) && Math.abs(a.yaw_rate) <= 1.5
}

export function applyAction(bot, action, blocked, dt = 0.05) {
  bot.setControlState('forward', action.forward && !blocked)
  // Safety clamp is separate from neural decoding; no pathfinder or hidden policy.
  return bot.look(bot.entity.yaw + action.yaw_rate * clamp(dt, 0, 0.1), 0, true)
}

export class Lease {
  constructor(stop, maxAge = 350) { this.stop = stop; this.maxAge = maxAge; this.last = -Infinity }
  renew(now = performance.now()) { this.last = now }
  check(now = performance.now()) { if (now - this.last > this.maxAge) this.stop() }
}
