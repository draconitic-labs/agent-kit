#!/usr/bin/env python3
"""Read-only live MCP smoke against public Draconitic evidence. No credentials."""
import json
import urllib.request

URL = 'https://agents.draconitic.com/mcp'


def rpc(method, params, call_id, session=None):
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json, text/event-stream',
               'User-Agent': 'draconitic-agent-kit-smoke/0.1.0',
               'MCP-Protocol-Version': '2025-03-26'}
    if session: headers['Mcp-Session-Id'] = session
    body = {'jsonrpc': '2.0', 'method': method, 'params': params}
    if call_id is not None: body['id'] = call_id
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers=headers)
    with urllib.request.urlopen(req, timeout=30) as response:
        data = response.read().decode(); current = response.headers.get('Mcp-Session-Id', session)
    if not data: return {}, current
    if data.lstrip().startswith('{'): value = json.loads(data)
    else:
        messages = [json.loads(line[5:].strip()) for line in data.splitlines() if line.startswith('data:')]
        value = next(x for x in messages if x.get('id') == call_id)
    if 'error' in value: raise RuntimeError('MCP error: ' + json.dumps(value['error']))
    return value.get('result', {}), current


def smoke():
    init, session = rpc('initialize', {'protocolVersion': '2025-03-26', 'capabilities': {},
                        'clientInfo': {'name': 'draconitic-kit-read-smoke', 'version': '0.1.0'}}, 1)
    _, session = rpc('notifications/initialized', {}, None, session)
    listing, session = rpc('tools/list', {}, 2, session)
    tools = {t['name']: t for t in listing['tools']}
    calls = [
        ('knowledge_catalog', {'site': 'markets', 'limit': 2}),
        ('knowledge_lookup', {'query': 'react', 'limit': 1}),
        ('knowledge_verify_exists', {'kind': 'npm_package', 'identifier': 'synthetic-draconitic-kit-missing-1793052000'}),
        ('knowledge_changes_since', {'since': '2026-10-01', 'limit': 1}),
        ('knowledge_check_citations', {'record_ids': ['synthetic:missing'], 'urls': ['https://example.org/source']}),
        ('knowledge_check_claims', {'claims': [{'record_id': 'synthetic:missing', 'text': 'Synthetic missing evidence'}]}),
    ]
    rows = []
    for i, (name, args) in enumerate(calls, 3):
        if tools[name].get('annotations', {}).get('readOnlyHint') is not True:
            raise RuntimeError('tool does not declare read-only behavior')
        result, session = rpc('tools/call', {'name': name, 'arguments': args}, i, session)
        if result.get('isError'): raise RuntimeError('tool failed: ' + name)
        if not result.get('content') and not result.get('structuredContent'):
            raise RuntimeError('tool returned no content: ' + name)
        rows.append({'tool': name, 'arguments': args, 'result': result})
    def structured(result):
        return result.get('structuredContent') or json.loads(result['content'][0]['text'])
    by_name = {row['tool']: structured(row['result']) for row in rows}
    if not by_name['knowledge_catalog'].get('datasets'):
        raise RuntimeError('catalog did not return datasets')
    if by_name['knowledge_verify_exists']['status'] != 'unknown':
        raise RuntimeError('missing identifier did not return unknown')
    if not by_name['knowledge_changes_since'].get('items'):
        raise RuntimeError('change query did not return records')
    record = by_name['knowledge_lookup']['items'][0]['record']
    entity = record['entity']
    positive = [
        ('knowledge_verify_exists', {'kind': entity['kind'], 'identifier': entity['identifier']}),
        ('knowledge_check_citations', {'record_ids': [record['id']], 'urls': [record['sources'][0]['url']]}),
        ('knowledge_check_claims', {'claims': [{'record_id': record['id'], 'text': record['summary']}]}),
    ]
    for i, (name, args) in enumerate(positive, 20):
        result, session = rpc('tools/call', {'name': name, 'arguments': args}, i, session)
        if result.get('isError'): raise RuntimeError('positive case failed: ' + name)
        data = structured(result)
        if name == 'knowledge_verify_exists' and data.get('status') != 'exists':
            raise RuntimeError('covered exact identifier did not return exists')
        if name == 'knowledge_check_citations' and not data['checks'][0].get('matches'):
            raise RuntimeError('known citation did not match')
        if name == 'knowledge_check_claims' and data['checks'][0].get('status') != 'matches_curated_record':
            raise RuntimeError('known summary did not match')
        rows.append({'tool': name, 'arguments': args, 'result': result})
    return {'server': init.get('serverInfo'), 'protocol': init.get('protocolVersion'), 'tools': sorted(tools), 'calls': rows}


if __name__ == '__main__':
    print(json.dumps(smoke(), indent=2))
