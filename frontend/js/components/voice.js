/**
 * Componente de entrada por voz via Web Speech API.
 *
 * Reconhecimento contínuo em português (pt-BR) com
 * resultados intermediários para feedback em tempo real.
 */
let _recognition = null;

/**
 * Inicia reconhecimento de voz e registra resultados e erros via callbacks.
 *
 * Args:
 *     onResult: Chamado com (text, isFinal) a cada resultado de fala.
 *     onEnd: Chamado quando o reconhecimento encerra (normalmente ou após erro).
 *     onError: Chamado com (errorType) quando ocorre um erro de reconhecimento.
 *
 * Returns:
 *     true se o reconhecimento foi iniciado, false se não suportado.
 */
function startVoice(onResult, onEnd, onError) {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) return false;

  _recognition = new SpeechRecognition();
  _recognition.lang = "pt-BR";
  _recognition.continuous = true;
  _recognition.interimResults = true;

  let _committedFinal = "";

  _recognition.onresult = (event) => {
    let fullFinal = "";
    let interim = "";

    for (let i = 0; i < event.results.length; i++) {
      if (event.results[i].isFinal) {
        fullFinal += event.results[i][0].transcript;
      } else {
        interim += event.results[i][0].transcript;
      }
    }

    if (fullFinal !== _committedFinal) {
      _committedFinal = fullFinal;
      if (_committedFinal && onResult) onResult(_committedFinal.trim(), true);
    } else if (interim && onResult) {
      onResult(interim.trim(), false);
    }
  };

  _recognition.onend = () => {
    if (onEnd) onEnd();
  };

  _recognition.onerror = (event) => {
    console.error("[Voice] Erro de reconhecimento:", event.error);
    if (onError) onError(event.error);
    if (onEnd) onEnd();
  };

  _recognition.start();
  return true;
}

function stopVoice() {
  if (_recognition) {
    _recognition.stop();
    _recognition = null;
  }
}

function isVoiceSupported() {
  return !!(window.SpeechRecognition || window.webkitSpeechRecognition);
}
