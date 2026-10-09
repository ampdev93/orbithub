let activeSetLink = null;
let activeSetLabel = "";

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
        const eventTarget = event.verified === false
            ? document.getElementById("unverified-sets-list")
            : target;

        if (!eventTarget) {
            return;
        }

        const date = document.createElement(event.flyer ? "a" : "span");
        date.textContent = event.display_date || event.date;

        if (event.flyer) {
            date.href = event.flyer;
            date.target = "_blank";
            date.rel = "noopener noreferrer";
        }

        eventTarget.appendChild(date);
        eventTarget.appendChild(document.createTextNode(" "));

        event.sets.forEach((set, index) => {
            const setLink = document.createElement("a");
            const label = set.label || `${set.number}. ${set.artist}`;

            setLink.href = "#";
            setLink.className = "set-link";
            setLink.dataset.label = label;
            setLink.textContent = label;
            setLink.setAttribute("aria-label", `Play ${label}`);

            setLink.addEventListener("click", event => {
                event.preventDefault();
                selectSet(setLink, label);
                playSet(set.audio);
            });

            eventTarget.appendChild(setLink);

            if (index < event.sets.length - 1) {
                eventTarget.appendChild(document.createTextNode(" "));
            }
        });

        eventTarget.appendChild(document.createElement("br"));
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
        eventTarget.appendChild(document.createElement("br"));
    });
}

function setPlayerState(state) {
    const stop = document.getElementById("stop-player");
    const status = document.getElementById("player-status");

    if (!activeSetLink || !stop || !status) {
        return;
    }

    activeSetLink.classList.remove("loading", "playing");

    if (state === "loading") {
        activeSetLink.classList.add("loading");
        activeSetLink.textContent = `… ${activeSetLabel}`;
        status.textContent = "Loading";
        stop.disabled = false;
    } else if (state === "playing") {
        activeSetLink.classList.add("playing");
        activeSetLink.textContent = `▶ ${activeSetLabel}`;
        status.textContent = "Playing";
        stop.disabled = false;
    } else {
        activeSetLink.textContent = activeSetLabel;
        status.textContent = "";
        stop.disabled = true;
        activeSetLink = null;
        activeSetLabel = "";
    }
}

function selectSet(link, label) {
    if (activeSetLink && activeSetLink !== link) {
        activeSetLink.classList.remove("loading", "playing");
        activeSetLink.textContent = activeSetLabel;
    }

    activeSetLink = link;
    activeSetLabel = label;
    setPlayerState("loading");
}

function setupPlayerControls() {
    const stop = document.getElementById("stop-player");
    const player = document.getElementById("player");

    if (!stop || !player) {
        return;
    }

    stop.addEventListener("click", () => {
        player.pause();
        player.removeAttribute("src");
        player.load();

        if (activeSetLink) {
            setPlayerState("stopped");
        }
    });

    player.addEventListener("loadstart", () => {
        if (activeSetLink) {
            setPlayerState("loading");
        }
    });

    player.addEventListener("waiting", () => {
        if (activeSetLink) {
            setPlayerState("loading");
        }
    });

    player.addEventListener("playing", () => {
        if (activeSetLink) {
            setPlayerState("playing");
        }
    });

    player.addEventListener("ended", () => {
        if (activeSetLink) {
            setPlayerState("stopped");
        }
    });

    player.addEventListener("error", () => {
        const status = document.getElementById("player-status");

        if (status) {
            status.textContent = "Audio error";
        }

        if (activeSetLink) {
            activeSetLink.classList.remove("loading", "playing");
            activeSetLink.textContent = activeSetLabel;
        }

        stop.disabled = true;
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
