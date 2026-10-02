const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {parseHTML} = require('linkedom');

function setup() {
    const {document} = parseHTML(fs.readFileSync('web/index.html', 'utf8'));
    // Linkedom does not implement the HTMLSelectElement.value setter.
    Object.defineProperty(document.getElementById('period'), 'value', {value: 'all', writable: true});
    const sockets = [];
    const timeouts = [];
    const requests = [];
    class Socket {
        static OPEN = 1;
        constructor() { this.readyState = 0; sockets.push(this); }
        close() { this.readyState = 3; this.onclose?.(); }
        open() { this.readyState = 1; this.onopen(); }
        message(call) { this.onmessage({data: JSON.stringify(call)}); }
    }
    const context = vm.createContext({
        document, window: {}, location: {protocol: 'https:', host: 'example.test'},
        console, Map, Date, AbortController, WebSocket: Socket,
        setTimeout: (fn, delay) => { const item = {fn, delay}; timeouts.push(item); return item; },
        clearTimeout: () => {}, setInterval: () => {},
        fetch: url => new Promise((resolve, reject) => requests.push({url, resolve, reject})),
    });
    vm.runInContext(fs.readFileSync('web/js/app.js', 'utf8'), context);
    const evaluate = source => vm.runInContext(source, context);
    const tick = () => new Promise(resolve => setImmediate(resolve));
    async function respond(request, data) {
        request.resolve({ok: true, json: async () => data});
        await tick();
    }
    return {document, sockets, timeouts, requests, evaluate, tick, respond};
}

test('history filters, phone search, counters, and copyright', async () => {
    const env = setup();
    const now = Date.now() / 1000;
    await env.respond(env.requests[0], {calls: [
        {id: '1', customer: 'Beispiel, Erika', number: '0561123456', started_at: now, status: 'answered', duration: 42},
        {id: '2', customer: 'unbekannt', number: '0176123456', started_at: now, status: 'missed', duration: 0},
        {id: '3', customer: 'Älterer Anruf', started_at: now - 86400 * 8, status: 'answered'},
    ]});
    assert.equal(env.document.querySelectorAll('#history tr').length, 3);
    assert.equal(env.document.getElementById('todayTotal').textContent, '2');
    assert.equal(env.document.getElementById('todayMissed').textContent, '1');
    env.evaluate("selectedFilter = 'missed'; renderHistory()");
    assert.equal(env.document.querySelectorAll('#history tr').length, 1);
    env.evaluate("selectedFilter = 'all'; byId('search').value = '0561 / 123'; renderHistory()");
    assert.match(env.document.getElementById('history').textContent, /Beispiel, Erika/);
    assert.doesNotMatch(env.document.getElementById('history').textContent, /Unbekannter/);
    env.evaluate("byId('search').value = ''; byId('period').value = '7'; renderHistory()");
    assert.equal(env.document.querySelectorAll('#history tr').length, 2);
    assert.match(env.document.querySelector('footer').textContent, /© Michel Stückrath 2026/);
});

test('customer data is escaped in history and active call markup', async () => {
    const env = setup();
    const call = {id: '1', customer: '<img src=x onerror=alert(1)>', number: '<script>bad()</script>', event: 'RING'};
    await env.respond(env.requests[0], {calls: [call]});
    env.sockets[0].message(call);
    assert.equal(env.document.querySelectorAll('#history img, #history script, #activeCalls img, #activeCalls script').length, 0);
    assert.match(env.document.getElementById('activeCalls').textContent, /<img/);
});

test('live calls, immediate disconnect, and reused call IDs', () => {
    const env = setup();
    const socket = env.sockets[0];
    socket.message({event: 'RING', id: '1', customer: 'Erika', started_at: 100});
    socket.message({event: 'RING', id: '2', customer: 'Max', started_at: 101});
    assert.equal(env.document.querySelectorAll('.active-card').length, 2);
    socket.message({event: 'CONNECT', id: '1', connected_at: Date.now() / 1000});
    assert.equal(env.document.querySelectorAll('.active-card.connected').length, 1);
    socket.message({event: 'DISCONNECT', id: '1'});
    assert.equal(env.document.querySelectorAll('.active-card').length, 1);
    socket.message({event: 'RING', id: '1', customer: 'Neu', started_at: 102});
    assert.equal(env.document.querySelectorAll('.active-card.connected').length, 0);
    assert.match(env.document.getElementById('activeCalls').textContent, /Neu/);
    socket.message({event: 'RESET'});
    assert.equal(env.document.querySelectorAll('.active-card').length, 0);
});

test('reconnect clears stale calls and reloads history and server snapshot', async () => {
    const env = setup();
    env.sockets[0].open();
    env.sockets[0].message({event: 'RING', id: 'old', customer: 'Alt'});
    const staleRequest = env.requests.find(request => request.url === '/status');
    env.sockets[0].close();
    assert.equal(env.document.querySelectorAll('.active-card').length, 0);
    await env.respond(staleRequest, {calls: [{event: 'RING', id: 'old', customer: 'Alt'}]});
    assert.equal(env.document.querySelectorAll('.active-card').length, 0);
    env.timeouts.find(item => item.delay === 3000).fn();
    env.sockets[1].open();
    await env.respond(env.requests.filter(request => request.url === '/status').at(-1), {
        fritz_connected: true, calls: [{event: 'CONNECT', id: 'new', customer: 'Neu', connected_at: Date.now() / 1000}], sync: {state: 'ok'},
    });
    await env.respond(env.requests.filter(request => request.url === '/history').at(-1), {calls: []});
    assert.match(env.document.getElementById('activeCalls').textContent, /Neu/);
    assert.doesNotMatch(env.document.getElementById('activeCalls').textContent, /Alt/);
    assert.match(env.document.getElementById('fritzStatus').textContent, /verbunden/);
});

test('snapshot in flight cannot resurrect a disconnected call', async () => {
    const env = setup();
    env.sockets[0].open();
    const request = env.requests.find(request => request.url === '/status');
    env.sockets[0].message({event: 'DISCONNECT', id: '1'});
    await env.respond(request, {fritz_connected: true, calls: [{event: 'RING', id: '1'}]});
    assert.equal(env.document.querySelectorAll('.active-card').length, 0);
});

test('failed history refresh preserves existing rows and offers visible feedback', async () => {
    const env = setup();
    await env.respond(env.requests[0], {calls: [{customer: 'Erika', status: 'answered'}]});
    env.evaluate('loadHistory()');
    env.requests.at(-1).reject(new Error('offline'));
    await env.tick();
    assert.equal(env.document.getElementById('historyError').hidden, false);
    assert.match(env.document.getElementById('history').textContent, /Erika/);
});
