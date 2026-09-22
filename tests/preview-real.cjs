// Render the locally saved real-response fixture without another model invocation.
const {chromium}=require('playwright');
const fs=require('node:fs');
(async()=>{
const record=JSON.parse(fs.readFileSync('test-results/real-preview.json','utf8'));
const browser=await chromium.launch({headless:true,...(process.env.BROWSER_PATH?{executablePath:process.env.BROWSER_PATH}:{})});
try{
const page=await browser.newPage({viewport:{width:1440,height:1000}});
await page.route('**/api/history**',route=>route.fulfill({json:route.request().url().endsWith('/api/history')?{items:[record]}:record}));
await page.goto('http://127.0.0.1:8010/');await page.locator('.history-open').click();await page.locator('#result table').first().waitFor();
await page.screenshot({path:'test-results/final-desktop.png',fullPage:true});
await page.setViewportSize({width:390,height:844});await page.screenshot({path:'test-results/final-mobile.png',fullPage:true});
console.log('Real-response preview: tables',await page.locator('#result table').count());
}finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
