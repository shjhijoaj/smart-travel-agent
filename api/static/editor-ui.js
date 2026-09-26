/* Editable itinerary: mutate the saved record only after a successful response. */
let unsavedSchedule=false;
window.addEventListener('beforeunload',event=>{if(unsavedSchedule){event.preventDefault();event.returnValue='';}});
saveStructured=async function(days){
  if(!current)return;
  if(!current.id)throw Error('方案未保存到服务器，请先生成并保存一份新方案，再编辑。');
  const saved=await api('/api/history/'+current.id+'/structured',{method:'PATCH',body:JSON.stringify({days})});
  current.result=saved.result;unsavedSchedule=false;show(current);await refreshHistory();
  message('行程修改已保存。复制、下载、日历和打印均使用修改后的内容。');
};
showStructured=function(record){
  let box=$('#structured-editor');if(!box){box=document.createElement('section');box.id='structured-editor';$('#result').after(box);}box.hidden=false;box.replaceChildren();
  const el=(tag,text,className)=>{const n=document.createElement(tag);if(text)n.textContent=text;if(className)n.className=className;return n;};
  const heading=el('div',null,'structured-head');heading.append(el('h3','把行程调整成你的节奏'),el('p','按天编辑时间、地点、费用和提醒，保存后即可带走。','hint'));box.append(heading);
  const days=editableDays(record);if(!days.length){const [start,end]=record.request.travel_dates.split('/');for(let d=new Date(start+'T00:00:00Z');d<=new Date(end+'T00:00:00Z');d.setUTCDate(d.getUTCDate()+1)){days.push({title:'自由安排',date:d.toISOString().slice(0,10),activities:[]});}}
  function activityRow(section,day,item,index){
    const row=el('div',null,'activity-edit');row.append(el('span',String(index+1).padStart(2,'0'),'activity-index'));
    const specs=[['时间',item.time,40,v=>item.time=v],['地点与活动',item.place,160,v=>item.place=v],['交通',item.fields['交通']||'',300,v=>item.fields['交通']=v],['预计费用',item.fields['预计费用']||item.fields['费用']||'',300,v=>item.fields['预计费用']=v],['提醒',Object.entries(item.fields).filter(([k])=>!/时间|地点|活动|交通|费用|time|place/i.test(k)).map(([,v])=>v).filter(Boolean).join('；'),600,v=>{for(const k of Object.keys(item.fields))if(!/时间|地点|活动|交通|费用|time|place/i.test(k))delete item.fields[k];item.fields['提醒']=v;}]];
    for(const [label,value,max,set] of specs){const wrap=el('label',label),input=el('input');input.value=value;input.maxLength=max;input.placeholder=label==='时间'?'09:00—11:00':'待确认';input.setAttribute('aria-label',`${day.date||day.title} 活动${index+1} ${label}`);input.oninput=()=>{set(input.value);unsavedSchedule=true;};wrap.append(input);row.append(wrap);}
    const remove=el('button','移除','text-button');remove.type='button';remove.onclick=()=>{day.activities.splice(index,1);unsavedSchedule=true;draw();};row.append(remove);section.append(row);
  }
  const list=el('div');box.append(list);
  function draw(){list.replaceChildren();for(const [index,day] of days.entries()){const section=el('details',null,'edit-day');section.open=index===0;section.append(el('summary',`第 ${index+1} 天 · ${day.date||'日期待确认'} · ${day.activities.length} 项安排`));for(const [i,item] of day.activities.entries())activityRow(section,day,item,i);const add=el('button','＋ 添加一项活动','secondary');add.disabled=day.activities.length>=20;add.onclick=()=>{day.activities.push({time:'',place:'',fields:{}});unsavedSchedule=true;draw();list.children[index].open=true;list.children[index].querySelector('.activity-edit:last-of-type input')?.focus();};section.append(add);list.append(section);}}
  draw();const buttons=el('div',null,'structured-actions'),save=el('button','保存行程修改','primary'),route=el('button','检查地图路线','secondary'),review=el('button','检查天气与移动安排','secondary');buttons.append(save,route,review);box.append(buttons);
  save.onclick=async()=>{save.disabled=true;try{await saveStructured(days);}catch(e){message(e.message,true);}finally{save.disabled=false;}};
  route.onclick=async()=>{const stops=structuredStops(days);if(stops.length<2)return message('请先填写至少两个具体地点。',true);route.disabled=true;try{const report=await api('/api/travel/route',{method:'POST',body:JSON.stringify({destination:record.request.destination,stops})});routePanel(report);box.dataset.route=JSON.stringify(report);}catch(e){message(e.message,true);}finally{route.disabled=false;}};
  review.onclick=async()=>{review.disabled=true;try{if(unsavedSchedule)await saveStructured(days);const report=await api('/api/travel/review',{method:'POST',body:JSON.stringify({request:record.request,weather:record.result.weather,route:box.dataset.route?JSON.parse(box.dataset.route):null,plan:planText(record.result)})});let area=$('#review-data');if(!area){area=el('section');area.id='review-data';$('#structured-editor').after(area);}area.replaceChildren(el('h3','行程检查'));for(const action of report.actions||[])area.append(el('p',action.message));area.append(el('p',report.next_step||'请确认实际预约与路线。','hint'));message('检查已完成，建议供你判断后修改行程。');}catch(e){message(e.message,true);}finally{review.disabled=false;}};
  if(record.result.edited_plan){$('#raw').textContent=record.result.answer||record.result.plan||Object.values(record.result.outputs||{}).join('\n\n');$('#original').hidden=false;}
};
const historyTools=document.createElement('div');historyTools.className='history-tools';
const historySearch=document.createElement('input');historySearch.id='history-search';historySearch.type='search';historySearch.placeholder='搜索目的地、日期或偏好';historySearch.setAttribute('aria-label','搜索旅行历史');historyTools.append(historySearch);$('#history-list').before(historyTools);
window.travelHistoryOffset=0;let historyTimer;
const pagination=document.createElement('div');pagination.className='history-pagination';const prev=document.createElement('button'),next=document.createElement('button');prev.textContent='上一页';next.textContent='下一页';next.id='history-next';pagination.append(prev,next);$('#history-list').after(pagination);
const originalHistory=refreshHistory;
refreshHistory=async function(){await originalHistory();prev.disabled=window.travelHistoryOffset===0;};
historySearch.oninput=()=>{clearTimeout(historyTimer);historyTimer=setTimeout(()=>{window.travelHistoryOffset=0;refreshHistory();},250);};prev.onclick=()=>{window.travelHistoryOffset=Math.max(0,window.travelHistoryOffset-20);refreshHistory();};next.onclick=()=>{window.travelHistoryOffset+=20;refreshHistory();};
const modeNote=document.createElement('div');modeNote.id='mode-note';modeNote.className='mode-note';document.querySelector('.hero').after(modeNote);
api('/api/ready').then(r=>{modeNote.textContent=r.provider==='dify'?'AI 服务已配置 · 可生成行程并继续手动编辑。':'本地手动规划 · 无需密钥即可创建、编辑、保存和导出行程。配置 Dify 后可启用 AI 生成。';}).catch(e=>{modeNote.textContent='服务尚未就绪：'+e.message;modeNote.classList.add('error');});
refreshHistory();
