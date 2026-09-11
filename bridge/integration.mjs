// Actual Mineflayer client -> actual local Flying Squid server -> packet assertions.
// Requires Python neural HTTP service via NEURAL_URL. No Mojang server or account.
import { createRequire } from 'node:module'
import { spawn } from 'node:child_process'
import { once } from 'node:events'
import assert from 'node:assert/strict'
const require = createRequire(import.meta.url)
const { createMCServer } = require('flying-squid')
const { Vec3 } = require('vec3')
const settings = require('flying-squid/config/default-settings.json')
const scenario = process.env.SCENARIO || 'wall'
const server = createMCServer({ ...settings, host: '127.0.0.1', port: 0,
  version: '1.16.5', 'online-mode': false, logging: false, gameMode: 1,
  worldFolder: undefined, 'view-distance': 2, 'max-entities': 32,
  generation: { name: 'superflat', options: { seed: 7 } } })
let child, target, first, maxDistance = 0, minYaw = Infinity, maxYaw = -Infinity, packets = 0
let minY=Infinity, maxY=-Infinity, lastPosition=null, lastMotionAt=Date.now()
let output = ''
const deadline = setTimeout(() => { console.error('Integration timeout', output); child?.kill(); process.exit(1) }, 25000)
try {
  await once(server, 'listening')
  server.getSpawnPoint = async () => new Vec3(0.5, 5, 0.5)
  // Wall to one side of the initial heading (+Z), leaving the forward path clear.
  if (scenario === 'wall') for (let z=-2;z<=6;z++) for (const y of [5,6]) {
    await server.setBlock(server.overworld, new Vec3(2,y,z), server.registry.blocksByName.stone.minStateId)
  }
  if (scenario === 'step') for (let x=-4;x<=4;x++) for (let z=2;z<=5;z++) {
    await server.setBlock(server.overworld, new Vec3(x,5,z), server.registry.blocksByName.stone.minStateId)
  }
  if (scenario === 'drop') for (let x=-5;x<=5;x++) for (let z=2;z<=6;z++) for (let y=0;y<=4;y++) {
    await server.setBlock(server.overworld, new Vec3(x,y,z),0)
  }
  server.on('newPlayer', player => {
    if (player._client.username !== 'FlyConnectome') return
    const capture = packet => {
      packets++
      if (Number.isFinite(packet.x)) {
        first ||= { x:packet.x, z:packet.z }
        maxDistance = Math.max(maxDistance, Math.hypot(packet.x-first.x, packet.z-first.z))
        minY=Math.min(minY,packet.y); maxY=Math.max(maxY,packet.y)
        if (!lastPosition || Math.hypot(packet.x-lastPosition.x,packet.z-lastPosition.z)>0.01) lastMotionAt=Date.now()
        lastPosition=packet
      }
      if (Number.isFinite(packet.yaw)) {
        minYaw = Math.min(minYaw, packet.yaw); maxYaw = Math.max(maxYaw, packet.yaw)
      }
    }
    for (const event of ['position','position_look','look']) player._client.on(event,capture)
  })
  child = spawn(process.execPath, ['index.mjs'], { cwd: new URL('.',import.meta.url),
    env:{...process.env, MC_HOST:'127.0.0.1',MC_PORT:String(server.listeningPort),MC_VERSION:'1.16.5',MC_AUTH:'offline'} })
  child.stdout.on('data', data => { output += data })
  child.stderr.on('data', data => { output += data })
  if (scenario === 'follow') {
    await new Promise(resolve => {
      const interval=setInterval(()=>{ if(first){clearInterval(interval);resolve()} },50)
    })
    server.getSpawnPoint=async()=>new Vec3(0.5,5,8.5)
    target=require('mineflayer').createBot({host:'127.0.0.1',port:server.listeningPort,username:'TargetProbe',auth:'offline',version:'1.16.5'})
    await once(target,'spawn')
    child.stdin.write('follow TargetProbe\n')
  }
  const started=Date.now()
  await new Promise((resolve,reject) => {
    const interval = setInterval(() => {
      const passed = scenario === 'wall' ? maxDistance>1 && maxYaw-minYaw>10
        : scenario === 'step' ? maxY>=6 && lastPosition?.z>2.5
        : scenario === 'drop' ? Date.now()-started>4000 && maxDistance>0.2 && minY>=4.99 && output.includes('drop')
        : scenario === 'follow' ? lastPosition && Math.hypot(lastPosition.x-0.5,lastPosition.z-8.5)<3 && Date.now()-lastMotionAt>750
        : false
      if (passed) { clearInterval(interval); resolve() }
    }, 100)
    child.once('exit', code => { clearInterval(interval); reject(new Error(`bot exited ${code}: ${output}`)) })
  })
  assert.ok(packets > 5)
  console.log(JSON.stringify({ test:'minecraft-network-integration', server:'flying-squid 1.12.0',
    protocol:'1.16.5', scenario, packets, distance_blocks:maxDistance, yaw_span_degrees:maxYaw-minYaw, minY,maxY }))
} catch (error) {
  console.error(error,output); process.exitCode=1
} finally {
  clearTimeout(deadline)
  target?.quit()
  if (child && child.exitCode === null && child.signalCode === null) {
    const exited = once(child,'exit'); child.kill('SIGTERM'); await exited.catch(()=>{})
  }
  await server.quit()
  // Flying Squid background world timers may remain after quit.
  process.exit(process.exitCode || 0)
}
