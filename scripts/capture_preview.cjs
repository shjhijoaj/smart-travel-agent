// Capture public README images from fictional fixtures, without model or account data.
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({headless: true,
    ...(process.env.BROWSER_PATH ? {executablePath: process.env.BROWSER_PATH} : {})});
  try {
    const page = await browser.newPage({viewport: {width: 1440, height: 1080}});
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    const answer = `## 行程概览
两天一夜，在西湖边慢下来。以下为界面演示，地点、费用和开放情况请自行核实。
## 每日行程
### 第1天 · 2026-10-03 · 湖畔漫步
| 时间 | 地点与活动 | 交通 | 预计费用 | 提醒 |
|---|---|---|---|---|
| 09:00-11:00 | 西湖湖滨散步 | 地铁后步行 | 待确认 | 随时休息，避开人流 |
| 11:30-13:00 | 湖滨午餐 | 步行 | 待确认 | 提前确认排队情况 |
| 14:00-16:00 | 中国丝绸博物馆 | 公交，路线待确认 | 待确认 | 核实开放时间和预约 |
### 第2天 · 2026-10-04 · 老城与茶香
| 时间 | 地点与活动 | 交通 | 预计费用 | 提醒 |
|---|---|---|---|---|
| 09:00-11:00 | 河坊街文化体验 | 公交 | 待确认 | 按体力调整步行距离 |
| 13:00-15:00 | 茶馆休息与返程 | 交通待确认 | 待确认 | 预留充足返程时间 |
## 预算估算
| 项目 | 所有人合计费用 |
|---|---|
| 交通与住宿 | 待确认 |
| 餐饮与活动 | 待确认 |
| 合计 | 待确认 |
## 下雨备选方案
- 湖滨散步调整为室内展馆，提前确认开放情况。
## 注意事项
- 此为固定虚构演示；出行前核实天气、票价、预约和返程车次。
`;
    const record = {
      id: 'readme-demo',
      request: {departure: '上海', destination: '杭州', travel_dates: '2026-10-03/2026-10-04',
        budget: '3000', companions: '2', preferences: '历史景点、当地美食、少走路', language: '中文'},
      result: {source: 'local-fallback', answer}
    };
    await page.route('**/api/**', route => {
      const endpoint = new URL(route.request().url()).pathname;
      const json = endpoint === '/api/history' ? {items: [record]}
        : endpoint === '/api/history/readme-demo' ? record
        : endpoint === '/api/account/me' ? {user: null}
        : endpoint === '/api/telemetry/summary' ? {count: 0} : {};
      return route.fulfill({json});
    });
    await page.goto(process.env.TRAVEL_URL || 'http://127.0.0.1:8010/');
    await page.locator('.history-open').click();
    await page.locator('#result table').first().waitFor();
    await page.evaluate(() => document.fonts.ready);
    const output = path.resolve(__dirname, '../docs/images');
    fs.mkdirSync(output, {recursive: true});
    await page.evaluate(() => window.scrollTo({top: 0, behavior: 'instant'}));
    await page.screenshot({path: path.join(output, 'desktop.png')});
    await page.setViewportSize({width: 390, height: 1100});
    await page.locator('#panel').evaluate(element => element.scrollIntoView({behavior: 'instant', block: 'start'}));
    assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
    await page.screenshot({path: path.join(output, 'mobile.png')});
    assert.deepEqual(errors, []);
    console.log('Public previews generated from fictional fixtures.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
