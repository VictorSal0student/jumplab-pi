// Development-only: npm install --no-save playwright && npx playwright install chromium
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const fs=require('node:fs');
(async()=>{
const browser=await chromium.launch({headless:true,executablePath:process.env.JUMPLAB_CHROMIUM||undefined,args:['--no-sandbox']});
const page=await browser.newPage({viewport:{width:1440,height:1100}});
const errors=[];page.on('pageerror',e=>errors.push(e.message));
const base=process.env.JUMPLAB_URL||'http://127.0.0.1:8765';
const out=path.resolve(__dirname,'../docs/screenshots');fs.mkdirSync(out,{recursive:true});
await page.goto(base);await page.waitForFunction(()=>!document.querySelector('#demo').disabled);
await page.screenshot({path:path.join(out,'01-empty-workspace.png'),fullPage:true});
await page.click('#cameraCheck');await page.waitForFunction(()=>document.querySelector('#cameraStatus').textContent.includes('import mode'));
await page.click('#demo');await page.waitForFunction(()=>document.querySelector('#frameIndex').textContent.startsWith('Frame 0 /'),{timeout:30000});
await page.click('#next');await page.waitForFunction(()=>document.querySelector('#frameIndex').textContent.startsWith('Frame 1 /'));
assert.match(await page.textContent('#frameTime'),/0.0333 s/);
await page.click('#prev');await page.waitForFunction(()=>document.querySelector('#frameIndex').textContent.startsWith('Frame 0 /'));
async function frame(n){await page.locator('#timeline').evaluate((el,n)=>{el.value=n;el.dispatchEvent(new Event('input'));},n);await page.waitForFunction(n=>document.querySelector('#frameIndex').textContent.startsWith(`Frame ${n} /`),n);}
await frame(29);await page.click('#takeoff');await page.waitForFunction(()=>document.querySelector('#takeoffInfo').textContent.includes('Frame 29'));
assert.equal(await page.textContent('#height'),'—');
await frame(45);await page.click('#landing');await page.waitForFunction(()=>document.querySelector('#height').textContent==='30.6');
assert.equal(await page.textContent('#flight'),'500.0 ms');
await page.click('#review');await page.waitForFunction(()=>document.querySelector('#message').textContent.includes('Confirm adjacent-frame'));
await page.check('#contactChecked');await page.check('#timingChecked');await page.fill('#notes','Synthetic workflow check — no hardware validation.');await page.click('#review');
await page.waitForFunction(()=>document.querySelector('#state').textContent==='Reviewed');
assert.equal(await page.locator('#message').evaluate(e=>e.classList.contains('error')),false);
await page.screenshot({path:path.join(out,'02-reviewed-demo-desktop.png'),fullPage:true});
const exportPromise=page.waitForEvent('download');await page.click('#export');const download=await exportPromise;const exported=path.join(out,'test-trial.zip');await download.saveAs(exported);
const initialId=await page.locator('#export').getAttribute('href');
await page.setInputFiles('#file',exported);await page.waitForFunction(id=>document.querySelector('#export').getAttribute('href')!==id,initialId,{timeout:30000});
await page.waitForFunction(()=>!document.querySelector('#landing').disabled);
assert.equal(await page.textContent('#state'),'Reviewed');assert.equal(await page.textContent('#flight'),'500.0 ms');
// An annotation change invalidates review, and incomplete/invalid order yields unavailable.
await frame(47);await page.click('#takeoff');await page.waitForFunction(()=>document.querySelector('#state').textContent==='Unreviewed');assert.equal(await page.textContent('#height'),'—');
await frame(29);await page.click('#takeoff');await page.waitForFunction(()=>document.querySelector('#height').textContent==='30.6');
// Rapid slider requests cannot make the label point at a different loaded image.
await page.route('**/frames/10',async route=>{await new Promise(r=>setTimeout(r,250));await route.continue();});
await page.locator('#timeline').evaluate(el=>{el.value=10;el.dispatchEvent(new Event('input'));el.value=11;el.dispatchEvent(new Event('input'));});
await page.waitForFunction(()=>document.querySelector('#frameIndex').textContent.startsWith('Frame 11 /'));
assert.match(await page.locator('#frame').getAttribute('src'),/\/frames\/11$/);
// Failed import retains the current workspace and reports failure.
await page.setInputFiles('#file',{name:'broken.mp4',mimeType:'video/mp4',buffer:Buffer.from('not a video')});
await page.waitForFunction(()=>document.querySelector('#message').classList.contains('error'),{timeout:30000});
assert.equal(await page.textContent('#flight'),'500.0 ms');
await frame(45);
// Repeat resize cycles and verify bounded viewer with no horizontal page overflow.
for(const width of [390,1280,390,1440,390]){await page.setViewportSize({width,height:900});const dims=await page.evaluate(()=>({height:document.querySelector('#stage').getBoundingClientRect().height,scroll:document.documentElement.scrollWidth,width:innerWidth}));assert(dims.height<=350);assert(dims.scroll<=dims.width,JSON.stringify(dims));}
await page.screenshot({path:path.join(out,'03-mobile-layout.png'),fullPage:true});
await page.setViewportSize({width:1440,height:1100});
await page.check('#contactChecked');await page.check('#timingChecked');await page.click('#review');await page.waitForFunction(()=>document.querySelector('#state').textContent==='Reviewed');
await page.locator('summary').click();await page.screenshot({path:path.join(out,'04-timing-diagnostics.png'),fullPage:true});
assert.deepEqual(errors,[]);fs.unlinkSync(exported);
console.log('PASS: desktop/mobile, no-camera mode, frame stepping, timestamps, event selection, review gate, calculation, ZIP export/reopen, invalid order, async frame race, failed import, repeated resize; no browser exceptions.');
await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
