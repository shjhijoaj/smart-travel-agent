// Build DOM nodes instead of inserting model-generated HTML.
function inline(node,text){
 const parts=text.split(/(\*\*[^*]+\*\*)/g);
 for(const part of parts){if(part.startsWith('**')&&part.endsWith('**')){const strong=document.createElement('strong');strong.textContent=part.slice(2,-2);node.append(strong);}else node.append(document.createTextNode(part));}
}
function renderPlan(text,values){
 result.replaceChildren();const nav=document.querySelector('#sections');nav.replaceChildren();
 const summary=document.querySelector('#summary');summary.replaceChildren();
 for(const label of [values.departure+' → '+values.destination,values.travel_dates,values.companions+' 人','预算上限 ¥'+values.budget]){const tag=document.createElement('span');tag.textContent=label;summary.append(tag);}
 const lines=text.replace(/\r/g,'').split('\n');let list=null,headingIndex=0;
 const cells=line=>line.trim().replace(/^\|/,'').replace(/\|$/,'').split('|').map(x=>x.trim());
 const separator=line=>line&&cells(line).every(x=>/^:?-{3,}:?$/.test(x));
 for(let i=0;i<lines.length;i++){
  const line=lines[i].trim();if(!line){list=null;continue;}
  if(line.includes('|')&&separator(lines[i+1])){
   list=null;const wrap=document.createElement('div');wrap.className='table-wrap';const table=document.createElement('table');const head=document.createElement('thead');const row=document.createElement('tr');
   const headers=cells(line);const timeIndex=headers.findIndex(h=>/时间|时段|time/i.test(h));const placeIndex=headers.findIndex(h=>/地点|景点|location|place/i.test(h));
   if(timeIndex>=0)table.className='itinerary';
   for(const cell of headers){const th=document.createElement('th');th.scope='col';inline(th,cell);row.append(th);}head.append(row);table.append(head);i++;
   const body=document.createElement('tbody');while(i+1<lines.length&&lines[i+1].includes('|')){const tr=document.createElement('tr');cells(lines[++i]).forEach((cell,index)=>{const td=document.createElement('td');td.dataset.label=headers[index]||'';inline(td,cell);if(index===placeIndex&&!/待确认|待定|unknown/i.test(cell)){const a=document.createElement('a');a.href='https://www.amap.com/search?query='+encodeURIComponent(values.destination+' '+cell.replace(/\*\*/g,''));a.target='_blank';a.rel='noopener noreferrer';a.textContent='地图搜索 ↗';td.append(a);}tr.append(td);});body.append(tr);}table.append(body);wrap.append(table);result.append(wrap);continue;
  }
  const clean=line.replace(/^\*\*(.*?)\*\*$/,'$1');
  const heading=clean.match(/^(#{1,6})\s+(.+)/);
  const section=/^[一二三四五六七八九十]+[、．.]\s*\S/.test(clean);
  const day=/^第[一二三四五六七八九十\d]+天(?:\s|[：:（(]|$)/.test(clean);
  if(heading||section||day){list=null;const h=document.createElement(heading?(heading[1].length<=2?'h2':'h3'):(day?'h3':'h2'));inline(h,heading?heading[2]:clean);h.id='section-'+headingIndex++;result.append(h);const link=document.createElement('a');link.href='#'+h.id;link.textContent=h.textContent;nav.append(link);continue;}
  if(/^[-*_]{3,}$/.test(line)||/^```/.test(line)){list=null;continue;}
  const bullet=line.match(/^(?:[-*+] |\d+[.)] )(.+)/);
  if(bullet){if(!list){list=document.createElement('ul');result.append(list);}const li=document.createElement('li');inline(li,bullet[1]);list.append(li);}else{list=null;const p=document.createElement('p');inline(p,line);result.append(p);}
 }
 document.querySelector('#raw').textContent=text;document.querySelector('#original').hidden=false;
}
