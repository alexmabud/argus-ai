/**
 * Componente de GPS com geocoding reverso.
 *
 * Captura coordenadas via Geolocation API (high accuracy)
 * e resolve endereço via Nominatim (OpenStreetMap).
 */
async function _resolveGPSPosition(position) {
  const { latitude, longitude, accuracy } = position.coords;
  let endereco_texto = null;

  // Geocoding reverso via Nominatim
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json&addressdetails=1`,
      { headers: { "Accept-Language": "pt-BR" } }
    );
    if (response.ok) {
      const data = await response.json();
      const addr = data.address;
      const parts = [
        addr.road,
        addr.house_number,
        addr.suburb || addr.neighbourhood,
        addr.city || addr.town || addr.village,
      ].filter(Boolean);
      endereco_texto = parts.join(", ");
    }
  } catch {
    // Geocoding falhou — retorna só coordenadas
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
