// Uses real account/history APIs, only model/weather fixture calls are intercepted.
const {chromium}=require('playwright');const assert=require('node:assert/strict');const crypto=require('node:crypto');
(async()=>{const browser=await chromium.launch({headless:true,...(process.env.BROWSER_PATH?{executablePath:process.env.BROWSER_PATH}:{})});try{
const page=await browser.newPage({viewport:{width:1280,height:900}});const errors=[];page.on('pageerror',e=>errors.push(e.message));
await page.goto(process.env.TRAVEL_URL||'http://127.0.0.1:8010/');await page.locator('#account-button').click();
const user='ui_'+crypto.randomBytes(5).toString('hex'),password=crypto.randomBytes(20).toString('hex');
await page.locator('#login-form [name=username]').fill(user);await page.locator('#login-form [name=password]').fill(password);await page.locator('#register-button').click();await page.locator('#memory-form').waitFor({state:'visible'});
await page.locator('#memory-content').fill('喜欢茶文化，不吃辣');await page.locator('#save-memory').click();await page.waitForFunction(()=>document.querySelector('#account-message').textContent.includes('已保存'));
await page.locator('#logout-button').click();await page.locator('#account-button').click();await page.locator('#login-form [name=username]').fill(user);await page.locator('#login-form [name=password]').fill(password);await page.locator('#login-button').click();await page.waitForFunction(()=>document.querySelector('#memory-content').value==='喜欢茶文化，不吃辣');
await page.locator('#clear-memory').click();await page.waitForFunction(()=>document.querySelector('#memory-content').value==='');await page.locator('#close-account').click();
await page.locator('#account-button').click();await page.locator('#memory-form summary').click();
const changedPassword=crypto.randomBytes(20).toString('hex');await page.locator('[name=old_password]').fill(password);await page.locator('[name=new_password]').fill(changedPassword);await page.locator('#password-form button').click();await page.waitForFunction(()=>document.querySelector('#account-message').textContent.includes('密码已更新'));
await page.locator('#logout-button').click();await page.locator('#account-button').click();await page.locator('#login-form [name=username]').fill(user);await page.locator('#login-form [name=password]').fill(changedPassword);await page.locator('#login-button').click();await page.locator('#memory-form').waitFor({state:'visible'});await page.locator('#close-account').click();
let queries=0;await page.route('**/api/travel/weather',route=>{queries++;return route.fulfill({json:queries===1?{status:'ambiguous',candidates:[{id:1808926,name:'杭州',region:'浙江',country:'中国'}]}:{status:'ok',message:'仅覆盖当前预报日期',fetched_at:new Date().toISOString(),location:{name:'杭州'},days:[{date:'2026-09-22',low_c:23,high_c:31,rain_percent:10}]}});});
await page.locator('#weather-check').click();await page.locator('#weather-location').selectOption('1808926');await page.locator('#weather-check').click();await page.locator('#weather-data').waitFor({state:'visible'});assert((await page.locator('#weather-data').textContent()).includes('23'));
await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));await page.screenshot({path:'test-results/account-mobile.png',fullPage:true});
assert.deepEqual(errors,[]);console.log('Account UI PASS: register, login, durable memory, delete memory, password change, city selection, mobile');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exitCode=1;});
