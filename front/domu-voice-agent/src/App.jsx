import { useState, useRef, useEffect } from "react";

function App() {
  const [recording, setRecording] = useState(false);
  const [loading, setLoading] = useState(false);
  const [wsStatus, setWsStatus] = useState("disconnected");
  const [lastReply, setLastReply] = useState(null);
  const [error, setError] = useState(null);
  const [isPlaying, setIsPlaying] = useState(false); // speaking animation state
  const [hasPlayedIntro, setHasPlayedIntro] = useState(false);
  const [phone, setPhone] = useState("");
  const [leadName, setLeadName] = useState("");
  const [leadId, setLeadId] = useState(null);

  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const audioRef = useRef(null); // reference to audio element

  // Helper to stop agent audio if playing
  const stopAgentAudioIfPlaying = () => {
    const audio = audioRef.current;
    if (audio && !audio.paused) {
      audio.pause();
      audio.currentTime = 0;
      setIsPlaying(false);
    }
  };

  // ---------- Play intro message from backend ----------
  // comments in English only
  const playIntro = async () => {
    if (loading || recording || hasPlayedIntro) return;
    if (!phone.trim()) {
      setError("Por favor ingresa un número de teléfono.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await fetch(
        `http://localhost:8000/intro?phone=${encodeURIComponent(phone.trim())}`
      );
      if (!res.ok) {
        throw new Error("Intro request failed");
      }
      const data = await res.json();

      setLeadId(data.leadId);
      setLeadName(data.leadName);

      setLastReply({
        type: "reply",
        userText: "",
        intent: "INTRO",
        replyText: data.text,
        audioUrl: data.audioUrl,
      });
      setHasPlayedIntro(true);
    } catch (err) {
      console.error(err);
      setError(
        "No se pudo reproducir el mensaje inicial (¿teléfono correcto?)."
      );
    } finally {
      setLoading(false);
    }
  };

  // ---------- Send audio blob to backend ----------
  const sendBlobToAgent = async (blob) => {
    setLoading(true);
    setError(null);
    setLastReply((prev) => prev); // keep intro visible until new reply

    try {
      const arrayBuffer = await blob.arrayBuffer();
      const ws = new WebSocket(
        `ws://localhost:8000/ws/voice${leadId ? `?lead_id=${leadId}` : ""}`
      );
      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        setWsStatus("connected");
        ws.send(arrayBuffer);
      };

      ws.onerror = (e) => {
        console.error("WS error", e);
        setError("Error en la conexión WebSocket.");
        setWsStatus("error");
        setLoading(false);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "error") {
            setError(data.detail || data.message || "Error en el backend.");
          } else {
            setLastReply(data);
          }
        } catch (err) {
          console.error("Invalid JSON from WS:", err);
          setError("Respuesta inválida del backend.");
        } finally {
          setLoading(false);
          ws.close();
          setWsStatus("disconnected");
        }
      };
    } catch (err) {
      console.error(err);
      setError("Error preparando el audio para enviar.");
      setLoading(false);
    }
  };

  // ---------- Push-to-talk recording ----------
  const startRecording = async () => {
    if (recording || loading) return;
    try {
      setError(null);

      // ⛔ DETENER AUDIO DEL AGENTE SI ESTÁ HABLANDO
      stopAgentAudioIfPlaying();

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = "audio/webm;codecs=opus";
      const mr = new MediaRecorder(stream, { mimeType });

      chunksRef.current = [];

      mr.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      mr.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: "audio/webm" });
        // stop tracks to release mic
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        // auto-send to agent
        if (blob.size > 0) {
          sendBlobToAgent(blob);
        } else {
          setError("El audio grabado está vacío.");
        }
      };

      mediaRecorderRef.current = mr;
      mr.start();
      setRecording(true);
    } catch (err) {
      console.error(err);
      setError("No se pudo acceder al micrófono.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && recording) {
      mediaRecorderRef.current.stop();
    }
  };

  // Mouse/touch handlers for push-to-talk
  const handlePressStart = (e) => {
    e.preventDefault();
    startRecording();
  };

  const handlePressEnd = (e) => {
    e.preventDefault();
    stopRecording();
  };

  // ---------- Spacebar push-to-talk ----------
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.code === "Space" || e.key === " ") {
        e.preventDefault();
        // Avoid retrigger when held
        if (!recording && !loading && hasPlayedIntro) {
          startRecording();
        }
      }
    };

    const handleKeyUp = (e) => {
      if (e.code === "Space" || e.key === " ") {
        e.preventDefault();
        if (recording) {
          stopRecording();
        }
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [recording, loading, hasPlayedIntro]);

  // ---------- Autoplay and speaking animation ----------
  useEffect(() => {
    if (!lastReply || !lastReply.audioUrl || !audioRef.current || recording) return;

    const audio = audioRef.current;

    const handleEnded = () => setIsPlaying(false);
    const handlePause = () => setIsPlaying(false);

    audio.addEventListener("ended", handleEnded);
    audio.addEventListener("pause", handlePause);

    const playAudio = async () => {
      try {
        audio.currentTime = 0;
        setIsPlaying(true);
        await audio.play();
      } catch (err) {
        console.error("Autoplay failed:", err);
        setIsPlaying(false);
      }
    };

    playAudio();

    return () => {
      audio.removeEventListener("ended", handleEnded);
      audio.removeEventListener("pause", handlePause);
    };
  }, [lastReply]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#050816",
        color: "#E5E7EB",
        fontFamily: "system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
        padding: "2rem",
      }}
    >
      <div style={{ maxWidth: 800, margin: "0 auto" }}>
        <h1
          style={{
            fontSize: "2.4rem",
            fontWeight: 800,
            marginBottom: "0.5rem",
          }}
        >
          🎙️ Domu Voice Agent — Walkie Talkie
        </h1>
        <p style={{ marginBottom: "1.5rem", color: "#9CA3AF" }}>
          Primero escucha el mensaje inicial del agente, luego mantén presionado
          el botón (o la tecla <b>Espacio</b>) para hablar. Al soltar, tu
          mensaje se envía automáticamente.
        </p>

        {/* Intro button */}
        <div
          style={{
            background: "#111827",
            borderRadius: "1rem",
            padding: "1.5rem",
            marginBottom: "1.5rem",
            border: "1px solid #1F2937",
          }}
        >
          <h2 style={{ fontSize: "1.2rem", marginBottom: "0.75rem" }}>
            ☎️ Iniciar llamada
          </h2>

          <div style={{ marginBottom: "0.75rem" }}>
            <label
              style={{
                display: "block",
                fontSize: "0.9rem",
                color: "#9CA3AF",
                marginBottom: "0.25rem",
              }}
            >
              Número de teléfono del cliente
            </label>
            <input
              type="text"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="Ej: 3001234567"
              style={{
                width: "100%",
                padding: "0.5rem 0.75rem",
                borderRadius: "0.5rem",
                border: "1px solid #374151",
                background: "#020617",
                color: "#E5E7EB",
                fontSize: "0.95rem",
              }}
            />
          </div>

          <button
            onClick={playIntro}
            disabled={loading || hasPlayedIntro || !phone.trim()}
            style={{
              padding: "0.7rem 1.8rem",
              borderRadius: "999px",
              border: "none",
              background:
                hasPlayedIntro || !phone.trim() ? "#1F2937" : "#2563EB",
              color: hasPlayedIntro || !phone.trim() ? "#9CA3AF" : "white",
              fontWeight: 600,
              cursor:
                hasPlayedIntro || !phone.trim() ? "not-allowed" : "pointer",
              marginRight: "0.75rem",
            }}
          >
            {hasPlayedIntro ? "Llamada iniciada" : "Reproducir mensaje inicial"}
          </button>
          <span style={{ fontSize: "0.9rem", color: "#9CA3AF" }}>
            {leadName
              ? `El agente saludará a ${leadName}.`
              : "El agente saludará al cliente según la información del teléfono."}
          </span>
        </div>

        {/* Push-to-talk button */}
        <div
          style={{
            background: "#111827",
            borderRadius: "1rem",
            padding: "1.5rem",
            marginBottom: "1.5rem",
            border: "1px solid #1F2937",
            textAlign: "center",
            opacity: hasPlayedIntro ? 1 : 0.6,
          }}
        >
          <h2 style={{ fontSize: "1.2rem", marginBottom: "0.75rem" }}>
            🎛️ Push-to-Talk
          </h2>

          <button
            onMouseDown={handlePressStart}
            onMouseUp={handlePressEnd}
            onMouseLeave={recording ? handlePressEnd : undefined}
            onTouchStart={handlePressStart}
            onTouchEnd={handlePressEnd}
            disabled={loading || !hasPlayedIntro}
            style={{
              padding: "1rem 2.5rem",
              borderRadius: "999px",
              border: "none",
              background:
                !hasPlayedIntro || loading
                  ? "#1F2937"
                  : recording
                  ? "#DC2626"
                  : "#16A34A",
              boxShadow:
                recording && hasPlayedIntro
                  ? "0 0 20px rgba(239,68,68,0.7)"
                  : hasPlayedIntro
                  ? "0 0 12px rgba(34,197,94,0.6)"
                  : "none",
              color: "white",
              fontWeight: 700,
              fontSize: "1.1rem",
              cursor: loading || !hasPlayedIntro ? "not-allowed" : "pointer",
              transition:
                "transform 0.1s ease, box-shadow 0.1s ease, background 0.1s",
            }}
          >
            {recording
              ? "Suelta para enviar..."
              : "Mantén presionado para hablar (o usa Espacio)"}
          </button>

          <p
            style={{
              marginTop: "0.75rem",
              fontSize: "0.9rem",
              color: "#9CA3AF",
            }}
          >
            Estado:{" "}
            <strong>
              {loading
                ? "Enviando al agente..."
                : recording
                ? "Grabando"
                : "Listo para escuchar"}
            </strong>
          </p>

          <p
            style={{
              marginTop: "0.25rem",
              fontSize: "0.85rem",
              color: "#6B7280",
            }}
          >
            WebSocket: <strong>{wsStatus}</strong>
          </p>
        </div>

        {/* Error */}
        {error && (
          <div
            style={{
              background: "#7F1D1D",
              borderRadius: "0.75rem",
              padding: "0.75rem 1rem",
              marginBottom: "1rem",
              color: "#FECACA",
            }}
          >
            ⚠️ {error}
          </div>
        )}

        {/* Reply card */}
        {lastReply && lastReply.type !== "error" && (
          <div
            style={{
              background: "#111827",
              borderRadius: "1rem",
              padding: "1.5rem",
              border: "1px solid #1F2937",
              marginTop: "1rem",
            }}
          >
            <h2 style={{ fontSize: "1.2rem", marginBottom: "1rem" }}>
              🤖 Respuesta del agente
            </h2>

            {/* Speaking mini animation */}
            <div
              style={{
                marginBottom: "0.75rem",
                display: "flex",
                gap: "0.5rem",
                alignItems: "center",
              }}
            >
              <div style={{ fontSize: "0.9rem", color: "#9CA3AF" }}>
                Estado de voz del agente:
              </div>
              {isPlaying ? (
                <div className="speaking-indicator">
                  <span className="speaking-bar" />
                  <span className="speaking-bar" />
                  <span className="speaking-bar" />
                </div>
              ) : (
                <span style={{ fontSize: "0.85rem", color: "#6B7280" }}>
                  En silencio
                </span>
              )}
            </div>

            <div style={{ marginBottom: "0.75rem" }}>
              <div style={{ fontSize: "0.9rem", color: "#9CA3AF" }}>
                Transcripción del usuario:
              </div>
              <div>{lastReply.userText || "—"}</div>
            </div>

            <div style={{ marginBottom: "0.75rem" }}>
              <div style={{ fontSize: "0.9rem", color: "#9CA3AF" }}>
                Intención detectada:
              </div>
              <code
                style={{
                  background: "#020617",
                  padding: "0.2rem 0.5rem",
                  borderRadius: "0.4rem",
                  fontSize: "0.85rem",
                }}
              >
                {lastReply.intent || "NEUTRAL"}
              </code>
            </div>

            <div style={{ marginBottom: "0.75rem" }}>
              <div style={{ fontSize: "0.9rem", color: "#9CA3AF" }}>
                Texto del agente:
              </div>
              <div>{lastReply.replyText || "—"}</div>
            </div>

            {lastReply.audioUrl && (
              <div>
                <audio
                  ref={audioRef}
                  src={lastReply.audioUrl}
                  controls
                  style={{ marginTop: "0.5rem", width: "100%" }}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
