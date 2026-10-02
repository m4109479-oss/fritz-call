"use strict";

const byId = id => document.getElementById(id);
let activeCalls = new Map();
let historyCalls = [];
let selectedFilter = "all";
let socket = null;
let reconnectTimer = null;
let callRevision = 0;
let statusRequest = 0;
let historyRequest = 0;

function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#039;");
}

function formatDuration(value) {
    const seconds = Math.max(0, Math.floor(Number(value) || 0));
    return String(Math.floor(seconds / 60)).padStart(2, "0") + ":" + String(seconds % 60).padStart(2, "0");
}

function callDate(call) {
    if (Number.isFinite(Number(call.started_at)) && call.started_at != null) {
        return new Date(Number(call.started_at) * 1000);
    }
    const match = String(call.time || "").match(/^(\d{2})\.(\d{2})\.(\d{2}|\d{4}) (\d{2}):(\d{2}):(\d{2})$/);
    if (!match) return null;
    const year = match[3].length === 2 ? 2000 + Number(match[3]) : Number(match[3]);
    return new Date(year, Number(match[2]) - 1, Number(match[1]), Number(match[4]), Number(match[5]), Number(match[6]));
}

function sameDay(first, second) {
    return first && first.getFullYear() === second.getFullYear() &&
        first.getMonth() === second.getMonth() && first.getDate() === second.getDate();
}

function customerName(call) {
    return !call.customer || call.customer === "unbekannt" ? "Unbekannter Anrufer" : call.customer;
}

function renderHistory() {
    const now = new Date();
    const today = historyCalls.filter(call => sameDay(callDate(call), now));
    byId("todayTotal").textContent = today.length;
    byId("todayAnswered").textContent = today.filter(call => call.status === "answered").length;
    byId("todayMissed").textContent = today.filter(call => call.status === "missed").length;
    const search = byId("search").value.trim().toLocaleLowerCase("de-DE");
    const digits = search.replace(/\D/g, "");
    const period = byId("period").value;
    const cutoff = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (period !== "all" && period !== "today") cutoff.setDate(cutoff.getDate() - Number(period) + 1);
    const filtered = historyCalls.filter(call => {
        if (selectedFilter !== "all" && call.status !== selectedFilter) return false;
        const date = callDate(call);
        if (period === "today" && !sameDay(date, now)) return false;
        if (period !== "today" && period !== "all" && (!date || date < cutoff || date > now)) return false;
        const text = [customerName(call), call.number, call.target].join(" ").toLocaleLowerCase("de-DE");
        const phoneMatch = /^[+\d\s()/.-]+$/.test(search) && digits &&
            String(call.number || "").replace(/\D/g, "").includes(digits);
        return !search || text.includes(search) || phoneMatch;
    });
    byId("historyCount").textContent = filtered.length + " von " + historyCalls.length + " gespeicherten Anrufen";
    byId("history").innerHTML = filtered.length ? filtered.map(call => {
        const date = callDate(call);
        const time = date ? date.toLocaleTimeString("de-DE", {hour: "2-digit", minute: "2-digit", second: "2-digit"}) : call.time || "—";
        const day = date ? date.toLocaleDateString("de-DE", {day: "2-digit", month: "2-digit", year: "numeric"}) : "";
        const status = call.status === "answered" ? '<span class="badge success">✓ Angenommen</span>' :
            call.status === "missed" ? '<span class="badge danger">↙ Verpasst</span>' : '<span class="badge neutral">Unbekannt</span>';
        return '<tr><td class="time">' + escapeHtml(time) + '<span class="date">' + escapeHtml(day) +
            '</span></td><td class="customer">' + escapeHtml(customerName(call)) +
            '</td><td class="number">' + escapeHtml(call.number || "Unterdrückt") +
            '</td><td class="target">' + escapeHtml(call.target || "—") +
            '</td><td class="duration">' + formatDuration(call.duration) +
            '</td><td class="call-status">' + status + '</td></tr>';
    }).join("") : '<tr><td class="empty" colspan="6">' +
        (historyCalls.length ? "Keine Anrufe für diese Auswahl." : "Noch keine abgeschlossenen Anrufe vorhanden.") + '</td></tr>';
}

function renderActive() {
    byId("activeCount").textContent = activeCalls.size;
    byId("activeCalls").innerHTML = activeCalls.size ? Array.from(activeCalls.values()).map(call => {
        const connected = call.event === "CONNECT";
        return '<article class="active-card' + (connected ? ' connected' : '') + '">' +
            '<span class="badge ' + (connected ? 'success' : 'warning') + '">' +
            (connected ? '● Gespräch läuft' : '☎ Eingehender Anruf') + '</span><h3>' +
            escapeHtml(customerName(call)) + '</h3><p class="active-details">' +
            escapeHtml(call.number || "Unterdrückte Rufnummer") + ' · Ziel ' + escapeHtml(call.target || "—") +
            (call.extension ? ' · Nebenstelle ' + escapeHtml(call.extension) : '') +
            '</p><span class="active-duration" data-call-id="' + escapeHtml(call.id) +
            '"></span></article>';
    }).join("") : '<p class="active-empty">Aktuell keine aktiven Anrufe.</p>';
    updateDurations();
}

function updateDurations() {
    document.querySelectorAll("[data-call-id]").forEach(element => {
        const call = activeCalls.get(element.dataset.callId);
        if (!call) return;
        element.textContent = call.event === "CONNECT" ?
            "Gesprächsdauer: " + formatDuration((Date.now() - Number(call.connected_at) * 1000) / 1000) : "Klingelt …";
    });
}

function setBadge(id, text, style) {
    const element = byId(id);
    element.textContent = text;
    element.className = "badge " + style;
}

function renderStatus(data) {
    setBadge("fritzStatus", data.fritz_connected ? "FRITZ!Box verbunden" : "FRITZ!Box getrennt",
        data.fritz_connected ? "success" : "danger");
    const element = byId("exportInfo");
    const modified = data.export_modified_at ? new Date(data.export_modified_at) : null;
    const valid = modified && !Number.isNaN(modified.getTime());
    const stale = valid && Date.now() - modified.getTime() > 48 * 3600000;
    let text = valid ? "Kundenexport: " + modified.toLocaleString("de-DE") : "Kundenexport nicht verfügbar";
    if (data.sync?.state === "error") text += " · Abgleich fehlgeschlagen";
    else if (data.sync?.state === "syncing") text += " · Wird aktualisiert";
    else if (stale) text += " · Älter als 48 Stunden";
    element.textContent = text;
    element.className = "export-info" + (!valid || stale || data.sync?.state === "error" ? " warning" : "");
}

async function fetchJson(url) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);
    try {
        const response = await fetch(url, {cache: "no-store", signal: controller.signal});
        if (!response.ok) throw new Error("HTTP " + response.status);
        return await response.json();
    } finally {
        clearTimeout(timeout);
    }
}

async function loadHistory() {
    const request = ++historyRequest;
    try {
        const data = await fetchJson("/history");
        if (request !== historyRequest) return;
        historyCalls = data.calls || [];
        byId("historyError").hidden = true;
        renderHistory();
    } catch (error) {
        if (request !== historyRequest) return;
        byId("historyError").textContent = "Anrufliste konnte nicht aktualisiert werden. Bitte erneut versuchen.";
        byId("historyError").hidden = false;
    }
}

async function loadStatus() {
    const request = ++statusRequest;
    const revision = callRevision;
    try {
        const data = await fetchJson("/status");
        if (request !== statusRequest) return;
        renderStatus(data);
        // Do not overwrite an event received while this snapshot was in flight.
        if (revision === callRevision) {
            activeCalls = new Map((data.calls || []).map(call => [String(call.id), call]));
            renderActive();
        }
    } catch (error) {
        if (request !== statusRequest) return;
        setBadge("fritzStatus", "FRITZ!Box: Status unbekannt", "warning");
        byId("exportInfo").textContent = "Kundenexport: Status nicht verfügbar";
        byId("exportInfo").className = "export-info warning";
    }
}

function showNotification(call) {
    if (!("Notification" in window) || Notification.permission !== "granted") return;
    try {
        new Notification("Eingehender Anruf", {
            body: customerName(call) + "\n" + (call.number || "Unterdrückte Rufnummer"),
            icon: "/favicon.png",
            tag: "fritz-call-" + call.id + "-" + call.started_at,
        });
    } catch (error) { console.warn("Benachrichtigung konnte nicht angezeigt werden"); }
}

function handleCallEvent(call) {
    if (!call) return;
    callRevision++;
    if (call.event === "RESET") {
        activeCalls.clear();
        renderActive();
        loadStatus();
        return;
    }
    if (call.id === undefined || call.id === null) return;
    const id = String(call.id);
    if (call.event === "DISCONNECT") {
        activeCalls.delete(id);
        renderActive();
        loadHistory();
    } else if (call.event === "RING" || call.event === "CONNECT") {
        const previous = activeCalls.get(id);
        // Callmonitor IDs are reused, so a new RING must replace the old object.
        activeCalls.set(id, call.event === "RING" ? {...call} : {...previous, ...call});
        renderActive();
        if (call.event === "RING" && (!previous || previous.started_at !== call.started_at)) showNotification(call);
    }
}

function updateNotificationButton() {
    const button = byId("notifyButton");
    if (!("Notification" in window)) {
        button.hidden = true;
    } else if (Notification.permission === "granted") {
        button.hidden = true;
    } else if (Notification.permission === "denied") {
        button.textContent = "Benachrichtigungen blockiert";
        button.title = "Bitte in den Website-Einstellungen des Browsers erlauben.";
        button.disabled = true;
    }
}

byId("notifyButton").addEventListener("click", async () => {
    try { await Notification.requestPermission(); updateNotificationButton(); }
    catch (error) { byId("notifyButton").textContent = "Bitte Browser-Einstellungen prüfen"; }
});

function connectWebSocket() {
    clearTimeout(reconnectTimer);
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    const currentSocket = new WebSocket(protocol + "//" + location.host + "/ws");
    socket = currentSocket;
    currentSocket.onopen = () => {
        if (socket !== currentSocket) return;
        setBadge("status", "Webserver verbunden", "success");
        loadStatus();
        loadHistory();
    };
    currentSocket.onmessage = event => {
        if (socket !== currentSocket) return;
        try { handleCallEvent(JSON.parse(event.data)); }
        catch (error) { console.warn("Telefonereignis konnte nicht verarbeitet werden"); }
    };
    currentSocket.onclose = () => {
        if (socket !== currentSocket) return;
        // Discard both uncertain live calls and in-flight snapshots.
        statusRequest++;
        historyRequest++;
        callRevision++;
        activeCalls.clear();
        renderActive();
        setBadge("status", "Webserver: verbinde …", "warning");
        setBadge("fritzStatus", "FRITZ!Box: Status unbekannt", "neutral");
        reconnectTimer = setTimeout(connectWebSocket, 3000);
    };
    currentSocket.onerror = () => currentSocket.close();
}

document.querySelectorAll("[data-filter]").forEach(button => button.addEventListener("click", () => {
    selectedFilter = button.dataset.filter;
    document.querySelectorAll("[data-filter]").forEach(tab => {
        const selected = tab.dataset.filter === selectedFilter;
        tab.classList.toggle("active", selected);
        tab.setAttribute("aria-pressed", String(selected));
    });
    renderHistory();
}));
byId("search").addEventListener("input", renderHistory);
byId("period").addEventListener("change", renderHistory);
byId("refreshButton").addEventListener("click", async () => {
    byId("refreshButton").disabled = true;
    await Promise.all([loadHistory(), loadStatus()]);
    byId("refreshButton").disabled = false;
});
setInterval(updateDurations, 1000);
setInterval(() => {
    if (socket?.readyState === WebSocket.OPEN) loadStatus();
}, 15000);
setInterval(renderHistory, 60000);
updateNotificationButton();
loadHistory();
connectWebSocket();
