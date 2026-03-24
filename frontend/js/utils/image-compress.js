/**
 * Compressao de imagem no cliente antes do upload.
 *
 * Redimensiona imagens para no maximo 1920px no lado maior
 * e exporta como JPEG 85% qualidade. Previne erro 413 em
 * uploads de fotos de celulares modernos (12-48 MP).
 */

/** Dimensao maxima permitida no lado maior (px). */
const MAX_DIMENSION = 1920;

/** Qualidade JPEG de saida (0-1). */
const JPEG_QUALITY = 0.85;

/**
 * Comprime um arquivo de imagem redimensionando e convertendo para JPEG.
 *
 * @param {File} file - Arquivo de imagem original.
 * @returns {Promise<File>} Arquivo comprimido (ou original se falhar).
 */
async function compressImage(file) {
  if (!file.type.startsWith("image/")) {
    return file;
  }

  try {
    const bitmap = await createImageBitmap(file);
    const { width, height } = bitmap;

    let newWidth = width;
    let newHeight = height;

    if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
      if (width >= height) {
        newWidth = MAX_DIMENSION;
        newHeight = Math.round(height * (MAX_DIMENSION / width));
      } else {
        newHeight = MAX_DIMENSION;
        newWidth = Math.round(width * (MAX_DIMENSION / height));
      }
    }

    const canvas = new OffscreenCanvas(newWidth, newHeight);
    const ctx = canvas.getContext("2d");
    ctx.drawImage(bitmap, 0, 0, newWidth, newHeight);
    bitmap.close();

    const blob = await canvas.convertToBlob({
      type: "image/jpeg",
      quality: JPEG_QUALITY,
    });

    const name = file.name.replace(/\.[^.]+$/, ".jpg");
    return new File([blob], name, { type: "image/jpeg" });
  } catch {
    return file;
  }
}
