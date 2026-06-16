/**
 * Componente de entrada por voz via Web Speech API.
 *
 * Reconhecimento em português (pt-BR) com resultados intermediários para
 * feedback em tempo real. No desktop usa modo contínuo; no celular o modo
 * contínuo é desligado (ver startVoice) para evitar a duplicação de fala
 * do Chrome no Android.
 */
let _recognition = null;

/**
 * Detecta se o dispositivo é móvel (celular/tablet).
 *
 * Usado para desligar o modo contínuo do reconhecimento: o Chrome no Android,
 * com continuous=true, re-finaliza o mesmo enunciado e o acumula em
 * event.results, fazendo a fala ser repetida várias vezes. Com continuous=false
 * o enunciado é finalizado uma única vez.
 *
 * Returns:
 *     true se for um dispositivo móvel, false caso contrário.
 */
function isMobileDevice() {
  if (navigator.userAgentData && typeof navigator.userAgentData.mobile === "boolean") {
    return navigator.userAgentData.mobile;
  }
  return /Android|iPhone|iPad|iPod|Mobi/i.test(navigator.userAgent);
}

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
  // No celular continuous=false: evita o Android re-finalizar o enunciado e
  // duplicar a fala. O usuário toca em VOZ a cada bloco; como o consumidor
  // anexa ao texto existente, o ditado em várias falas continua funcionando.
  _recognition.continuous = !isMobileDevice();
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
