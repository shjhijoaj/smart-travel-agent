"""Dify SSE decoder and reasoning filter. No fabricated token streaming."""
import json
import re
import anyio
import httpx


class ReasoningFilter:
    def __init__(self):
        self.buffer = ''
        self.hidden = False
        self.comment = False

    def feed(self, text, final=False):
        self.buffer += text
        output = ''
        while self.buffer:
            if self.comment:
                end = self.buffer.find('-->')
                if end < 0:
                    self.buffer = self.buffer[-2:]
                    break
                self.buffer = self.buffer[end+3:]
                self.comment = False
                continue
            pos = self.buffer.find('<')
            if pos < 0:
                if not self.hidden:
                    output += self.buffer
                self.buffer = ''
                break
            if not self.hidden:
                output += self.buffer[:pos]
            self.buffer = self.buffer[pos:]
            if self.buffer.startswith('<!--'):
                self.comment = True
                self.buffer = self.buffer[4:]
                continue
            end = self.buffer.find('>')
            if end < 0:
                if final:
                    # Never flush an incomplete provider tag or hidden block.
                    self.buffer = ''
                break
            tag = self.buffer[:end+1]
            if re.fullmatch(r'<think\b[^>]*>', tag, re.I):
                self.hidden = True
            elif re.fullmatch(r'</think\s*>', tag, re.I):
                self.hidden = False
            elif not self.hidden:
                output += tag
            self.buffer = self.buffer[end+1:]
        return output


async def sse_objects(response):
    lines = []
    async for line in response.aiter_lines():
        if line == '':
            if lines:
                payload = '\n'.join(lines)
                if payload != '[DONE]':
                    yield json.loads(payload)
                lines = []
        elif line.startswith('data:'):
            lines.append(line[5:].lstrip())
    if lines and '\n'.join(lines) != '[DONE]':
        yield json.loads('\n'.join(lines))


async def dify_stream(base_url, endpoint, api_key, payload, timeout):
    filter_ = ReasoningFilter()
    text, finished, task_id = '', False, None
    result = dict(success=True, source='dify')
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream('POST', base_url+endpoint, headers={'Authorization': 'Bearer '+api_key}, json=payload) as response:
                response.raise_for_status()
                async for event in sse_objects(response):
                    task_id = event.get('task_id', task_id)
                    kind = event.get('event')
                    if kind == 'error':
                        raise ValueError('Dify 执行失败，请检查模型及工作流配置')
                    if kind in ('message', 'agent_message', 'text_chunk'):
                        fragment = event.get('answer', '') if kind != 'text_chunk' else event.get('data', {}).get('text', '')
                        delta = filter_.feed(fragment)
                        if delta:
                            text += delta
                            if len(text) > 200000:
                                raise ValueError('方案过长，已停止接收')
                            yield {'event': 'delta', 'text': delta}
                    elif kind == 'node_started':
                        yield {'event': 'status', 'message': '正在执行：'+str(event.get('data', {}).get('title', '规划节点'))[:100]}
                    elif kind == 'workflow_finished':
                        data = event.get('data', {})
                        if data.get('status') != 'succeeded':
                            raise ValueError('Dify 工作流未成功完成')
                        result['workflow_id'] = event.get('workflow_run_id')
                        if endpoint.endswith('/workflows/run'):
                            result['outputs'] = data.get('outputs', {})
                            finished = True
                    elif kind == 'message_end':
                        result.update(message_id=event.get('message_id'), conversation_id=event.get('conversation_id'))
                        result['sources'] = event.get('metadata', {}).get('retriever_resources', [])
                        finished = True
                    elif kind == 'message_replace':
                        # Moderation replacements supersede earlier output.
                        filter_ = ReasoningFilter()
                        text = filter_.feed(event.get('answer', ''), final=True)
                        yield {'event': 'replace', 'text': text}
                    if finished:
                        break
            if not finished:
                raise ValueError('上游流提前中断，方案未保存，请重试')
            tail = filter_.feed('', final=True)
            if tail:
                text += tail
                yield {'event': 'delta', 'text': tail}
            if endpoint.endswith('/chat-messages'):
                if not text.strip():
                    raise ValueError('Dify 未返回最终方案')
                result['answer'] = text.strip()
            elif not result.get('outputs'):
                raise ValueError('Dify 未返回有效输出')
            yield {'event': 'result', 'result': result}
        finally:
            if task_id and not finished:
                # Closing the stream also asks Dify to stop work; failure is best effort.
                with anyio.CancelScope(shield=True):
                    try:
                        stop = '/v1/chat-messages/' if endpoint.endswith('/chat-messages') else '/v1/workflows/tasks/'
                        await client.post(base_url+stop+task_id+'/stop', headers={'Authorization':'Bearer '+api_key},
                                          json={'user':payload['user']}, timeout=3)
                    except httpx.HTTPError:
                        pass


def encode(event):
    return 'event: '+event['event']+'\ndata: '+json.dumps(event, ensure_ascii=False)+'\n\n'
