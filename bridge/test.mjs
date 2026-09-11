import test from 'node:test'
import assert from 'node:assert/strict'
import { direction, observe, validAction, applyAction, Lease } from './control.mjs'

test('yaw sign and neural turn command agree', async () => {
  assert.ok(direction(Math.PI / 2).x < -0.99)
  const calls = []
  const bot = { entity: { yaw: 0 }, setControlState: (...x) => calls.push(x), look: (...x) => calls.push(x) }
  await applyAction(bot, { forward: true, yaw_rate: 1 }, false)
  assert.deepEqual(calls[0], ['forward', true]); assert.equal(calls[1][0], 0.05)
  await applyAction(bot, { forward: true, yaw_rate: 1 }, true)
  assert.deepEqual(calls[2], ['forward', false])
})
test('sensor detects left wall and unloaded terrain', () => {
  const bot = { entity: { yaw: 0, position: { offset: (x,y,z) => ({ x,y,z }) } },
    blockAt: p => ({ boundingBox: p.x < -0.3 ? 'block' : 'empty' }) }
  const obs = observe(bot)
  assert.ok(obs.neural.obstacle_left > obs.neural.obstacle_right)
  bot.blockAt = () => null
  assert.equal(observe(bot).blocked, true)
})
test('invalid / stale actions rejected and lease expires', () => {
  const action = { protocol: 1, session: 's', seq: 2, forward: true, yaw_rate: 0 }
  assert.ok(validAction(action, 's', 2))
  for (const patch of [{ seq: 1 }, { session: 'old' }, { yaw_rate: NaN }, { yaw_rate: 5 }, { forward: 1 }]) {
    assert.ok(!validAction({ ...action, ...patch }, 's', 2))
  }
  let stops = 0
  const lease = new Lease(() => stops++)
  lease.renew(100); lease.check(449); assert.equal(stops, 0)
  lease.check(451); assert.equal(stops, 1)
})
