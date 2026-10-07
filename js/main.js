async function loadFragment(id, url) {
    const target = document.getElementById(id);

    if (!target) {
        return;
    }

    try {
        const response = await fetch(url);

        if (!response.ok) {
            throw new Error(`${response.status} ${response.statusText}`);
        }

        target.innerHTML = await response.text();
    } catch (error) {
        console.error(`Unable to load ${url}:`, error);
    }
}

async function loadIncludes() {
    await Promise.all([
        loadFragment("header", "header.html"),
        loadFragment("footer", "footer.html")
    ]);
}

loadIncludes();

// Sound player
function playSet(url) {
    const player = document.getElementById("player");

    if (!player) {
        return;
    }

    if (player.getAttribute("src") !== url) {
        player.src = url;
    }

    player.play().catch(error => {
        console.error("Unable to play set:", error);
    });
}
