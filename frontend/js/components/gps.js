/**
 * Componente de GPS com geocoding reverso.
 *
 * Captura coordenadas via Geolocation API (high accuracy) e resolve o
 * endereço pelo proxy autenticado do backend (/geocode/reverse) — evita
 * enviar as coordenadas precisas da operação direto ao Nominatim/OSM a
 * partir do dispositivo de cada agente.
 */
async function _resolveGPSPosition(position) {
  const { latitude, longitude, accuracy } = position.coords;
  let endereco_texto = null;

  // Geocoding reverso via proxy do backend (best-effort).
  try {
    const data = await api.get(
      `/geocode/reverse?lat=${encodeURIComponent(latitude)}&lon=${encodeURIComponent(longitude)}`
    );
    endereco_texto = data?.endereco || null;
  } catch {
    // Geocoding falhou (offline/erro) — retorna só coordenadas
  }

  return { latitude, longitude, accuracy, endereco_texto };
}

async function getGPSLocation() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation não suportado"));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => resolve(await _resolveGPSPosition(position)),
      (error) => reject(error),
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 60000,
      }
    );
  });
}

async function getGPSLocationLowAccuracy() {
  return new Promise((resolve, reject) => {
    if (!navigator.geolocation) {
      reject(new Error("Geolocation não suportado"));
      return;
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => resolve(await _resolveGPSPosition(position)),
      (error) => reject(error),
      {
        enableHighAccuracy: false,
        timeout: 15000,
        maximumAge: 300000,
      }
    );
  });
}
