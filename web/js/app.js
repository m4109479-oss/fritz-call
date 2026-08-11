const popups =
    document.getElementById("popups");

const notifyButton =
    document.getElementById("notifyButton");

const statusElement =
    document.getElementById("status");

const historyElement =
    document.getElementById("history");


let calls = {};

let socket = null;


/*
 * ==========================================================
 * BENACHRICHTIGUNGEN
 * ==========================================================
 */


function updateNotificationButton() {

    if (!notifyButton) {
        return;
    }


    if (
        "Notification" in window &&
        Notification.permission === "granted"
    ) {

        notifyButton.style.display = "none";

    } else {

        notifyButton.style.display = "block";

    }

}



async function enableNotifications() {

    if (!("Notification" in window)) {

        alert(
            "Dieser Browser unterstützt keine Benachrichtigungen."
        );

        return;
    }


    try {

        await Notification.requestPermission();

        updateNotificationButton();

    } catch (error) {

        console.error(
            "Fehler bei Benachrichtigungen:",
            error
        );

    }

}



if (notifyButton) {

    notifyButton.addEventListener(
        "click",
        enableNotifications
    );

}


updateNotificationButton();



/*
 * ==========================================================
 * HILFSFUNKTIONEN
 * ==========================================================
 */


function escapeHtml(value) {

    if (value === null || value === undefined) {
        return "";
    }


    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");

}



function formatDuration(seconds) {

    seconds =
        Math.max(
            0,
            Math.floor(
                Number(seconds) || 0
            )
        );


    const minutes =
        Math.floor(seconds / 60);


    const remaining =
        seconds % 60;


    return (
        String(minutes).padStart(2, "0")
        + ":"
        + String(remaining).padStart(2, "0")
    );

}



/*
 * ==========================================================
 * BROWSER-BENACHRICHTIGUNG
 * ==========================================================
 */


function showBrowserNotification(call) {

    if (
        !("Notification" in window)
    ) {
        return;
    }


    if (
        Notification.permission !== "granted"
    ) {
        return;
    }


    try {

        new Notification(
            "Eingehender Anruf",
            {
                body:
                    (
                        call.customer ||
                        "Unbekannter Anrufer"
                    )
                    +
                    "\n"
                    +
                    (
                        call.number ||
                        ""
                    ),

                icon:
                    "/favicon.png"
            }
        );

    } catch (error) {

        console.error(
            "Browser-Benachrichtigung fehlgeschlagen:",
            error
        );

    }

}



/*
 * ==========================================================
 * HISTORY
 * ==========================================================
 */


function renderHistory(callsList) {

    if (!historyElement) {
        return;
    }


    historyElement.innerHTML = "";


    if (
        !callsList ||
        callsList.length === 0
    ) {

        historyElement.innerHTML = `
            <div class="call">
                <div class="customer">
                    Keine Anrufe vorhanden
                </div>
            </div>
        `;

        return;
    }



    callsList.forEach(
        call => {

            historyElement.appendChild(
                createHistoryEntry(call)
            );

        }
    );

}



function createHistoryEntry(call) {

    const element =
        document.createElement("div");


    element.className =
        "call";


    const status =
        call.status || "";


    const statusText =
        status === "answered"
            ? "Angenommen"
            : status === "missed"
                ? "Verpasst"
                : "";


    const statusClass =
        status === "answered"
            ? "answered"
            : status === "missed"
                ? "missed"
                : "";


    element.innerHTML = `

        <div class="time">
            ${escapeHtml(call.time)}
        </div>

        <div class="customer">
            ${escapeHtml(
                call.customer ||
                "Unbekannt"
            )}
        </div>

        <div class="number">
            ${escapeHtml(
                call.number || ""
            )}
        </div>

        <div class="target">
            ${escapeHtml(
                call.target || ""
            )}
        </div>

        <div class="duration">
            ${formatDuration(
                call.duration || 0
            )}
        </div>

        <div class="${statusClass}">
            ${statusText}
        </div>

    `;


    return element;

}



async function loadHistory() {

    try {

        const response =
            await fetch(
                "/history",
                {
                    cache: "no-store"
                }
            );


        if (!response.ok) {

            throw new Error(
                `HTTP ${response.status}`
            );

        }


        const data =
            await response.json();


        renderHistory(
            data.calls || []
        );


    } catch (error) {

        console.error(
            "History konnte nicht geladen werden:",
            error
        );

    }

}



async function addHistoryCall(call) {

    /*
     * Die History vom Server laden.
     *
     * Dadurch bleibt die Reihenfolge exakt
     * so wie sie der CallManager liefert.
     */

    await loadHistory();

}



/*
 * ==========================================================
 * POPUPS
 * ==========================================================
 */


function getPopupId(callId) {

    return (
        "popup-" +
        String(callId)
    );

}



function createPopup(call) {

    if (!popups) {
        return;
    }


    const callId =
        String(call.id);


    const popupId =
        getPopupId(callId);


    /*
     * Nicht doppelt erzeugen.
     */

    if (
        document.getElementById(
            popupId
        )
    ) {

        return;

    }


    const popup =
        document.createElement("div");


    popup.id =
        popupId;


    popup.className =
        "popup";


    popup.innerHTML = `

        <div class="popup-title">
            ☎ Eingehender Anruf
        </div>

        <div class="customer">
            ${escapeHtml(
                call.customer ||
                "Unbekannt"
            )}
        </div>

        <div class="number">
            ${escapeHtml(
                call.number ||
                ""
            )}
        </div>

        <div class="target">
            Ziel: ${escapeHtml(
                call.target ||
                ""
            )}
        </div>

        <div class="popup-duration">
            Klingelt...
        </div>

    `;


    /*
     * SOFORT anzeigen.
     */

    popup.style.display =
        "block";


    popups.appendChild(
        popup
    );

}



/*
 * ==========================================================
 * POPUP → CONNECTED
 * ==========================================================
 */


function setConnected(call) {

    const callId =
        String(call.id);


    const popup =
        document.getElementById(
            getPopupId(callId)
        );


    if (!popup) {

        createPopup(call);

    }


    const currentPopup =
        document.getElementById(
            getPopupId(callId)
        );


    if (!currentPopup) {
        return;
    }


    currentPopup.classList.add(
        "connected"
    );


    const title =
        currentPopup.querySelector(
            ".popup-title"
        );


    if (title) {

        title.textContent =
            "🟢 Gespräch läuft";

    }


    const duration =
        currentPopup.querySelector(
            ".popup-duration"
        );


    if (duration) {

        duration.textContent =
            "Gespräch läuft...";

    }

}



/*
 * ==========================================================
 * POPUP ENTFERNEN
 * ==========================================================
 */


function removePopupAfterDelay(callId) {

    const id =
        String(callId);


    /*
     * 2 Sekunden nach Gesprächsende
     * verschwinden lassen.
     */

    setTimeout(
        () => {

            const popup =
                document.getElementById(
                    getPopupId(id)
                );


            if (popup) {

                popup.remove();

            }


            delete calls[id];

        },
        2000
    );

}



/*
 * ==========================================================
 * EVENT VERARBEITEN
 * ==========================================================
 */


function handleCallEvent(call) {

    if (!call) {
        return;
    }


    if (
        call.id === undefined ||
        call.id === null
    ) {
        return;
    }


    const id =
        String(call.id);



    /*
     * ------------------------------------------------------
     * RING
     * ------------------------------------------------------
     */

    if (
        call.event === "RING"
    ) {

        calls[id] = {
            ...call,
            startedAt: Date.now()
        };


        createPopup(
            calls[id]
        );


        showBrowserNotification(
            calls[id]
        );


        return;
    }



    /*
     * ------------------------------------------------------
     * CONNECT
     * ------------------------------------------------------
     */

    if (
        call.event === "CONNECT"
    ) {

        if (calls[id]) {

            calls[id] = {
                ...calls[id],
                ...call,
                connectedAt: Date.now()
            };

        } else {

            calls[id] = {
                ...call,
                connectedAt: Date.now()
            };

        }


        setConnected(
            calls[id]
        );


        return;
    }



    /*
     * ------------------------------------------------------
     * DISCONNECT
     * ------------------------------------------------------
     */

    if (
        call.event === "DISCONNECT"
    ) {

        /*
         * History sofort aktualisieren.
         */

        addHistoryCall(
            call
        );


        /*
         * Popup noch 2 Sekunden anzeigen.
         */

        removePopupAfterDelay(
            id
        );


        return;
    }

}



/*
 * ==========================================================
 * GESPRÄCHSDAUER
 * ==========================================================
 */


function updateDurations() {

    const now =
        Date.now();


    Object.keys(
        calls
    ).forEach(
        id => {

            const call =
                calls[id];


            if (
                !call.connectedAt
            ) {

                return;
            }


            const popup =
                document.getElementById(
                    getPopupId(id)
                );


            if (!popup) {
                return;
            }


            const duration =
                popup.querySelector(
                    ".popup-duration"
                );


            if (!duration) {
                return;
            }


            const seconds =
                Math.floor(
                    (
                        now -
                        call.connectedAt
                    ) / 1000
                );


            duration.textContent =
                "Gesprächsdauer: " +
                formatDuration(
                    seconds
                );

        }
    );

}


setInterval(
    updateDurations,
    1000
);



/*
 * ==========================================================
 * WEBSOCKET
 * ==========================================================
 */


function connectWebSocket() {

    const protocol =
        window.location.protocol === "https:"
            ? "wss:"
            : "ws:";


    const websocketUrl =
        `${protocol}//${window.location.host}/ws`;


    console.log(
        "Verbinde WebSocket:",
        websocketUrl
    );


    try {

        socket =
            new WebSocket(
                websocketUrl
            );

    } catch (error) {

        console.error(
            "WebSocket konnte nicht erstellt werden:",
            error
        );


        if (statusElement) {

            statusElement.textContent =
                "Verbinde...";

        }


        setTimeout(
            connectWebSocket,
            3000
        );


        return;
    }



    /*
     * Verbindung hergestellt
     */

    socket.onopen =
        () => {

            console.log(
                "WebSocket verbunden"
            );


            if (statusElement) {

                statusElement.textContent =
                    "Online";

                statusElement.style.background =
                    "#e8f7ed";

                statusElement.style.color =
                    "#16803c";

            }

        };



    /*
     * Event empfangen
     */

    socket.onmessage =
        event => {

            try {

                const call =
                    JSON.parse(
                        event.data
                    );


                console.log(
                    "Call Event:",
                    call
                );


                handleCallEvent(
                    call
                );


            } catch (error) {

                console.error(
                    "Fehler beim Verarbeiten des Events:",
                    error
                );

            }

        };



    /*
     * Verbindung getrennt
     */

    socket.onclose =
        () => {

            console.log(
                "WebSocket getrennt"
            );


            if (statusElement) {

                statusElement.textContent =
                    "Verbinde...";

                statusElement.style.background =
                    "#fff7ed";

                statusElement.style.color =
                    "#c2410c";

            }


            setTimeout(
                connectWebSocket,
                3000
            );

        };



    /*
     * WebSocket Fehler
     */

    socket.onerror =
        error => {

            console.error(
                "WebSocket Fehler:",
                error
            );

        };

}



/*
 * ==========================================================
 * START
 * ==========================================================
 */


/*
 * History sofort beim Laden holen.
 */

loadHistory();


/*
 * WebSocket starten.
 */

connectWebSocket();
