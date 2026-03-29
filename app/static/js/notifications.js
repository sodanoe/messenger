// ─────────────────────────────────────────────────────────
//  Browser notifications + sound + tab blink
// ─────────────────────────────────────────────────────────

let swReg = null;  // кэшируем регистрацию SW

// Регистрируем SW и запрашиваем разрешение на уведомления за один вызов
async function requestNotifPermission() {
  if (!('Notification' in window)) return;

  // Регистрируем Service Worker — нужен Chrome для показа уведомлений
  if ('serviceWorker' in navigator && !swReg) {
    swReg = await navigator.serviceWorker.register('/sw.js').catch(() => null);
  }

  if (Notification.permission === 'granted') { notifGranted = true; return; }
  if (Notification.permission !== 'denied') {
    const p = await Notification.requestPermission();
    notifGranted = (p === 'granted');
  }
}

// Chrome требует SW для showNotification(); Firefox/Brave работают и без него
async function showBrowserNotif(title, body) {
  if (!notifGranted) return;
  try {
    if (swReg) {
      // Путь для Chrome — уведомление через SW
      await swReg.showNotification(title, { body, tag: 'messenger-msg', silent: true });
    } else {
      // Fallback: Firefox, Brave, Safari
      const n = new Notification(title, { body, tag: 'messenger-msg', silent: true });
      n.onclick = () => { window.focus(); n.close(); };
    }
  } catch(e) {}
}

function notifyUser(fromName, content) {
  playNotifSound();
  if (document.hidden) startTitleBlink(fromName);
  // Показываем уведомление всегда — браузер сам решает,
  // показывать ли поверх активной вкладки
  showBrowserNotif(`💬 ${fromName}`, content.slice(0, 100));
}

let _audioCtx = null;
function getAudioCtx() {
  if (!_audioCtx || _audioCtx.state === 'closed') _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  return _audioCtx;
}

function playNotifSound() {
  try {
    const ctx  = getAudioCtx();
    const osc  = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(660, ctx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.35);
  } catch(e) {}
}

function startTitleBlink(name) {
  stopTitleBlink();
  let on = true;
  titleBlinkTimer = setInterval(() => {
    document.title = on ? `💬 ${name}` : PAGE_TITLE;
    on = !on;
  }, 900);
}

function stopTitleBlink() {
  if (titleBlinkTimer) { clearInterval(titleBlinkTimer); titleBlinkTimer = null; }
  document.title = PAGE_TITLE;
}

document.addEventListener('visibilitychange', () => { if (!document.hidden) stopTitleBlink(); });
window.addEventListener('focus', stopTitleBlink);
