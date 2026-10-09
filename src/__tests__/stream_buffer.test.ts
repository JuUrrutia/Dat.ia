import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createStreamBuffer, type StreamBuffer } from '../shared/stream_buffer';

// Cubre el bug del buffer de stream COMPARTIDO entre intentos: el deltas del
// intento cancelado se pegaban delante del siguiente. El mecanismo es el
// `discard()` que llama quien PARA el intento (handleCancelPrompt /
// handleNewThread), no el `finally` de handleSendPrompt.
//
// ponytail: `node` puro, sin renderizar el hook. El hook depende de useAuth,
// useNotifications, SSE y refs de navegador; reproducirlo exigiria un harness de
// mocks mas caro que el bug. La logica con estado temporal compartida vive en
// `shared/stream_buffer` y se prueba aqui.
describe('stream buffer compartido entre intentos', () => {
  let narrative: string[];
  let buffer: StreamBuffer;

  beforeEach(() => {
    vi.useFakeTimers();
    narrative = [];
    buffer = createStreamBuffer(80, (text) => {
      narrative.push(text);
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('agrupa los deltas en un solo volcado por ventana', () => {
    buffer.push('Hola');
    buffer.push(' mu');
    buffer.push('ndo');
    expect(narrative).toEqual([]); // todavia nada escrito

    vi.advanceTimersByTime(80);
    expect(narrative).toEqual(['Hola mundo']);
  });

  it('descartar tras un intento deja el buffer limpio para el siguiente', () => {
    // Intento A: llega narrativa y el usuario cancela (Ctrl+N) antes de que
    // venza la ventana de volcado.
    buffer.push('narrativa del intento A');
    vi.advanceTimersByTime(40);
    buffer.discard();

    // Intento B: escribe en el MISMO buffer compartido.
    buffer.push('narrativa del intento B');
    vi.advanceTimersByTime(80);

    // Sin el discard, el primer volcado seria 'narrativa del intento Anarrativa
    // del intento B'.
    expect(narrative).toEqual(['narrativa del intento B']);
  });

  it('descartar cancela el temporizador pendiente', () => {
    buffer.push('A');
    buffer.discard();
    // El timer del intento A no puede revivir 80 ms despues.
    vi.advanceTimersByTime(500);
    expect(narrative).toEqual([]);
  });

  it('volcar a mano entrega lo pendiente y cancela el temporizador', () => {
    buffer.push('parcial');
    buffer.flush();
    expect(narrative).toEqual(['parcial']);

    // El temporizador ya no debe escribir nada extra.
    vi.advanceTimersByTime(500);
    expect(narrative).toEqual(['parcial']);
  });

  it('volcar sin nada pendiente es noop', () => {
    buffer.flush();
    vi.advanceTimersByTime(500);
    expect(narrative).toEqual([]);
  });

  it('ignora deltas vacios', () => {
    buffer.push('');
    vi.advanceTimersByTime(80);
    expect(narrative).toEqual([]);
  });
});