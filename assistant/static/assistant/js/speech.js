/**
 * Thin wrapper around the browser's Web Speech API (SpeechRecognition +
 * SpeechSynthesis). Works in Chrome/Edge; other browsers fall back
 * gracefully to text-only input.
 */
(function () {
  const SpeechRecognitionImpl = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognizer = null;
  let onResultCallback = null;
  let onStateChangeCallback = null;

  function supported() {
    return !!SpeechRecognitionImpl;
  }

  function init() {
    if (!supported()) return;
    recognizer = new SpeechRecognitionImpl();
    recognizer.lang = "en-US";
    recognizer.continuous = false;
    recognizer.interimResults = false;

    recognizer.onstart = () => onStateChangeCallback && onStateChangeCallback("listening");
    recognizer.onend = () => onStateChangeCallback && onStateChangeCallback("idle");
    recognizer.onerror = () => onStateChangeCallback && onStateChangeCallback("idle");

    recognizer.onresult = (event) => {
      const text = event.results[0][0].transcript;
      onResultCallback && onResultCallback(text);
    };
  }

  function start(onResult, onStateChange) {
    if (!supported()) {
      alert("Speech recognition isn't supported in this browser. Try Chrome or Edge.");
      return;
    }
    onResultCallback = onResult;
    onStateChangeCallback = onStateChange;
    if (!recognizer) init();
    try {
      recognizer.start();
    } catch (e) {
      // already running - ignore
    }
  }

  function speak(text) {
    if (!("speechSynthesis" in window) || !text) return;
    window.speechSynthesis.cancel();
    const utter = new SpeechSynthesisUtterance(text);
    utter.rate = 1.02;
    utter.pitch = 1.0;
    window.speechSynthesis.speak(utter);
  }

  window.MindMeshSpeech = { supported, start, speak };
})();
