function buildSongItem(cancion) {
    // Lógica para truncar la letra a 300 caracteres y añadir el botón de copiar
    let lyricsHtml = '';
    if (cancion.letra) {
        const truncatedLyrics = cancion.letra.length > 300 ? cancion.letra.substring(0, 300) + '...' : cancion.letra;
        lyricsHtml = `
            <div class="song-lyrics-preview" id="lyrics-preview-${cancion.id}">
                <p>${truncatedLyrics}</p>
                <button class="copy-lyrics-button" data-lyrics-id="lyrics-preview-${cancion.id}">Copiar Letra</button>
            </div>`;
    }
    // Lógica para la letra y el botón de copiar
    let lyricsPreview = '';
    let copyButton = '';
    if (cancion.letra) {
        const truncatedLyrics = cancion.letra.length > 300 ? cancion.letra.substring(0, 300) + '...' : cancion.letra;
        lyricsPreview = `<div class="song-lyrics-preview" id="lyrics-preview-${cancion.id}"><p>${truncatedLyrics}</p></div>`;
        copyButton = `<button class="copy-lyrics-button" data-lyrics-id="lyrics-preview-${cancion.id}">Copiar Letra</button>`;
    }
    // Lógica para la foto con enlace de descarga
    let photoHtml = cancion.ruta_foto ?
    `<div class="song-image">
    <a href="/static/${cancion.ruta_foto}" download="${cancion.titulo.replace(' ', '_')}.jpg">
         <img src="/static/${cancion.ruta_foto}" alt="Foto de ${cancion.titulo}" class="foto-cancion">
     </a>
    </div>` :
    `<div class="song-image"><span class="no-photo">No hay foto disponible</span></div>`;

    // Lógica para la URL web
    let webUrl = '';
    if (cancion.url_web_foto) {
        webUrl = `<div class="web-url">URL Web: <a href="${cancion.url_web_foto}" target="_blank">${cancion.url_web_foto}</a></div>`;
    }

    
    
    // Lógica para el botón de subir a la web
    let uploadButton = cancion.ruta_foto ? `
        <form action="/subir_a_web/${cancion.id}" method="post" style="display:inline;">
            <button type="submit" class="action-button upload-button">Subir a Web</button>
        </form>` : '';

    let html = `
<li class="song-item">
    <div class="song-info">
        <strong>${cancion.titulo}</strong>
    </div>
    
    <div class="song-media-actions">
        ${photoHtml}
        ${copyButton}
    </div>

    ${lyricsPreview}

    <div class="song-actions">
        <a href="/editar/${cancion.id}" class="action-button edit-button">Editar</a>
        <form action="/eliminar/${cancion.id}" method="post" style="display:inline;">
            <button type="submit" class="action-button delete-button" onclick="return confirm('¿Estás seguro de que quieres eliminar esta canción?');">
                Eliminar
            </button>
        </form>
        ${uploadButton}
    </div>
    ${webUrl}
</li>
`;
return html;
}

document.addEventListener('click', function(event) {
    if (event.target.classList.contains('copy-lyrics-button')) {
        const lyricsId = event.target.dataset.lyricsId;
        // La lógica aquí debe obtener todo el texto, no solo el truncado.
        // Podrías ajustar tu `buildSongItem` para incluir el texto completo.
        // Por ahora, funciona con el texto visible.
        const lyricsElement = document.getElementById(lyricsId).querySelector('p');
        if (lyricsElement) {
            navigator.clipboard.writeText(lyricsElement.innerText.replace('...', '').trim())
                .then(() => {
                    alert('¡Letra copiada al portapapeles!');
                })
                .catch(err => {
                    console.error('Error al copiar la letra:', err);
                    alert('No se pudo copiar la letra.');
                });
        }
    }
});

function buscarCanciones() {
    const query = document.getElementById('searchInput').value;
    const songListContainer = document.getElementById('song-list-container');
    
    fetch(`/buscar?q=${query}`)
        .then(response => response.json())
        .then(canciones => {
            let htmlContent = `<ul class="song-list">`;
            if (canciones.length > 0) {
                canciones.forEach(cancion => {
                    htmlContent += buildSongItem(cancion);
                });
            } else {
                htmlContent += `<li class="no-songs">No se encontraron canciones.</li>`;
            }
            htmlContent += `</ul>`;
            
            songListContainer.innerHTML = htmlContent;
        })
        .catch(error => {
            console.error('Error en la búsqueda:', error);
            songListContainer.innerHTML = `<p class="error">Ocurrió un error al buscar las canciones.</p>`;
        });
}