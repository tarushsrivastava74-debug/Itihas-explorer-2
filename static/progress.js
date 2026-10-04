// static/progress.js
// Shared by roadmap.html and timeline.html.
// Handles: login with a unique ID, loading progress, saving progress (all via the Flask API).

const ItihasProgress = (() => {
  let completedCache = null;
  let loginPromise = null;

  async function request(url, options = {}) {
    const res = await fetch(url, {
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    let data = null;
    try { data = await res.json(); } catch (e) { /* no JSON body */ }
    return { ok: res.ok, status: res.status, data };
  }

  // ---------- header user pill ----------
  // Fallback look for the header user pill. :where() has zero specificity, so any page
  // that already defines its own .user-pill / .user-avatar / .user-name styles keeps them.
  function injectPillStyles() {
    if (document.getElementById("itihas-pill-styles")) return;
    const style = document.createElement("style");
    style.id = "itihas-pill-styles";
    style.textContent =
      ":where(.header-user){display:flex;align-items:center;gap:14px;}" +
      ":where(.theme-pill){white-space:nowrap;flex:0 0 auto;}" +
      ":where(.user-pill){display:flex;align-items:center;gap:8px;}" +
      ":where(.user-avatar){width:28px;height:28px;border-radius:50%;flex:0 0 auto;" +
      "background:linear-gradient(135deg,#f59e0b,#ef4444);color:#fff;font-size:11px;font-weight:800;" +
      "display:flex;align-items:center;justify-content:center;}" +
      ":where(.user-name){font-size:12px;font-weight:600;white-space:nowrap;color:inherit;}";
    document.head.appendChild(style);
  }

  // Pages without a header user pill (e.g. mysteries.html) get a small floating badge
  function createFloatingBadge() {
    const pill = document.createElement("div");
    pill.className = "user-pill";
    pill.style.cssText =
      "position:fixed;top:12px;right:12px;z-index:9999;display:flex;align-items:center;gap:8px;" +
      "padding:6px 14px 6px 6px;border-radius:999px;background:rgba(20,20,31,0.85);" +
      "border:1px solid rgba(255,153,51,0.5);color:#fff;font:600 13px system-ui,sans-serif;" +
      "backdrop-filter:blur(6px);";
    pill.innerHTML =
      '<div class="user-avatar" style="width:26px;height:26px;border-radius:50%;background:#ff9933;' +
      'color:#000;display:flex;align-items:center;justify-content:center;font-weight:700;"></div>' +
      '<span class="user-name"></span>';
    document.body.appendChild(pill);
  }

  function showUser(user) {
    injectPillStyles();
    if (!document.querySelector(".user-name")) createFloatingBadge();
    const nameEl = document.querySelector(".user-name");
    const avatarEl = document.querySelector(".user-avatar");
    if (nameEl) nameEl.textContent = user.name || user.username;
    if (avatarEl) avatarEl.textContent = (user.name || user.username || "?").charAt(0).toUpperCase();

    const pill = document.querySelector(".user-pill");
    if (pill) {
      pill.style.cursor = "pointer";
      pill.title = "Click to switch ID";
      pill.onclick = async () => {
        if (confirm("Switch to a different ID?")) {
          await request("/api/logout", { method: "POST" });
          location.reload();
        }
      };
    }
  }

  // ---------- login popup ----------
  function showLoginModal() {
    return new Promise((resolve) => {
      const overlay = document.createElement("div");
      overlay.style.cssText =
        "position:fixed;inset:0;z-index:99999;display:flex;align-items:center;justify-content:center;" +
        "background:rgba(5,5,10,0.88);backdrop-filter:blur(6px);font-family:inherit;";

      overlay.innerHTML = `
        <div style="width:min(92vw,400px);background:#14141f;border:1px solid rgba(255,153,51,0.45);
                    border-radius:16px;padding:28px;color:#fff;box-shadow:0 20px 60px rgba(0,0,0,0.6);">
          <h2 style="margin:0 0 6px;font-size:1.3rem;">Welcome to Itihas Explorer</h2>
          <p style="margin:0 0 18px;color:#a0a0b0;font-size:0.9rem;line-height:1.5;">
            Enter your unique ID. Use the same ID next time to see your saved progress.
          </p>
          <input id="itihas-id-input" type="text" maxlength="50" autocomplete="off"
                 placeholder="e.g. tejas_01"
                 style="width:100%;box-sizing:border-box;padding:12px 14px;border-radius:10px;
                        border:1px solid rgba(255,255,255,0.2);background:#0b0b14;color:#fff;font-size:1rem;outline:none;">
          <div id="itihas-id-error" style="min-height:18px;margin-top:8px;color:#ff6b6b;font-size:0.82rem;"></div>
          <button id="itihas-id-btn"
                  style="width:100%;margin-top:10px;padding:12px;border:none;border-radius:10px;cursor:pointer;
                         background:linear-gradient(135deg,#ff9933,#e67e00);color:#000;font-weight:700;font-size:1rem;">
            Continue
          </button>
        </div>`;
      document.body.appendChild(overlay);

      const input = overlay.querySelector("#itihas-id-input");
      const errorBox = overlay.querySelector("#itihas-id-error");
      const button = overlay.querySelector("#itihas-id-btn");
      input.focus();

      async function submit() {
        errorBox.textContent = "";
        const username = input.value.trim();
        if (!username) { errorBox.textContent = "Please enter your ID."; return; }

        button.disabled = true;
        const r = await request("/api/login", {
          method: "POST",
          body: JSON.stringify({ username }),
        });
        button.disabled = false;

        if (!r.ok) {
          errorBox.textContent = (r.data && r.data.error) || "Login failed. Try again.";
          return;
        }
        overlay.remove();
        resolve(r.data);
      }

      button.addEventListener("click", submit);
      input.addEventListener("keydown", (e) => { if (e.key === "Enter") submit(); });
    });
  }

  // ---------- one-time move of old localStorage ticks into the database ----------
  async function migrateOldLocalProgress() {
    let old = [];
    try { old = JSON.parse(localStorage.getItem("itihas_completed_topics")) || []; } catch (e) { /* ignore */ }
    if (!Array.isArray(old) || old.length === 0) return;

    for (const id of old) {
      await request("/api/progress/" + encodeURIComponent(id), { method: "POST" });
    }
    localStorage.removeItem("itihas_completed_topics");
    completedCache = null;
  }

  // ---------- public API ----------
  function ensureLogin() {
    if (!loginPromise) {
      loginPromise = (async () => {
        const me = await request("/api/me");
        const user = me.ok ? me.data : await showLoginModal();
        showUser(user);
        await migrateOldLocalProgress();
        return user;
      })().catch((err) => { loginPromise = null; throw err; });
    }
    return loginPromise;
  }

  async function getCompleted(retried = false) {
    await ensureLogin();
    if (completedCache) return completedCache;

    const r = await request("/api/progress");
    if (r.status === 401 && !retried) {  // session expired -> ask for ID again
      loginPromise = null;
      return getCompleted(true);
    }
    completedCache = r.ok ? r.data.completed : [];
    return completedCache;
  }

  async function markDone(topicId) {
    await ensureLogin();
    const r = await request("/api/progress/" + encodeURIComponent(topicId), { method: "POST" });
    if (!r.ok) throw new Error((r.data && r.data.error) || "Could not save progress");
    if (completedCache && !completedCache.includes(topicId)) completedCache.push(topicId);
  }

  async function unmarkDone(topicId) {
    await ensureLogin();
    const r = await request("/api/progress/" + encodeURIComponent(topicId), { method: "DELETE" });
    if (!r.ok) throw new Error((r.data && r.data.error) || "Could not update progress");
    if (completedCache) completedCache = completedCache.filter((id) => id !== topicId);
  }

  return { ensureLogin, getCompleted, markDone, unmarkDone };
})();