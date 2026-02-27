/**
 * Componente de OCR de placa veicular.
 *
 * Captura imagem via file input, envia para backend
 * POST /fotos/ocr-placa e exibe placa detectada.
 */
function ocrPlacaComponent() {
  return {
    placa: null,
    processing: false,

    async processImage(event) {
      const file = event.target.files[0];
      if (!file) return;

      this.processing = true;
      this.placa = null;

      try {
        const result = await api.uploadFile("/fotos/ocr-placa", file);
        if (result.detectada) {
          this.placa = result.placa;
          // Disparar evento para preencher autocomplete de veículo
          this.$dispatch("ocr-placa-detected", { placa: result.placa });
        } else {
          showToast("Nenhuma placa detectada na imagem", "warning");
        }
      } catch {
        showToast("Erro ao processar OCR", "error");
      } finally {
        this.processing = false;
      }
    },
  };
}
