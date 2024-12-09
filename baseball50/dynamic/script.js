// Player Search code

document.getElementById("search-btn").addEventListener("click", async () => {
    const playerInput = document.getElementById("player-input").value;
    const resultsDiv = document.getElementById("results");
    resultsDiv.innerHTML = ""; // Clear previous results

    if (playerInput.trim() === "") {
        resultsDiv.innerHTML = "<p>Please enter a player name.</p>";
        return;
    }

    const response = await fetch("/search", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: `player_name=${encodeURIComponent(playerInput)}`
    });

    const data = await response.json();

    if (data.length === 0) {
        resultsDiv.innerHTML = "<p>No players found.</p>";
    } else {
        data.forEach(player => {
            const playerCard = `
                <div class="result-item">
                    <h3>${player.name} (${player.team})</h3>
                    <p><strong>AVG:</strong> ${player.avg || "N/A"}</p>
                    <p><strong>ERA:</strong> ${player.era || "N/A"}</p>
                    <p><strong>Home Runs:</strong> ${player.home_runs || "N/A"}</p>
                    <p><strong>RBIs:</strong> ${player.rbis || "N/A"}</p>
                </div>
            `;
            resultsDiv.innerHTML += playerCard;
        });
    }
});
