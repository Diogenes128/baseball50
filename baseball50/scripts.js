// For trade webpage

document.getElementById("viewRosterBtn").addEventListener("click", () => {
    const username = document.getElementById("username").value;
    fetch("/get_roster", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                username
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                document.getElementById("rosterDisplay").innerHTML =
                    `<h3>${username}'s Roster:</h3><ul>` +
                    data.roster.map(player => `<li>${player}</li>`).join("") +
                    "</ul>";
            } else {
                alert(data.message);
            }
        });
});

function fetchTradeRequests() {
    fetch("/get_trade_requests?user=yourUsername")
        .then(response => response.json())
        .then(data => {
            if (data.status === "success") {
                const request = data.trade_request;
                document.getElementById("tradeMessages").innerHTML = `
            <p>${request.sender} wants to trade: ${request.trade_offer}</p>
            <button class="accept-btn" onclick="respondTrade('accept')">Accept</button>
            <button class="reject-btn" onclick="respondTrade('reject')">Reject</button>
          `;
            } else {
                document.getElementById("tradeMessages").innerHTML = `<p>${data.message}</p>`;
            }
        });
}

function respondTrade(response) {
    fetch("/respond_trade", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            user: "yourUsername",
            response
        })
    }).then(() => fetchTradeRequests());
}

fetchTradeRequests();
