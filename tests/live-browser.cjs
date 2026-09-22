// Opt-in: invokes the configured model once and verifies the real streaming UI.
const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,...(process.env.BROWSER_PATH?{executablePath:process.env.BROWSER_PATH}:{})});
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(process.env.TRAVEL_URL||'http://127.0.0.1:8010/');
 await page.locator('[name=destination]').fill('广州');
 await page.locator('[name=preferences]').fill('陈家祠、广东省博物馆、沙面；轻松出行，参考知识库');
 const today=new Date(),end=new Date();end.setDate(today.getDate()+1);
 const day=d=>d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');
 await page.locator('[name=start]').fill(day(today));await page.locator('[name=end]').fill(day(end));
 const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/travel/stream'),{timeout:180000});
 await page.evaluate(()=>{const nativeFetch=window.fetch;window.fetch=async(...args)=>{const response=await nativeFetch(...args);if(String(args[0]).endsWith('/api/travel/stream'))window.travelTestBody=response.clone().text();return response;};});
 await page.locator('#submit').click();const response=await responsePromise;
 assert.equal(response.status(),200);assert(response.headers()['content-type'].includes('text/event-stream'));
 await page.waitForFunction(()=>document.querySelector('#panel').getAttribute('aria-busy')==='false',{},{timeout:200000});
 const body=await page.evaluate(()=>window.travelTestBody);
 const events=body.split('\n').filter(s=>s.startsWith('data: ')).map(s=>JSON.parse(s.slice(6)));
 const completion=events.find(e=>e.event==='complete');
 assert(completion,'Stream did not complete');assert.equal(completion.result.source,'dify');
 const deltas=events.filter(e=>e.event==='delta');assert(deltas.length>1);
 assert(!deltas.map(e=>e.text).join('').includes('<think>'));
 await page.locator('#result table').first().waitFor();
 fs.mkdirSync('test-results',{recursive:true});
 const report={status:response.status(),source:completion.result.source,deltas:deltas.length,answerLength:completion.result.answer?.length,sourceCount:completion.result.sources?.length,tableCount:await page.locator('#result table').count()};
 fs.writeFileSync('test-results/live-browser.json',JSON.stringify(report,null,2));
 await page.screenshot({path:'test-results/live-desktop.png',fullPage:true});
 await page.reload();await page.locator('.history-open').first().click();await page.locator('#result table').first().waitFor();
 await page.setViewportSize({width:390,height:844});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
 await page.screenshot({path:'test-results/live-mobile.png',fullPage:true});
 assert.deepEqual(errors,[]);
 const cleanup=await page.request.delete(new URL('/api/history/'+completion.result.plan_id,page.url()).href);
 assert.equal(cleanup.status(),200);
 console.log(JSON.stringify(report));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
