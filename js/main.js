//  function toggleMenu(){}     
/*  for multiple lines */

async function loadIncludes() {

    const header = document.getElementById("header");
    const footer = document.getElementById("footer");

    if (header) {
        header.innerHTML =
            await fetch("header.html")
                .then(r => r.text());
    }

    if (footer) {
        footer.innerHTML =
            await fetch("footer.html")
                .then(r => r.text());
    }
}

loadIncludes();

// sounds player //
function playSet(url) {
    const player = document.getElementById('player');

    if (player.src !== url) {
        player.src = url;
    }

    player.play();
}
