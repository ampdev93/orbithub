async function fetchResource(url, type = "text") {
    const response = await fetch(url);

    if (!response.ok) {
        throw new Error(`${response.status} ${response.statusText}`);
    }

    return type === "json" ? response.json() : response.text();
}

async function loadFragment(id, url) {
    const target = document.getElementById(id);

    if (!target) {
        return;
    }

    try {
        target.innerHTML = await fetchResource(url);
    } catch (error) {
        console.error(`Unable to load ${url}:`, error);
    }
}

async function loadJson(url) {
    try {
        return await fetchResource(url, "json");
    } catch (error) {
        console.error(`Unable to load ${url}:`, error);
        return [];
    }
}

async function loadIncludes() {
    await Promise.all([
        loadFragment("header", "header.html"),
        loadFragment("footer", "footer.html")
    ]);
}

async function renderFlyers() {
    const target = document.getElementById("flyer-gallery");

    if (!target) {
        return;
    }

    const flyers = await loadJson("content/flyers.json");

    flyers.forEach(flyer => {
        const link = document.createElement("a");
        link.href = flyer.full;
        link.target = "_blank";
        link.rel = "noopener noreferrer";

        const image = document.createElement("img");
        image.src = flyer.thumbnail;
        image.alt = flyer.alt || "Orbit flyer";

        link.appendChild(image);
        target.appendChild(link);
    });
}

async function renderSets() {
    const target = document.getElementById("sets-list");

    if (!target) {
        return;
    }

    const events = await loadJson("content/sets.json");

    events.forEach(event => {
        const date = document.createElement(event.flyer ? "a" : "span");
        date.textContent = event.display_date || event.date;

        if (event.flyer) {
            date.href = event.flyer;
            date.target = "_blank";
            date.rel = "noopener noreferrer";
        }

        target.appendChild(date);
        target.appendChild(document.createTextNode(" "));

        event.sets.forEach((set, index) => {
            const setLink = document.createElement("a");
            setLink.href = "#";
            setLink.textContent = `${set.number}. ${set.artist}`;
            setLink.addEventListener("click", event => {
                event.preventDefault();
                playSet(set.audio);
            });

            target.appendChild(setLink);

            if (index < event.sets.length - 1) {
                target.appendChild(document.createTextNode(" "));
            }
        });

        target.appendChild(document.createElement("br"));
    });
}

async function renderImages() {
    const target = document.getElementById("image-gallery");

    if (!target) {
        return;
    }

    const images = await loadJson("content/images.json");

    images.forEach(item => {
        const link = document.createElement("a");
        link.href = item.full;
        link.target = "_blank";
        link.rel = "noopener noreferrer";

        const image = document.createElement("img");
        image.src = item.thumbnail;
        image.alt = item.alt || item.caption || "Orbit archive image";

        link.appendChild(image);
        target.appendChild(link);
    });
}

async function renderLinks() {
    const target = document.getElementById("links-list");

    if (!target) {
        return;
    }

    const links = await loadJson("content/links.json");

    links.forEach(item => {
        const link = document.createElement("a");
        link.href = item.url;
        link.target = "_blank";
        link.rel = "noopener noreferrer";
        link.className = "icon-link";

        const label = document.createElement("span");
        label.textContent = item.title;

        link.appendChild(label);
        target.appendChild(link);
        target.appendChild(document.createElement("br"));
    });
}

function setupPlayerControls() {
    const stop = document.getElementById("stop-player");
    const player = document.getElementById("player");

    if (!stop || !player) {
        return;
    }

    stop.addEventListener("click", event => {
        event.preventDefault();
        player.pause();
    });
}

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

loadIncludes();

Promise.all([
    renderFlyers(),
    renderSets(),
    renderImages(),
    renderLinks()
]).then(setupPlayerControls);
