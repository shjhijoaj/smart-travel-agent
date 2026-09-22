// Run against the local app. UI responses are fixtures; real API integration is separate.
const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
const path=require('node:path');
(async()=>{
const browser=await chromium.launch({headless:true,...(process.env.BROWSER_PATH?{executablePath:process.env.BROWSER_PATH}:{})});
try{
const context=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:true});
const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
const answer='## 行程概览\n- 西湖漫步与老城美食，给旅途留一点空白。\n## 每日行程\n### 第1天 · 2026-10-03 · 抵达与西湖\n| 时间 | 地点与活动 | 交通 | 预计费用 | 提醒 |\n|---|---|---|---|---|\n| 下午 | 西湖湖滨散步 | 公交，线路待确认 | 待确认 | 预留休息 |\n| 晚上 | 湖滨用餐 | 步行距离待确认 | 待确认 | 避开排队高峰 |\n### 第2天 · 2026-10-04 · 文化体验\n| 时间 | 地点与活动 | 交通 | 预计费用 | 提醒 |\n|---|---|---|---|---|\n| 上午 | 博物馆参观 | 公交 | 待确认 | 提前预约 |\n## 预算估算\n| 项目 | 所有人合计费用 |\n|---|---|\n| 交通与住宿 | 待确认 |\n| 合计 | 待确认 |\n## 下雨备选方案\n- 户外散步 → 室内展馆，开放情况待确认。\n## 注意事项\n- 确认返程车次。\n- <img src=x onerror=alert(1)>\n';
let records=[],requests=[],fail=false;
function streamBody(record){return [{event:'status',message:'正在生成'},{event:'delta',text:answer},{event:'complete',result:{...record.result,plan_id:record.id}}].map(e=>'event: '+e.event+'\ndata: '+JSON.stringify(e)+'\n\n').join('');}
await page.route(/\/api\/history(?:\/.*)?(?:\?.*)?$/,async route=>{const req=route.request(),url=new URL(req.url()),parts=url.pathname.split('/');if(req.method()==='GET'){return route.fulfill({json:parts.length===3?{items:records}:records.find(x=>x.id===parts[3])});}if(req.method()==='DELETE'){records=records.filter(x=>x.id!==parts[3]);return route.fulfill({json:{deleted:true}});}const input=req.postDataJSON();requests.push(input);const record={id:'plan-'+(records.length+1),request:input,parent_id:parts[3],result:{answer,source:'dify'}};records.unshift(record);await route.fulfill({contentType:'text/event-stream',body:streamBody(record)});});
await page.route('**/api/travel/stream',async route=>{requests.push(route.request().postDataJSON());if(fail)return route.fulfill({status:504,json:{detail:'生成方案超时，请稍后重试'}});const record={id:'plan-1',request:route.request().postDataJSON(),result:{source:'dify',answer}};records.unshift(record);await route.fulfill({contentType:'text/event-stream',body:streamBody(record)});});
await page.goto(process.env.TRAVEL_URL||'http://127.0.0.1:8010/');await page.locator('#submit').click();await page.locator('#result table').first().waitFor();
assert.equal(await page.locator('#result table').count(),3);assert.equal(await page.locator('#result img').count(),0);assert.equal(await page.locator('#history-list .history-open').count(),1);
assert.equal(await page.evaluate(()=>planText({answer:'<think>secret reasoning</think>最终方案'})),'最终方案');
await page.locator('#checks input').first().check();
const mdPromise=page.waitForEvent('download');await page.locator('#download').click();const md=await mdPromise;assert(md.suggestedFilename().endsWith('.md'));
const icsPromise=page.waitForEvent('download');await page.locator('#calendar').click();const ics=await icsPromise;const icsText=fs.readFileSync(await ics.path(),'utf8');assert(icsText.includes('BEGIN:VCALENDAR'));assert(icsText.includes('DTEND;VALUE=DATE:'));
await page.locator('#edit').click();await page.locator('[name=budget]').fill('2500');await page.locator('#submit').click();await page.waitForFunction(()=>document.querySelectorAll('.history-open').length===2);assert.equal(records[0].parent_id,'plan-1');assert.equal(requests.at(-1).budget,'2500');
await page.reload();await page.locator('.history-open').last().click();assert(await page.locator('#checks input').first().isChecked());
fs.mkdirSync('test-results',{recursive:true});await page.screenshot({path:'test-results/desktop.png',fullPage:true});
await page.setViewportSize({width:390,height:844});await page.screenshot({path:'test-results/mobile.png',fullPage:true});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
page.on('dialog',dialog=>dialog.accept());await page.locator('.history-delete').first().click();await page.waitForFunction(()=>document.querySelectorAll('.history-open').length===1);
await page.locator('#new').click();fail=true;await page.locator('#submit').click();await page.waitForFunction(()=>document.querySelector('#status').classList.contains('error'));assert(await page.locator('#submit').isEnabled());assert(await page.locator('#result table').count()>0);
assert.deepEqual(errors,[]);console.log('UI PASS: render, history, revision, checklist, downloads, deletion, mobile overflow, safe text, error recovery');
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
