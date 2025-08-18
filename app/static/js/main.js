document.addEventListener("DOMContentLoaded", function () {
    const searchInput = document.getElementById("search-input");
    const songResultsContainer = document.getElementById("song-results");
    const loadingIndicator = document.getElementById("loading");
    let searchTimer;

    function fetchResults(query) {
        if (loadingIndicator) {
            loadingIndicator.style.display = 'block';
        }

        const url = new URL(window.location.href);
        url.searchParams.set("q", query);

        fetch(url, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => response.text())
        .then(html => {
            if (songResultsContainer) {
                songResultsContainer.innerHTML = html;
            }
        })
        .catch(error => console.error("Error fetching search results:", error))
        .finally(() => {
            if (loadingIndicator) {
                loadingIndicator.style.display = 'none';
            }
        });
    }

    if (searchInput) {
        searchInput.addEventListener("keyup", function () {
            clearTimeout(searchTimer);
            const query = this.value;
            if (query.length > 2 || query.length === 0) {
                searchTimer = setTimeout(() => {
                    fetchResults(query);
                }, 300); // Pequeño retraso para evitar peticiones excesivas
            }
        });
    }
});

// Función para copiar texto
function copyToClipboard(elementId) {
    const lyricsElement = document.getElementById(elementId);
    if (lyricsElement) {
        const textToCopy = lyricsElement.textContent || lyricsElement.innerText;
        navigator.clipboard.writeText(textToCopy).then(() => {
            alert('Texto copiado al portapapeles!');
        }).catch(err => {
            console.error('Error al copiar el texto: ', err);
            alert('Error al copiar el texto.');
        });
    }
}