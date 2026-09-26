const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const fs=require('fs'),path=require('path'),assert=require('assert');
const root=path.resolve(__dirname,'..'),findings=[],errors=[];
fs.mkdirSync(path.join(root,'test-results'),{recursive:true});
(async()=>{
const browser=await chromium.launch({headless:true,...(process.env.BROWSER_CHANNEL?{channel:process.env.BROWSER_CHANNEL}:{})});
const travelContext=await browser.newContext({viewport:{width:1440,height:1000}});travelContext.on('page',p=>p.on('pageerror',e=>errors.push(e.message)));
try{
 const travel=await travelContext.newPage();await travel.goto(process.env.TRAVEL_URL||'http://127.0.0.1:8791');await travel.locator('#mode-note').waitFor();await travel.locator('#submit').click();await travel.locator('#structured-editor .activity-edit').first().waitFor();assert(await travel.locator('#source-badge').innerText()==='手动规划');
 await travel.locator('.activity-edit').first().getByLabel(/地点与活动/).fill('西湖散步（已人工确认）');await travel.getByRole('button',{name:'保存行程修改',exact:true}).click();await travel.waitForFunction(()=>document.querySelector('#status').textContent.includes('修改已保存'));assert((await travel.locator('#result').innerText()).includes('西湖散步'));assert(!(await travel.locator('#raw').innerText()).includes('西湖散步'));
 const [md]=await Promise.all([travel.waitForEvent('download'),travel.locator('#download').click()]);const mdPath=path.join(root,'test-results/edited.md');await md.saveAs(mdPath);assert(fs.readFileSync(mdPath,'utf8').includes('西湖散步'));findings.push('行旅创建、编辑、保存、下载内容一致，保留原始文本');
 await travel.reload();await travel.locator('.history-open').first().click();await travel.waitForFunction(()=>document.querySelector('#result').textContent.includes('西湖散步'));await travel.locator('#history-search').fill('不存在的城市xyz');await travel.waitForTimeout(400);await travel.waitForFunction(()=>document.querySelectorAll('.history-open').length===0);await travel.locator('#history-search').fill('杭州');await travel.locator('.history-open').first().waitFor();
 await travel.locator('#account-button').click();await travel.locator('#login-form [name=username]').fill('traveler_'+Date.now());await travel.locator('#login-form [name=password]').fill('ExampleTravel1234');await travel.locator('#register-button').click();await travel.locator('#memory-form').waitFor({state:'visible'});await travel.locator('#memory-content').fill('喜欢历史建筑和轻松步行');await travel.locator('#save-memory').click();await travel.waitForFunction(()=>document.querySelector('#account-message').textContent.includes('已保存'));await travel.locator('#close-account').click();await travel.locator('.history-open').first().click();findings.push('行旅历史搜索、账号注册、游客历史归属和偏好保存成功');
 fs.mkdirSync(path.join(root,'test-results/screenshots'),{recursive:true});await travel.screenshot({path:path.join(root,'test-results/screenshots/travel-desktop.png'),fullPage:true});await travel.setViewportSize({width:390,height:844});assert(await travel.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await travel.screenshot({path:path.join(root,'test-results/screenshots/travel-mobile.png'),fullPage:true});await travel.locator('#account-button').click();await travel.locator('#logout-button').click();await travel.locator('#structured-editor').waitFor({state:'hidden'});findings.push('行旅手机布局及退出账号后隐私清理通过');

assert.deepStrictEqual(errors,[]);console.log(JSON.stringify({passed:true,findings,browserErrors:errors},null,2));
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
