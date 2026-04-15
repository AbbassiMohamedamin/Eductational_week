(() => {
  const defaultChildId = window.ASSISTANT_CHAT_CHILD_ID || 'child_001';
  const defaultGreeting = window.ASSISTANT_CHAT_GREETING || "Hello! I'm your safety assistant. How can I help you today?";
  const autoPlayVoice = window.ASSISTANT_CHAT_AUTO_PLAY !== false;

  const state = {
    messagesEl: null,
    inputEl: null,
    sendBtn: null,
    recordBtn: null,
    typingEl: null,
    debugLogEl: null,
    debugBadgeEl: null,
    containerEl: null,
    mediaRecorder: null,
    audioChunks: [],
    recording: false,
    initDone: false,
  };

  const escapeHtml = (value) => String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

  const scrollToBottom = () => {
    if (!state.messagesEl) return;
    state.messagesEl.scrollTop = state.messagesEl.scrollHeight;
  };

  const setTyping = (visible) => {
    if (!state.typingEl) return;
    state.typingEl.classList.toggle('hidden', !visible);
  };

  const setDebugBadge = (label, kind = 'idle') => {
    if (!state.debugBadgeEl) return;

    state.debugBadgeEl.textContent = label;
    state.debugBadgeEl.className = 'text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded-full';

    if (kind === 'active') {
      state.debugBadgeEl.classList.add('bg-secondary', 'text-white');
    } else if (kind === 'error') {
      state.debugBadgeEl.classList.add('bg-error', 'text-white');
    } else if (kind === 'success') {
      state.debugBadgeEl.classList.add('bg-primary', 'text-white');
    } else {
      state.debugBadgeEl.classList.add('bg-surface-container-low', 'text-on-surface-variant');
    }
  };

  const pushDebug = (message) => {
    if (!state.debugLogEl) return;

    if (state.debugLogEl.querySelector('p.italic')) {
      state.debugLogEl.innerHTML = '';
    }

    const line = document.createElement('p');
    line.className = 'rounded-lg bg-surface-container-low px-3 py-2 border border-outline-variant/20';
    line.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;
    state.debugLogEl.prepend(line);
  };

  const speakWithBrowser = (text) => {
    if (!('speechSynthesis' in window) || !text) return false;

    try {
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = 'ar-SA';
      utterance.rate = 0.95;
      utterance.pitch = 1.0;

      const voices = window.speechSynthesis.getVoices();
      const arabicVoice = voices.find((v) => (v.lang || '').toLowerCase().startsWith('ar'));
      if (arabicVoice) {
        utterance.voice = arabicVoice;
      }

      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
      return true;
    } catch (error) {
      console.error('Browser TTS fallback error:', error);
      return false;
    }
  };

  const appendMessage = (role, text, audioUrl = null) => {
    if (!state.messagesEl) return null;

    const isUser = role === 'user';
    const message = document.createElement('div');
    message.className = `p-3 rounded-xl max-w-[85%] ${isUser
      ? 'bg-secondary text-white self-end ml-auto'
      : 'bg-primary-container/10 border border-primary/10 text-on-surface self-start mr-auto'}`;

    const safeText = escapeHtml(text ?? '');
    message.innerHTML = `
      <p class="font-bold text-[10px] mb-1 opacity-70 uppercase tracking-widest">${isUser ? 'You' : 'Assistant'}</p>
      <p class="leading-relaxed">${safeText}</p>
      ${audioUrl ? `<button type="button" data-audio-url="${escapeHtml(audioUrl)}" class="mt-2 flex items-center gap-1 text-[10px] font-bold bg-white/20 px-2 py-1 rounded-full hover:bg-white/30 transition-colors"><span class="material-symbols-outlined text-sm">play_circle</span>Play Response</button>` : ''}
    `;

    const audioButton = message.querySelector('[data-audio-url]');
    if (audioButton) {
      audioButton.addEventListener('click', () => {
        const url = audioButton.getAttribute('data-audio-url');
        if (url) {
          new Audio(url).play().catch(() => {});
        }
      });
    }

    state.messagesEl.appendChild(message);
    scrollToBottom();
    return message;
  };

  const setRecordingState = (recording) => {
    state.recording = recording;
    if (!state.recordBtn) return;

    if (recording) {
      state.recordBtn.classList.add('bg-error', 'text-white', 'animate-pulse');
      state.recordBtn.innerHTML = '<span class="material-symbols-outlined">stop_circle</span>';
    } else {
      state.recordBtn.classList.remove('bg-error', 'text-white', 'animate-pulse');
      state.recordBtn.innerHTML = '<span class="material-symbols-outlined">mic</span>';
    }
  };

  const sendChatMessage = async (text = null, audioData = null) => {
    if (!text && !audioData) return;

    window.chatStartTime = Date.now();
    const outgoingText = text ? text.trim() : '';
    if (!outgoingText && !audioData) return;

    if (audioData) {
      pushDebug('Audio blob captured and sent to backend.');
      setDebugBadge('Sending', 'active');
      pushDebug('Waiting for Whisper transcription...');
    }

    if (outgoingText) {
      appendMessage('user', outgoingText);
      if (state.inputEl) state.inputEl.value = '';
    } else {
      appendMessage('user', '🎤 Voice Message');
    }

    setTyping(true);

    try {
      const response = await fetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text_input: outgoingText || null,
          audio_data: audioData,
          child_id: defaultChildId,
        }),
      });

      const payload = await response.json();
      setTyping(false);

      if (!response.ok) {
        throw new Error(payload?.detail || payload?.error || 'Chat request failed');
      }

      pushDebug(`Backend returned: transcript=${payload.transcript ? 'yes' : 'no'}, voice_url=${payload.voice_url ? 'yes' : 'no'}, tts_model=${payload.tts_model || 'n/a'}`);

      if (payload.transcript && audioData) {
        pushDebug(`Whisper transcript received: ${payload.transcript}`);
        const lastUserMessage = state.messagesEl?.lastElementChild;
        if (lastUserMessage && lastUserMessage.innerText.includes('Voice Message')) {
          const bodyParagraph = lastUserMessage.querySelector('p:nth-child(2)');
          if (bodyParagraph) {
            bodyParagraph.innerText = `🎤 ${payload.transcript}`;
          }
        }
      }

      const responseText = payload.analysis || 'I could not generate a reply.';
      appendMessage('assistant', responseText, payload.voice_url || null);

      // Record to Communication History
      if (typeof window.recordChatMessage === 'function') {
        const inputText = outgoingText || (audioData ? '🎤 Voice Message' : '');
        const latency = Date.now() - (window.chatStartTime || Date.now());
        window.recordChatMessage(inputText, responseText, 'Jais LLM', latency);
      }

      if (payload.voice_url && autoPlayVoice) {
        setDebugBadge('Playing', 'success');
        pushDebug(`TTS generated. Playing audio from ${payload.voice_url}`);
        new Audio(payload.voice_url).play().catch((playError) => {
          console.error('Audio playback error:', playError);
          setDebugBadge('Autoplay blocked', 'error');
          pushDebug(`Browser autoplay blocked: ${playError?.message || playError}`);
          appendMessage('assistant', 'I generated a voice file, but the browser did not autoplay it. Click the Listen button on the response or check browser audio permissions.');
        });
      } else if (payload.tts_error) {
        setDebugBadge('TTS error', 'error');
        pushDebug(`TTS failed: ${payload.tts_error}`);
        appendMessage('assistant', `TTS failed: ${payload.tts_error}`);

        const browserFallbackWorked = speakWithBrowser(payload.analysis || '');
        if (browserFallbackWorked) {
          setDebugBadge('Browser TTS', 'success');
          pushDebug('Groq TTS unavailable, browser speech synthesis fallback started.');
          appendMessage('assistant', 'Groq TTS is unavailable for this model right now. I am using browser voice fallback.');
        } else {
          pushDebug('Browser speech synthesis fallback unavailable in this browser.');
        }
      } else {
        setDebugBadge('Idle', 'idle');
      }
    } catch (error) {
      console.error('Assistant chat error:', error);
      setTyping(false);
      setDebugBadge('Error', 'error');
      pushDebug(`Chat error: ${error?.message || error}`);
      appendMessage('assistant', 'Sorry, I encountered an error. Please try again.');
    }
  };

  const toggleRecording = async () => {
    if (state.recording) {
      if (state.mediaRecorder && state.mediaRecorder.state !== 'inactive') {
        state.mediaRecorder.stop();
      }
      setRecordingState(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      state.mediaRecorder = new MediaRecorder(stream);
      state.audioChunks = [];
      pushDebug('Microphone permission granted. Recording started.');
      setDebugBadge('Recording', 'active');

      state.mediaRecorder.ondataavailable = (event) => {
        state.audioChunks.push(event.data);
      };

      state.mediaRecorder.onstop = () => {
        const audioBlob = new Blob(state.audioChunks, { type: 'audio/webm' });
        pushDebug(`Recording stopped. Audio blob size: ${audioBlob.size} bytes.`);
        const reader = new FileReader();
        reader.onloadend = () => {
          pushDebug('Audio blob converted to data URL.');
          sendChatMessage(null, reader.result);
        };
        reader.readAsDataURL(audioBlob);
      };

      state.mediaRecorder.start();
      setRecordingState(true);
    } catch (error) {
      console.error('Mic error:', error);
      setDebugBadge('Mic error', 'error');
      pushDebug(`Microphone access failed: ${error?.message || error}`);
      alert('Could not access microphone.');
    }
  };

  const init = () => {
    if (state.initDone) return;

    state.containerEl = document.getElementById('assistant-chat-panel') || document.getElementById('assistant-chat-shell');
    state.messagesEl = document.getElementById('chat-messages');
    state.inputEl = document.getElementById('chat-input');
    state.sendBtn = document.getElementById('btn-chat-send');
    state.recordBtn = document.getElementById('btn-chat-record');
    state.typingEl = document.getElementById('typing-indicator');
    state.debugLogEl = document.getElementById('voice-debug-log');
    state.debugBadgeEl = document.getElementById('voice-debug-badge');

    if (!state.messagesEl) return;

    state.initDone = true;

    if (!state.messagesEl.children.length) {
      appendMessage('assistant', defaultGreeting);
    }

    pushDebug('Voice debug panel ready.');
    setDebugBadge('Idle', 'idle');

    if (state.sendBtn && state.inputEl) {
      state.sendBtn.addEventListener('click', () => sendChatMessage(state.inputEl.value));
      state.inputEl.addEventListener('keypress', (event) => {
        if (event.key === 'Enter') {
          event.preventDefault();
          sendChatMessage(state.inputEl.value);
        }
      });
    }

    if (state.recordBtn) {
      state.recordBtn.addEventListener('click', toggleRecording);
    }
  };

  window.GuardianAssistantChat = {
    init,
    sendChatMessage,
    appendMessage,
    setTyping,
    pushDebug,
    setDebugBadge,
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
