const status =
    document.getElementById("status");


const history =
    document.getElementById("history");


const popups =
    document.getElementById("popups");


const notifyButton =
    document.getElementById("notifyButton");





function checkNotificationStatus() {

    if (
        Notification.permission === "granted"
    ) {

        notifyButton.style.display = "none";

    }

}





notifyButton.onclick = function() {

    Notification.requestPermission()

    .then(function(permission){

        console.log(
            "Notification:",
            permission
        );

        checkNotificationStatus();

    });

};



checkNotificationStatus();







function showCall(call) {


    let state = "";


    if(call.status === "answered") {

        state =
        "<div class='answered'>✓ Angenommen</div>";

    }


    if(call.status === "missed") {

        state =
        "<div class='missed'>✗ Verpasst</div>";

    }



    return `

<div class="call">


<div class="time">
${call.time || "-"}
</div>


<div class="customer">
${call.customer || "unbekannt"}
</div>


<div class="number">
☎ ${call.number || "unterdrückt"}
</div>


<div class="target">
Ziel: ${call.target || "-"}
</div>


<div class="duration">
${call.duration || 0}s
</div>


${state}


</div>

`;

}





async function loadHistory() {


    const response =
        await fetch("/history");


    const data =
        await response.json();



    history.innerHTML = "";



    data.calls.forEach(call => {


        history.innerHTML +=
            showCall(call);


    });


}









function showPopup(call) {


    popups.innerHTML = `


<div id="popup">


<div class="popup-title">

☎ Eingehender Anruf

</div>



<div class="customer">

${call.customer || "unbekannt"}

</div>



<div class="number">

☎ ${call.number || "unterdrückt"}

</div>



<div class="target">

Ziel: ${call.target || "-"}

</div>


</div>


`;

}






function showConnected() {


    const popup =
        document.getElementById("popup");


    if(popup) {


        popup.classList.add(
            "connected"
        );


        popup.innerHTML += `


<div class="popup-duration">

🟢 Gespräch läuft

</div>


`;

    }


}







function hidePopup() {


    popups.innerHTML = "";

}









const ws = new WebSocket(

    (location.protocol === "https:" ? "wss://" : "ws://")

    + location.host

    + "/ws"

);








ws.onopen = function() {


    status.innerHTML =
        "🟢 Verbunden";


};







ws.onclose = function() {


    status.innerHTML =
        "🔴 Getrennt";


};








ws.onmessage = function(event) {


    console.log(
        "EVENT:",
        event.data
    );



    const call =
        JSON.parse(event.data);






    if(call.event === "RING") {


        if(
            Notification.permission === "granted"
        ) {


            new Notification(

                "☎ Eingehender Anruf",

                {

                    body:

                    (call.customer || "unbekannt")
                    + "\n"
                    + (call.number || "unterdrückt")
                    + "\nZiel: "
                    + (call.target || "-")

                }

            );


        }



        showPopup(call);


    }





    if(call.event === "CONNECT") {


        showConnected();


    }





    if(call.event === "DISCONNECT") {


        setTimeout(

            function(){

                hidePopup();

            },

            2000

        );


    }



    loadHistory();


};







loadHistory();
