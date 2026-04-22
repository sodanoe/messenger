import { useEffect, useRef, useState } from "react";

const PAGE_TITLE = document.title;
let _audioCtx = null;
let swReg = null;

function getAudioCtx() {
  if (!_audioCtx || _audioCtx.state === "closed")
    _audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  return _audioCtx;
}

function playNotifSound() {
  try {
    const ctx = getAudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.type = "sine";
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(660, ctx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.35);
    osc.start(ctx.currentTime);
    osc.stop(ctx.currentTime + 0.35);
  } catch {
    // intentional
  }
}

async function showBrowserNotif(title, body) {
  try {
    if (swReg) {
      await swReg.showNotification(title, {
        body,
        tag: "messenger-msg",
        silent: true,
      });
    } else {
      const n = new Notification(title, {
        body,
        tag: "messenger-msg",
        silent: true,
      });
      n.onclick = () => {
        window.focus();
        n.close();
      };
    }
  } catch {
    // intentional
  }
}

export function useNotifications() {
  const [granted, setGranted] = useState(false);
  const titleBlinkTimer = useRef(null);

  async function requestPermission() {
    if (!("Notification" in window)) return;
    if ("serviceWorker" in navigator && !swReg) {
      swReg = await navigator.serviceWorker
        .register("/sw.js")
        .catch(() => null);
    }
    if (Notification.permission === "granted") {
      setGranted(true);
      return;
    }
    if (Notification.permission !== "denied") {
      const p = await Notification.requestPermission();
      setGranted(p === "granted");
    }
  }

  function startTitleBlink(name) {
    stopTitleBlink();
    let on = true;
    titleBlinkTimer.current = setInterval(() => {
      document.title = on ? `💬 ${name}` : PAGE_TITLE;
      on = !on;
    }, 900);
  }

  function stopTitleBlink() {
    if (titleBlinkTimer.current) {
      clearInterval(titleBlinkTimer.current);
      titleBlinkTimer.current = null;
    }
    document.title = PAGE_TITLE;
  }

  function notifyUser(fromName, content) {
    playNotifSound();
    if (document.hidden) startTitleBlink(fromName);
    if (granted) showBrowserNotif(`💬 ${fromName}`, content.slice(0, 100));
  }

  useEffect(() => {
    const stop = () => stopTitleBlink();
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) stop();
    });
    window.addEventListener("focus", stop);
    return () => {
      document.removeEventListener("visibilitychange", stop);
      window.removeEventListener("focus", stop);
      stopTitleBlink();
    };
  }, []);

  return { notifyUser, requestPermission, granted };
}
