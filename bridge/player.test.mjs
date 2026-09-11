import test from 'node:test'
import assert from 'node:assert/strict'
import { terrain, Player } from './player.mjs'

function world(extra = () => null) {
  const p = { x: 0.5, y: 5, z: 0.5, offset(x,y,z) { return { x:this.x+x,y:this.y+y,z:this.z+z } } }
  return { entity: { position:p, yaw:0, onGround:true }, players:{}, blockAt: p => {
    const [x,y,z] = [Math.floor(p.x),Math.floor(p.y),Math.floor(p.z)]
    return extra(x,y,z) || (y <= 4 ? {name:'stone',boundingBox:'block'} : {name:'air',boundingBox:'empty'})
  } }
}
const block = { name:'stone', boundingBox:'block' }, air = {name:'air',boundingBox:'empty'}
const action = {forward:true,yaw_rate:0}

test('flat ground walks, full step jumps, high wall and low ceiling cannot jump', () => {
  const flat = world(), player = new Player()
  assert.equal(terrain(flat).hazard,null)
  assert.equal(player.decide(flat,action,player.sense(flat),0).forward,true)
  const step = world((x,y,z) => z === -1 && y === 5 ? block:null)
  const s = player.sense(step)
  assert.equal(s.ground.canJump,true)
  const c = player.decide(step,action,s,100)
  assert.equal(c.jump,true); assert.equal(c.reason,'step-jump')
  assert.equal(player.decide(step,action,s,150).jump,false)
  for (const ceiling of [6,7]) {
    const wall = world((x,y,z) => z === -1 && [5,ceiling].includes(y) ? block:null)
    assert.equal(terrain(wall).canJump,false)
    assert.equal(player.decide(wall,action,player.sense(wall),200).forward,false)
  }
})
test('drop, hazardous landing surface and unloaded chunks stop forward and jump', () => {
  const cases = [
    world((x,y,z) => z === -1 && y <= 4 ? air:null),
    world((x,y,z) => z === -1 && y === 4 ? {name:'lava',boundingBox:'empty'}:null),
    world((x,y,z) => z === -1 && y === 4 ? {name:'magma_block',boundingBox:'block'}:null)
  ]
  const missing = world(); missing.blockAt = () => null; cases.push(missing)
  for (const bot of cases) {
    const p = new Player(), s=p.sense(bot), c=p.decide(bot,action,s,0)
    assert.ok(s.ground.hazard); assert.equal(c.forward,false); assert.equal(c.jump,false)
  }
})
test('stuck recovery rotates in place, ends, and is reset by stop', () => {
  const bot=world(), p=new Player(), s=p.sense(bot)
  p.decide(bot,action,s,0)
  const recovery=p.decide(bot,action,s,1600)
  assert.equal(recovery.reason,'recovery-turn'); assert.equal(recovery.forward,false)
  assert.notEqual(recovery.yawRate,0)
  assert.equal(p.decide(bot,action,s,2750).forward,true)
  p.command('stop')
  const stopped=p.decide(bot,action,p.sense(bot),3000)
  assert.equal(stopped.forward,false); assert.equal(stopped.yawRate,0)
})
test('follow biases neural inputs, holds near/missing/far target and rejects malformed commands', () => {
  const bot=world(), p=new Player()
  p.command('follow Senuil')
  assert.equal(p.sense(bot).hold,'target-unavailable')
  bot.players.Senuil={entity:{position:{x:-5,y:5,z:0.5}}}
  const s=p.sense(bot)
  assert.ok(s.neural.obstacle_right > 0.9)
  assert.equal(p.decide(bot,{forward:true,yaw_rate:0.5},s,0).forward,false)
  bot.players.Senuil.entity.position={x:0.5,y:5,z:-1}
  assert.equal(p.sense(bot).hold,'near-target')
  bot.players.Senuil.entity.position.z=-30
  assert.equal(p.sense(bot).hold,'target-too-far')
  for (const c of ['follow','follow x y','stop now','attack Senuil']) assert.throws(()=>p.command(c))
  p.command('roam'); assert.equal(p.sense(bot).hold,null)
})
test('head-on wall can recover even when neural forward has been suppressed', () => {
  const bot=world((x,y,z)=>z===-1 && (y===5 || y===6)?block:null), p=new Player()
  const s=p.sense(bot)
  p.decide(bot,{forward:false,yaw_rate:0},s,0)
  assert.equal(p.decide(bot,{forward:false,yaw_rate:0},s,1600).reason,'recovery-turn')
})
