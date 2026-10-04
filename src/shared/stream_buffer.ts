// Buffer del stream de narrativa: texto recibido que todavia no esta en el
// estado. Es logica pura a proposito (sin React, sin refs, sin red) porque es
// la parte con estado COMPARTIDO entre intentos de una misma sesion, y la clase
// de bug que solo aparece en pantalla: el buffer es el mismo para el intento
// A y el B, asi que si nadie lo limpia al PARAR un intento, la narrativa
// cancelada del A aparece pegada delante de la del B. `discard()` existe justo
// para eso y la tiene que llamar quien detiene el intento, no el `finally` de
// handleSendPrompt (el buffer ya es del intento vigente para entonces).
export interface StreamBuffer {
  /** Acumula un delta. No escribe nada todavia: agrupa. */
  push(chunk: string): void;
  /** Vuelca lo pendiente al sink de una vez. Noop si no hay nada. */
  flush(): void;
  /** Tira buffer y temporizador: lo pendiente nunca llega al sink. */
  discard(): void;
}

export function createStreamBuffer(flushMs: number, sink: (text: string) => void): StreamBuffer {
  let buffer = '';
  let timer: ReturnType<typeof setTimeout> | null = null;

  const stopTimer = () => {
    if (timer !== null) {
      clearTimeout(timer);
      timer = null;
    }
  };

  const flush = () => {
    stopTimer();
    const pending = buffer;
    buffer = '';
    if (pending) sink(pending);
  };

  return {
    push(chunk: string) {
      if (!chunk) return;
      buffer += chunk;
      // Un volcado por ventana, no uno por token: los deltas llegan token a
      // token y escribir cada uno es un render por token.
      if (timer === null) {
        timer = setTimeout(flush, flushMs);
      }
    },
    flush,
    discard() {
      stopTimer();
      buffer = '';
    },
  };
}