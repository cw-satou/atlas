"use strict";
(() => {
  // public/liff/src/state.ts
  var state = {
    /** 現在のUIステート */
    userState: "mode_select",
    /** ユーザー入力データ */
    formData: {},
    /** 選択中のモード */
    selectedMode: null,
    /** メッセージ表示キュー */
    messageQueue: Promise.resolve(),
    /** 診断結果 */
    divinationResult: null,
    /** 商品候補リスト */
    productCandidates: [],
    /** 選択中の商品インデックス */
    selectedProductIndex: null,
    /** ユーザーID */
    userId: null,
    /** ローディングメッセージのインデックス */
    thinkingIndex: 0
  };

  // public/liff/src/chat.ts
  function scrollChatToBottom() {
    const box = document.getElementById("chatBox");
    if (!box)
      return;
    box.scrollTop = box.scrollHeight;
  }
  function formatText(text) {
    if (!text)
      return "";
    const decoded = text.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&amp;/g, "&");
    return decoded.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  }
  function typeText(element, text, speed = 40) {
    return new Promise((resolve) => {
      const plain = text.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]*>/g, "");
      let i = 0;
      function type() {
        if (i < plain.length) {
          element.textContent = plain.slice(0, i + 1);
          i++;
          scrollChatToBottom();
          setTimeout(type, speed);
        } else {
          element.innerHTML = text;
          resolve();
        }
      }
      type();
    });
  }
  function addMsg(text, isUser = false) {
    state.messageQueue = state.messageQueue.then(() => renderMessage(text, isUser));
    return state.messageQueue;
  }
  function renderMessage(text, isUser) {
    return new Promise((resolve) => {
      const box = document.getElementById("chatBox");
      if (!box) {
        resolve();
        return;
      }
      const div = document.createElement("div");
      div.className = `msg ${isUser ? "user" : "bot"}`;
      box.appendChild(div);
      const formatted = formatText(text.replace(/\n/g, "<br>"));
      if (isUser) {
        div.innerHTML = formatted;
        scrollChatToBottom();
        resolve();
        return;
      }
      typeText(div, formatted, 40).then(() => {
        scrollChatToBottom();
        resolve();
      });
    });
  }
  function setInputArea(html) {
    const el = document.getElementById("inputArea");
    if (el)
      el.innerHTML = html;
    scrollChatToBottom();
  }
  function clearInputArea() {
    setInputArea("");
  }
  function setProgress(step, total, label) {
    const el = document.getElementById("progressBar");
    if (el) {
      el.innerHTML = `STEP ${step} / ${total}<br>${label}`;
    }
  }

  // public/liff/src/starfield.ts
  var stars = [];
  var canvas;
  var ctx;
  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  function createStars() {
    stars = [];
    for (let i = 0; i < 120; i++) {
      stars.push({
        x: Math.random() * canvas.width,
        y: Math.random() * canvas.height,
        r: Math.random() * 1.5,
        speed: Math.random() * 0.3 + 0.1
      });
    }
  }
  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "white";
    stars.forEach((star) => {
      ctx.beginPath();
      ctx.arc(star.x, star.y, star.r, 0, Math.PI * 2);
      ctx.fill();
      star.y += star.speed;
      if (star.y > canvas.height) {
        star.y = 0;
        star.x = Math.random() * canvas.width;
      }
    });
    requestAnimationFrame(animate);
  }
  function initStarfield() {
    const el = document.getElementById("starfield");
    if (!el)
      return;
    canvas = el;
    const context = canvas.getContext("2d");
    if (!context)
      return;
    ctx = context;
    window.addEventListener("resize", resize);
    resize();
    createStars();
    animate();
  }

  // public/liff/src/liff.ts
  async function initLiff() {
    try {
      await liff.init({
        liffId: "2009078638-GZhFVgaz"
      });
      if (liff.isLoggedIn()) {
        const profile = await liff.getProfile();
        window.LINE_USER_ID = profile.userId;
      }
    } catch {
      console.log("LIFF not available");
    }
  }
  function fillOrderNote() {
    const params = new URLSearchParams(window.location.search);
    const diagnosisId = params.get("d");
    if (!diagnosisId)
      return;
    const noteField = document.querySelector("#order_comments");
    if (noteField) {
      noteField.value = "diagnosis_id:" + diagnosisId;
    }
  }

  // public/liff/src/profile.ts
  var PROFILE_STORAGE_KEY = "hoshin-profile";
  function saveProfileToLocalStorage() {
    const profile = {
      name: state.formData.name,
      gender: state.formData.gender,
      birth: state.formData.birth,
      wrist_inner_cm: state.formData.wrist_inner_cm,
      bead_size_mm: state.formData.bead_size_mm,
      bracelet_type: state.formData.bracelet_type
    };
    localStorage.setItem(PROFILE_STORAGE_KEY, JSON.stringify(profile));
    if (state.userId) {
      fetch("/api/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: state.userId, ...profile })
      }).catch(() => {
      });
    }
  }
  function getUserNameForDisplay() {
    return state.formData.name && state.formData.name.trim() ? `${state.formData.name.trim()}\u3055\u3093` : "\u3042\u306A\u305F";
  }
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      return parts.pop()?.split(";").shift() || null;
    }
    return null;
  }
  function getGreetingMessage() {
    const hour = (/* @__PURE__ */ new Date()).getHours();
    const nameForDisplay = getUserNameForDisplay();
    if (hour >= 5 && hour < 11) {
      return `\u304A\u306F\u3088\u3046\u3054\u3056\u3044\u307E\u3059\u3002\u661F\u306E\u7F85\u91DD\u76E4\u300C\u3042\u3068\u3089\u3059\u300D\u3067\u3059\u3002
\u4ECA\u306E\u6C17\u5206\u3084\u3001\u3061\u3087\u3063\u3068\u6C17\u306B\u306A\u3063\u3066\u3044\u308B\u3053\u3068\u304C\u3042\u308C\u3070\u3001\u3053\u3053\u3067\u6574\u7406\u3057\u3066\u307F\u307E\u305B\u3093\u304B\uFF1F

\u3042\u306A\u305F\u306E\u304A\u8A71\u3068\u661F\u306E\u6D41\u308C\u3092\u3082\u3068\u306B\u3001\u4ECA\u306E\u3042\u306A\u305F\u306B\u5408\u3044\u305D\u3046\u306A\u77F3\u3084\u904E\u3054\u3057\u65B9\u306E\u30D2\u30F3\u30C8\u3092\u304A\u4F1D\u3048\u3057\u307E\u3059\u3002`;
    } else if (hour >= 11 && hour < 17) {
      return `\u3053\u3093\u306B\u3061\u306F\u3002\u661F\u306E\u7F85\u91DD\u76E4\u300C\u3042\u3068\u3089\u3059\u300D\u3067\u3059\u3002
\u4ED5\u4E8B\u3084\u4EBA\u9593\u95A2\u4FC2\u3001\u3053\u308C\u304B\u3089\u306E\u3053\u3068\u306A\u3069\u3001\u982D\u306E\u4E2D\u304C\u5C11\u3057\u3054\u3061\u3083\u3054\u3061\u3083\u3057\u3066\u3044\u308B\u3068\u304D\u306F\u3001\u4E00\u5EA6\u8A00\u8449\u306B\u3057\u3066\u307F\u308B\u306E\u304C\u304A\u3059\u3059\u3081\u3067\u3059\u3002

\u3044\u307E\u6C17\u306B\u306A\u3063\u3066\u3044\u308B\u3053\u3068\u3092\u6559\u3048\u3066\u3044\u305F\u3060\u3051\u308C\u3070\u3001\u661F\u306E\u914D\u7F6E\u3068\u3042\u308F\u305B\u3066\u3001\u843D\u3061\u7740\u3044\u3066\u8003\u3048\u308B\u305F\u3081\u306E\u30D2\u30F3\u30C8\u3092\u304A\u51FA\u3057\u3057\u307E\u3059\u3002`;
    } else {
      return `\u3053\u3093\u3070\u3093\u306F\u3002\u661F\u306E\u7F85\u91DD\u76E4\u300C\u3042\u3068\u3089\u3059\u300D\u3067\u3059\u3002
\u4E00\u65E5\u306E\u7D42\u308F\u308A\u306B\u3001\u5FC3\u306E\u4E2D\u3092\u5C11\u3057\u3060\u3051\u632F\u308A\u8FD4\u3063\u3066\u307F\u307E\u305B\u3093\u304B\u3002

\u3046\u307E\u304F\u8A00\u8449\u306B\u306A\u3089\u306A\u304F\u3066\u3082\u5927\u4E08\u592B\u306A\u306E\u3067\u3001\u6C17\u306B\u306A\u3063\u3066\u3044\u308B\u3053\u3068\u3084\u30E2\u30E4\u30E2\u30E4\u3057\u3066\u3044\u308B\u3053\u3068\u3092\u3001\u3053\u3053\u306B\u305D\u306E\u307E\u307E\u66F8\u3044\u3066\u307F\u3066\u304F\u3060\u3055\u3044\u3002`;
    }
  }
  function loadProfileFromLocalStorage() {
    const saved = localStorage.getItem(PROFILE_STORAGE_KEY);
    if (saved) {
      try {
        const localProfile = JSON.parse(saved);
        state.formData = { ...localProfile, ...state.formData };
      } catch {
      }
    }
  }

  // public/liff/src/fortune.ts
  async function stepTodayFortune() {
    state.selectedMode = "today_fortune";
    await addMsg(
      "\u4ECA\u65E5\u306E\u904B\u52E2\u3092\u8AAD\u3080\u305F\u3081\u306B\u3001\u751F\u5E74\u6708\u65E5\u30FB\u751F\u307E\u308C\u305F\u6642\u9593\u3068\u5834\u6240\u3092\u6559\u3048\u3066\u3044\u305F\u3060\u3051\u307E\u3059\u304B\uFF1F",
      false
    );
  }
  function submitTodayComment() {
    const textarea = document.getElementById("todayComment");
    const comment = textarea && textarea.value.trim() || "";
    if (comment) {
      addMsg(comment, true);
      state.formData.today_comment = comment;
    }
    clearInputArea();
    addMsg(
      "\u3042\u308A\u304C\u3068\u3046\u3054\u3056\u3044\u307E\u3059\u3002\n\u3067\u306F\u3001\u3053\u306E\u6D41\u308C\u3092\u8E0F\u307E\u3048\u3066\u3001\u4ECA\u65E5\u306F\u3069\u3093\u306A\u30C6\u30FC\u30DE\u306B\u3064\u3044\u3066\u8A73\u3057\u304F\u898B\u3066\u3044\u304D\u307E\u3057\u3087\u3046\u304B\uFF1F",
      false
    );
  }
  async function runTodayFortune() {
    const birth = state.formData.birth || {};
    await addMsg(
      "\u751F\u307E\u308C\u305F\u6642\u9593\u3068\u5834\u6240\u3082\u542B\u3081\u3066\u3001AI\u306B\u4ECA\u65E5\u306E\u904B\u52E2\u3092\u805E\u3044\u3066\u307F\u307E\u3059\u306D\u3002",
      false
    );
    setInputArea(`
    <div class="loading">
      <div class="spinner"></div>
      <p>\u4ECA\u65E5\u306E\u904B\u52E2\u3092\u8AAD\u307F\u89E3\u3044\u3066\u3044\u307E\u3059... \u{1F52E}</p>
    </div>
  `);
    try {
      const res = await fetch("/api/today-fortune", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          gender: state.formData.gender,
          birth
        })
      });
      if (!res.ok) {
        throw new Error(`HTTP error ${res.status}`);
      }
      const json = await res.json();
      if (json.error) {
        clearInputArea();
        await addMsg(
          `\u5360\u3044\u306E\u51E6\u7406\u4E2D\u306B\u30A8\u30E9\u30FC\u304C\u767A\u751F\u3057\u307E\u3057\u305F:
${json.error}`,
          false
        );
        setInputArea(`
        <button class="btn btn-secondary" onclick="restartFromBeginning()">
          \u{1F504} \u6700\u521D\u306B\u623B\u308B
        </button>
      `);
        return;
      }
      const rawMessage = json.message || "\u4ECA\u65E5\u306F\u3001\u81EA\u5206\u306E\u30DA\u30FC\u30B9\u3092\u5927\u5207\u306B\u904E\u3054\u3059\u3068\u826F\u3055\u305D\u3046\u306A\u65E5\u3067\u3059\u3002";
      const fortuneText = extractFortuneFromMessage(rawMessage);
      clearInputArea();
      await addMsg(`\u3010\u4ECA\u65E5\u306E\u904B\u52E2\u3011
${fortuneText}`, false);
      await addMsg(
        "\u3053\u306E\u6D41\u308C\u3092\u8E0F\u307E\u3048\u3066\u3001\u3042\u306A\u305F\u306E\u5C0E\u304D\u306E\u5929\u7136\u77F3\u3092\u8A3A\u65AD\u3057\u3066\u307F\u307E\u3059\u304B\uFF1F",
        false
      );
      setInputArea(`
      <button class="btn" onclick="selectMode('divination')">
        \u{1F48E} \u5C0E\u304D\u306E\u5929\u7136\u77F3\u3092\u8A3A\u65AD\u3059\u308B
      </button>
      <button class="btn btn-secondary" onclick="restartFromBeginning()">
        \u{1F504} \u6700\u521D\u306B\u623B\u308B
      </button>
    `);
    } catch {
      clearInputArea();
      await addMsg(
        "AI\u306B\u3046\u307E\u304F\u30A2\u30AF\u30BB\u30B9\u3067\u304D\u307E\u305B\u3093\u3067\u3057\u305F\u3002\n\u5C11\u3057\u6642\u9593\u3092\u304A\u3044\u3066\u304B\u3089\u3082\u3046\u4E00\u5EA6\u304A\u8A66\u3057\u304F\u3060\u3055\u3044\u3002",
        false
      );
      setInputArea(`
      <button class="btn" onclick="restartFromBeginning()">\u{1F504} \u6700\u521D\u306B\u623B\u308B</button>
    `);
    }
  }
  function extractFortuneFromMessage(raw) {
    if (!raw)
      return "";
    const cleaned = raw.replace(/```json/g, "").replace(/```/g, "").trim();
    try {
      const obj = JSON.parse(cleaned);
      return obj.\u9451\u5B9A\u7D50\u679C || cleaned;
    } catch {
      return cleaned;
    }
  }

  // public/liff/src/bracelet.ts
  async function stepBraceletSize() {
    const nameForDisplay = getUserNameForDisplay();
    await addMsg("\u6B21\u306F\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u306E\u30B5\u30A4\u30BA\u3092\u6C7A\u3081\u307E\u3059\u3002", false);
    await addMsg("\u3075\u3060\u3093\u8EAB\u306B\u3064\u3051\u308B\u3053\u3068\u3092\u30A4\u30E1\u30FC\u30B8\u3057\u306A\u304C\u3089\u9078\u3093\u3067\u307F\u3066\u304F\u3060\u3055\u3044\u3002", false);
    await addMsg("\u624B\u9996\u306E\u5185\u5F84\u306B\u8FD1\u3044\u30B5\u30A4\u30BA\u3092\u9078\u3076\u3068\u81EA\u7136\u306B\u7740\u3051\u3089\u308C\u307E\u3059\u3002", false);
    await addMsg("\u3042\u3068\u304B\u3089\u30B5\u30A4\u30BA\u76F4\u3057\u3092\u3057\u306A\u304F\u3066\u6E08\u3080\u3088\u3046\u306B\u3001\u3053\u3053\u3060\u3051\u5C11\u3057\u4E01\u5BE7\u306B\u9078\u3073\u307E\u3057\u3087\u3046\u3002", false);
    const savedWrist = state.formData.wrist_inner_cm || 16;
    const savedType = state.formData.bracelet_type || "birth_top_element_side";
    setInputArea(`
    <div class="input-field">
      <label>\u624B\u9996\u306E\u5185\u5F84\uFF08cm\uFF09</label>
      <div class="btn-group">
        <button class="btn-toggle ${savedWrist === 16 ? "active" : ""}" onclick="selectWristSize(16, this)">16cm</button>
        <button class="btn-toggle ${savedWrist === 18 ? "active" : ""}" onclick="selectWristSize(18, this)">18cm</button>
        <button class="btn-toggle ${savedWrist === 20 ? "active" : ""}" onclick="selectWristSize(20, this)">20cm</button>
      </div>
    </div>
    <div class="input-field">
      <label>\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u306E\u30BF\u30A4\u30D7</label>
      <div class="btn-group">
        <button class="btn-toggle ${savedType === "birth_top_element_side" ? "active" : ""}" onclick="selectBraceletType('birth_top_element_side', this)">\u8A95\u751F\u77F3\u3092\u30C8\u30C3\u30D7\u3001\u30A8\u30EC\u30E1\u30F3\u30C8\u306E\u77F3\u3092\u30B5\u30A4\u30C9\u306B</button>
        <button class="btn-toggle ${savedType === "element_top_only" ? "active" : ""}" onclick="selectBraceletType('element_top_only', this)">\u30A8\u30EC\u30E1\u30F3\u30C8\u306E\u77F3\u3060\u3051\u3092\u30C8\u30C3\u30D7\u306B</button>
      </div>
    </div>
    <button class="btn" onclick="buildBracelet()">\u{1F48E} \u3053\u306E\u77F3\u3067\u4F5C\u3089\u308C\u305F\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u3092\u898B\u308B</button>
  `);
  }
  function selectWristSize(size, el) {
    state.formData.wrist_inner_cm = size;
    el.parentElement?.querySelectorAll(".btn-toggle").forEach((b) => b.classList.remove("active"));
    el.classList.add("active");
  }
  function selectBraceletType(type, el) {
    state.formData.bracelet_type = type;
    el.parentElement?.querySelectorAll(".btn-toggle").forEach((b) => b.classList.remove("active"));
    el.classList.add("active");
  }
  function selectDesign(style, el) {
    state.formData.design_style = style;
    document.querySelectorAll(".input-field:last-child .btn-group .btn-toggle").forEach((b) => b.classList.remove("active"));
    el.classList.add("active");
  }
  async function buildBracelet() {
    addMsg("\u3053\u306E\u77F3\u3092\u4E2D\u5FC3\u306B\u3001\u3042\u306A\u305F\u306E\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u3092\u5F62\u306B\u3057\u307E\u3059\u3002", false);
    saveProfileToLocalStorage();
    setInputArea(`
    <div class="loading">
      <div class="spinner"></div>
      <p>\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u3092\u6E96\u5099\u3057\u3066\u3044\u307E\u3059... \u{1F48E}</p>
    </div>
  `);
    const result = state.divinationResult;
    const json = {
      product_slug: result?.product_slug,
      stone_name: result?.stone_name,
      design_text: result?.bracelet_proposal || "",
      image_url: result?.image_url,
      product_name: result?.product_name
    };
    await addMsg("\u3053\u306E\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u306F\u3001\u3042\u306A\u305F\u306E\u8A3A\u65AD\u7D50\u679C\u3092\u3082\u3068\u306B\u9078\u3070\u308C\u305F\u3082\u306E\u3067\u3059\u3002", false);
    await addMsg("\u4ECA\u306E\u3042\u306A\u305F\u306E\u6D41\u308C\u306B\u5408\u3046\u77F3\u3092\u4E2D\u5FC3\u306B\u3057\u305F\u4E00\u672C\u3067\u3059\u3002", false);
    displayBraceletResult(json);
  }
  function displayBraceletResult(data) {
    setProgress(4, 4, "\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u751F\u6210");
    const nameForDisplay = getUserNameForDisplay();
    clearInputArea();
    const chatBox = document.getElementById("chatBox");
    if (!chatBox)
      return;
    const section = document.createElement("div");
    section.className = "result-section";
    let html = `<h3>\u{1F48E} ${nameForDisplay}\u3092\u5C0E\u304F\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8</h3>`;
    html += `<p style="font-size:18px;font-weight:bold;">${data.product_name || data.bracelet_name || ""}</p>`;
    if (data.name || data.bracelet_name) {
      html += `<p style="font-weight:bold;font-size:16px;margin-top:6px;">${data.name || data.bracelet_name}</p>`;
    }
    if (data.name_en || data.bracelet_name_en) {
      html += `<p style="font-size:12px;opacity:0.7;">${data.name_en || data.bracelet_name_en}</p>`;
    }
    const img = data.image_url || data.image;
    if (img) {
      html += `<img src="${img}" style="width:100%;border-radius:12px;margin:12px 0;">`;
    }
    if (data.design_text) {
      html += `<p>${formatText(data.design_text)}</p>`;
    }
    if (data.stone_counts) {
      html += `<p style="margin-top:12px;font-size:13px;">`;
      for (const [stone, count] of Object.entries(data.stone_counts)) {
        html += `${stone} \xD7 ${count}<br>`;
      }
      html += `</p>`;
    }
    section.innerHTML = html;
    chatBox.appendChild(section);
    scrollChatToBottom();
    setInputArea(`
    <button class="btn" onclick="goToProduct()">\u{1F6D2} \u3053\u306E\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u3092\u8CFC\u5165\u3059\u308B</button>
    <button class="btn btn-secondary" onclick="restartFromBeginning()">\u{1F504} \u3082\u3046\u4E00\u5EA6\u5360\u3046</button>
  `);
  }
  function goToProduct() {
    const result = state.divinationResult;
    const slug = result?.product_slug || result?.bracelet?.product_slug;
    if (!slug) {
      addMsg("\u5546\u54C1\u30DA\u30FC\u30B8\u304C\u898B\u3064\u304B\u308A\u307E\u305B\u3093\u3067\u3057\u305F", false);
      return;
    }
    const url = `https://spicastar.info/atlas/?p=` + result?.id;
    window.location.href = url;
  }
  function confirmOrder() {
    const diagnosisId = window.diagnosisId;
    const wrist = state.formData.wrist_inner_cm;
    const problem = state.formData.problem || "";
    const oracleCard = state.divinationResult?.oraclecardname || "";
    const lines = [
      "\u3053\u306E\u5185\u5BB9\u3067\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u3092\u6CE8\u6587\u3057\u305F\u3044\u3067\u3059\u3002",
      diagnosisId ? `\u8A3A\u65ADID: ${diagnosisId}` : "",
      wrist ? `\u624B\u9996\u5185\u5F84: ${wrist}cm` : "",
      problem ? `\u304A\u60A9\u307F: ${problem}` : "",
      oracleCard ? `\u30AA\u30E9\u30AF\u30EB\u30AB\u30FC\u30C9: ${oracleCard}` : ""
    ].filter(Boolean);
    const encoded = encodeURIComponent(lines.join("\n"));
    window.location.href = `https://line.me/R/oaMessage/@586spjck/?${encoded}`;
  }

  // public/liff/src/steps.ts
  function stepModeSelect() {
    state.userState = "mode_select";
    addMsg("\u4ECA\u65E5\u306F\u3069\u3061\u3089\u306B\u3057\u307E\u3059\u304B\uFF1F", false);
    setInputArea(`
    <button class="btn" onclick="selectMode('divination')">\u2728 \u5C0E\u304D\u306E\u77F3\u3092\u8A3A\u65AD\u3059\u308B</button>
    <button class="btn" onclick="selectMode('today_fortune')">\u{1F52E} \u4ECA\u65E5\u306E\u904B\u52E2\u3092\u8A3A\u65AD\u3059\u308B</button>
    <button class="btn btn-secondary" onclick="selectMode('stone_select')">\u{1F48E} \u597D\u307F\u3067\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u3092\u9078\u3076</button>
  `);
  }
  function selectMode(mode) {
    state.selectedMode = mode;
    if (mode === "today_fortune") {
      addMsg("\u4ECA\u65E5\u306E\u904B\u52E2\u3092\u8A3A\u65AD\u3059\u308B", true);
      stepTodayFortune().then(() => showAstrologicalInfoForm());
    } else if (mode === "divination") {
      addMsg("\u5C0E\u304D\u306E\u77F3\u3092\u8A3A\u65AD\u3059\u308B", true);
      showAstrologicalInfoForm();
    } else {
      addMsg("\u597D\u307F\u3067\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u3092\u9078\u3076", true);
      stepStoneSelectMethod();
    }
  }
  function showAstrologicalInfoForm() {
    setProgress(1, 4, "\u30D7\u30ED\u30D5\u30A3\u30FC\u30EB\u5165\u529B");
    addMsg("\u4ECA\u306E\u3042\u306A\u305F\u306B\u3064\u3044\u3066\u5C11\u3057\u3060\u3051\u6559\u3048\u3066\u304F\u3060\u3055\u3044\u3002\n\u306F\u3058\u3081\u306B\u3001\u8A3A\u65AD\u306B\u5FC5\u8981\u306A\u60C5\u5831\u3092\u304A\u805E\u304B\u305B\u304F\u3060\u3055\u3044\u3002", false);
    const gender = state.formData.gender || "";
    const birth = state.formData.birth || {};
    const savedDate = birth.date || "";
    const savedTime = birth.time || "";
    const savedPlace = birth.place || "";
    const savedName = state.formData.name || "";
    state.userState = "astrological_info";
    setInputArea(`
    <div class="input-field">
      <label>\u304A\u540D\u524D\uFF08\u30CB\u30C3\u30AF\u30CD\u30FC\u30E0\uFF09</label>
      <input type="text" id="userName" value="${savedName}" placeholder="\u4F8B\uFF1A\u3055\u3068">
    </div>
    <div class="input-field">
      <label>\u6027\u5225 *</label>
      <div class="btn-group">
        <button class="btn-toggle ${gender === "\u5973\u6027" ? "active" : ""}" onclick="selectGender('\u5973\u6027', this)">\u5973\u6027</button>
        <button class="btn-toggle ${gender === "\u7537\u6027" ? "active" : ""}" onclick="selectGender('\u7537\u6027', this)">\u7537\u6027</button>
        <button class="btn-toggle ${gender === "\u305D\u306E\u4ED6" ? "active" : ""}" onclick="selectGender('\u305D\u306E\u4ED6', this)">\u305D\u306E\u4ED6</button>
      </div>
    </div>
    <div class="input-field">
      <label>\u751F\u5E74\u6708\u65E5 *</label>
      <input type="text" id="birthDate" value="${savedDate}" required>
    </div>
    <div class="input-field">
      <label>\u51FA\u751F\u6642\u9593</label>
      <input type="text" id="birthTime" value="${savedTime}">
    </div>
    <div class="input-field">
      <label>\u51FA\u751F\u5730</label>
      <input type="text" id="birthPlace" placeholder="\u4F8B\uFF1A\u672D\u5E4C\u5E02" value="${savedPlace}">
    </div>
    <button class="btn" onclick="nextStep()">\u6B21\u3078</button>
  `);
    flatpickr("#birthDate", { locale: "ja", dateFormat: "Y-m-d", maxDate: "today" });
    flatpickr("#birthTime", { enableTime: true, noCalendar: true, dateFormat: "H:i", time_24hr: true });
  }
  function selectGender(gender, el) {
    state.formData.gender = gender;
    el.parentElement?.querySelectorAll(".btn-toggle").forEach((b) => b.classList.remove("active"));
    el.classList.add("active");
  }
  function nextStep() {
    if (state.userState === "astrological_info") {
      const name = document.getElementById("userName")?.value || "";
      const date = document.getElementById("birthDate")?.value;
      const time = document.getElementById("birthTime")?.value || "";
      const place = document.getElementById("birthPlace")?.value || "";
      if (!state.formData.gender) {
        addMsg("\u6027\u5225\u3092\u9078\u3093\u3067\u304F\u3060\u3055\u3044", false);
        return;
      }
      if (!date) {
        addMsg("\u751F\u5E74\u6708\u65E5\u306F\u5FC5\u9808\u3067\u3059", false);
        return;
      }
      state.formData.birth = { date, time, place };
      state.formData.name = name;
      saveProfileToLocalStorage();
      clearInputArea();
      if (state.selectedMode === "today_fortune") {
        runTodayFortune();
      } else {
        stepConcerns();
      }
      return;
    } else if (state.userState === "concerns") {
      stepProblem();
    }
  }
  function stepConcerns() {
    setProgress(2, 4, "\u60A9\u307F\u306E\u8A3A\u65AD");
    const nameForDisplay = getUserNameForDisplay();
    const text = [
      `${nameForDisplay}\u304C\u3044\u307E\u3001\u7279\u306B\u6C17\u306B\u306A\u3063\u3066\u3044\u308B\u30C6\u30FC\u30DE\u3092\u6559\u3048\u3066\u304F\u3060\u3055\u3044\u3002`,
      "\u8907\u6570\u9078\u3093\u3067\u3082\u5927\u4E08\u592B\u3067\u3059\u3002"
    ].join("\n\n");
    addMsg(text, false);
    state.userState = "concerns";
    setInputArea(`
    <div class="btn-group">
      <button class="btn-toggle" onclick="toggleConcern(this, '\u604B\u611B')">\u{1F495} \u604B\u611B</button>
      <button class="btn-toggle" onclick="toggleConcern(this, '\u4ED5\u4E8B')">\u{1F4BC} \u4ED5\u4E8B</button>
      <button class="btn-toggle" onclick="toggleConcern(this, '\u91D1\u904B')">\u{1F4B0} \u91D1\u904B</button>
      <button class="btn-toggle" onclick="toggleConcern(this, '\u5065\u5EB7')">\u{1F33F} \u5065\u5EB7</button>
      <button class="btn-toggle" onclick="toggleConcern(this, '\u4EBA\u9593\u95A2\u4FC2')">\u{1F91D} \u4EBA\u9593\u95A2\u4FC2</button>
      <button class="btn-toggle" onclick="toggleConcern(this, '\u305D\u306E\u4ED6')">\u2728 \u305D\u306E\u4ED6</button>
    </div>
    <button class="btn" onclick="nextStep()">\u6B21\u3078</button>
  `);
  }
  function toggleConcern(el, concern) {
    state.formData.concerns = state.formData.concerns || [];
    if (el.classList.contains("active")) {
      el.classList.remove("active");
      state.formData.concerns = state.formData.concerns.filter((c) => c !== concern);
    } else {
      el.classList.add("active");
      if (!state.formData.concerns.includes(concern)) {
        state.formData.concerns.push(concern);
      }
    }
  }
  async function stepProblem() {
    if (!state.formData.concerns || state.formData.concerns.length === 0) {
      addMsg("\u5C11\u306A\u304F\u3068\u30821\u3064\u9078\u3093\u3067\u304F\u3060\u3055\u3044\u3002", false);
      return;
    }
    addMsg(state.formData.concerns.join("\u3001"), true);
    await addMsg(
      "\u5177\u4F53\u7684\u306A\u72B6\u6CC1\u3084\u304A\u6C17\u6301\u3061\u3092\u3001\u66F8\u3051\u308B\u7BC4\u56F2\u3067\u6559\u3048\u3066\u304F\u3060\u3055\u3044\u3002\n\u3046\u307E\u304F\u307E\u3068\u307E\u3063\u3066\u3044\u306A\u304F\u3066\u3082\u5927\u4E08\u592B\u3067\u3059\u3002",
      false
    );
    state.userState = "problem";
    setInputArea(`
    <div class="input-field">
      <textarea id="problemText" placeholder="\u4F8B\uFF1A\u6700\u8FD1\u5F7C\u3068\u306E\u95A2\u4FC2\u304C\u3046\u307E\u304F\u3044\u304B\u306A\u304F\u3066..."></textarea>
    </div>
    <button class="btn" onclick="executeDiagnose()">\u8A3A\u65AD\u958B\u59CB</button>
  `);
  }
  function stepStoneSelectMethod() {
    addMsg("\u3069\u306E\u65B9\u6CD5\u3067\u77F3\u3092\u9078\u3073\u307E\u3059\u304B\uFF1F", false);
    setInputArea(`
    <div class="btn-group">
      <button class="btn-toggle active" onclick="selectStoneMethod('color', this)">\u8272</button>
      <button class="btn-toggle" onclick="selectStoneMethod('effect', this)">\u52B9\u679C</button>
      <button class="btn-toggle" onclick="selectStoneMethod('zodiac', this)">\u661F\u5EA7</button>
      <button class="btn-toggle" onclick="selectStoneMethod('moon', this)">\u6708</button>
    </div>
    <button class="btn" onclick="showStoneOptions()">\u6B21\u3078</button>
  `);
  }
  function selectStoneMethod(method, el) {
    state.formData.stone_method = method;
    el.parentElement?.querySelectorAll(".btn-toggle").forEach((b) => b.classList.remove("active"));
    el.classList.add("active");
  }
  function showStoneOptions() {
    const method = state.formData.stone_method || "color";
    const methodLabelMap = {
      color: "\u8272",
      effect: "\u52B9\u679C",
      zodiac: "\u661F\u5EA7",
      moon: "\u8A95\u751F\u6708"
    };
    const methodLabel = methodLabelMap[method] || "";
    addMsg(methodLabel, true);
    let options = [];
    if (method === "color") {
      options = ["\u7D2B", "\u30D4\u30F3\u30AF", "\u9EC4", "\u900F\u660E", "\u9ED2", "\u6C34\u8272", "\u7D3A", "\u8336\u91D1", "\u767D", "\u8D64"];
    } else if (method === "effect") {
      options = ["\u611B\u60C5", "\u7652\u3057", "\u91D1\u904B", "\u6D44\u5316", "\u4FDD\u8B77", "\u76F4\u611F", "\u60C5\u71B1", "\u5973\u6027\u6027"];
    } else if (method === "zodiac") {
      options = ["\u7261\u7F8A\u5EA7", "\u7261\u725B\u5EA7", "\u53CC\u5B50\u5EA7", "\u87F9\u5EA7", "\u7345\u5B50\u5EA7", "\u4E59\u5973\u5EA7", "\u5929\u79E4\u5EA7", "\u880D\u5EA7", "\u5C04\u624B\u5EA7", "\u5C71\u7F8A\u5EA7", "\u6C34\u74F6\u5EA7", "\u9B5A\u5EA7"];
    } else {
      options = ["1\u6708", "2\u6708", "3\u6708", "4\u6708", "5\u6708", "6\u6708", "7\u6708", "8\u6708", "9\u6708", "10\u6708", "11\u6708", "12\u6708"];
    }
    addMsg(`${methodLabel}\u3092\u9078\u3093\u3067\u304F\u3060\u3055\u3044`, false);
    let html = '<div class="btn-group">';
    for (const opt of options) {
      html += `<button class="btn-toggle" onclick="selectStoneOption('${opt}', this)">${opt}</button>`;
    }
    html += '</div><button class="btn" onclick="confirmStoneSelection()">\u3053\u306E\u77F3\u3067\u9032\u3080</button>';
    setInputArea(html);
  }
  function selectStoneOption(option, el) {
    state.formData.stone_option = option;
    el.parentElement?.querySelectorAll(".btn-toggle").forEach((b) => b.classList.remove("active"));
    el.classList.add("active");
  }
  function confirmStoneSelection() {
    const option = state.formData.stone_option;
    if (!option) {
      addMsg("\u9078\u629E\u3057\u3066\u304F\u3060\u3055\u3044", false);
      return;
    }
    addMsg(option, true);
    const stoneMap = {
      "\u7D2B": "\u30A2\u30E1\u30B8\u30B9\u30C8",
      "\u30D4\u30F3\u30AF": "\u30ED\u30FC\u30BA\u30AF\u30A9\u30FC\u30C4",
      "\u9EC4": "\u30B7\u30C8\u30EA\u30F3",
      "\u900F\u660E": "\u6C34\u6676",
      "\u9ED2": "\u30AA\u30CB\u30AD\u30B9",
      "\u6C34\u8272": "\u30A2\u30AF\u30A2\u30DE\u30EA\u30F3",
      "\u7D3A": "\u30E9\u30D4\u30B9\u30E9\u30BA\u30EA",
      "\u8336\u91D1": "\u30BF\u30A4\u30AC\u30FC\u30A2\u30A4",
      "\u767D": "\u30E0\u30FC\u30F3\u30B9\u30C8\u30FC\u30F3",
      "\u8D64": "\u30AB\u30FC\u30CD\u30EA\u30A2\u30F3"
    };
    const selectedStone = stoneMap[option] || "\u30A2\u30E1\u30B8\u30B9\u30C8";
    state.divinationResult = {
      stones_for_user: [
        { name: selectedStone, reason: `${option}\u3092\u9078\u3093\u3060\u3042\u306A\u305F\u306B\u3074\u3063\u305F\u308A\u306E\u77F3\u3067\u3059` }
      ]
    };
    stepOrderChoice();
  }
  function stepOrderChoice() {
    addMsg("\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u306E\u6CE8\u6587\u65B9\u6CD5\u3092\u9078\u3093\u3067\u304F\u3060\u3055\u3044\u3002", false);
    setInputArea(`
    <button class="btn" onclick="selectOrderType('custom')">\u2728 \u30AA\u30FC\u30C0\u30FC\u30E1\u30A4\u30C9\uFF08\u30AB\u30B9\u30BF\u30DE\u30A4\u30BA\uFF09</button>
    <button class="btn btn-secondary" onclick="selectOrderType('shop')">\u{1F6D2} \u30CD\u30C3\u30C8\u30B7\u30E7\u30C3\u30D7\u304B\u3089\u9078\u3076</button>
  `);
  }
  function selectOrderType(type) {
    if (type === "custom") {
      addMsg("\u30AA\u30FC\u30C0\u30FC\u30E1\u30A4\u30C9\uFF08\u30AB\u30B9\u30BF\u30DE\u30A4\u30BA\uFF09", true);
      stepBraceletSize();
    } else {
      addMsg("\u30CD\u30C3\u30C8\u30B7\u30E7\u30C3\u30D7\u304B\u3089\u9078\u3076", true);
      addMsg("\u4ECA\u306E\u8A3A\u65AD\u7D50\u679C\u306B\u95A2\u9023\u3059\u308B\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u3092\u3001\u30CD\u30C3\u30C8\u30B7\u30E7\u30C3\u30D7\u3067\u304A\u898B\u305B\u3057\u307E\u3059\u306D\u3002", false);
      const method = state.formData.stone_method;
      const option = state.formData.stone_option;
      const categoryUrlMap = {
        color: {
          "\u7D2B": "https://spicastar.info/atlas/shop/product-category/color-purple/",
          "\u30D4\u30F3\u30AF": "https://spicastar.info/atlas/shop/product-category/color-pink/",
          "\u9EC4": "https://spicastar.info/atlas/shop/product-category/color-yellow/",
          "\u900F\u660E": "https://spicastar.info/atlas/shop/product-category/color-clear/",
          "\u9ED2": "https://spicastar.info/atlas/shop/product-category/color-black/",
          "\u6C34\u8272": "https://spicastar.info/atlas/shop/product-category/color-lightblue/",
          "\u7D3A": "https://spicastar.info/atlas/shop/product-category/color-navy/",
          "\u8336\u91D1": "https://spicastar.info/atlas/shop/product-category/color-brown-gold/",
          "\u767D": "https://spicastar.info/atlas/shop/product-category/color-white/",
          "\u8D64": "https://spicastar.info/atlas/shop/product-category/color-red/"
        },
        effect: {
          "\u611B\u60C5": "https://spicastar.info/atlas/shop/product-category/effect-love/",
          "\u7652\u3057": "https://spicastar.info/atlas/shop/product-category/effect-healing/",
          "\u91D1\u904B": "https://spicastar.info/atlas/shop/product-category/effect-money/",
          "\u6D44\u5316": "https://spicastar.info/atlas/shop/product-category/effect-purify/",
          "\u4FDD\u8B77": "https://spicastar.info/atlas/shop/product-category/effect-protection/",
          "\u76F4\u611F": "https://spicastar.info/atlas/shop/product-category/effect-intuition/",
          "\u60C5\u71B1": "https://spicastar.info/atlas/shop/product-category/effect-passion/",
          "\u5973\u6027\u6027": "https://spicastar.info/atlas/shop/product-category/effect-femininity/"
        },
        zodiac: {
          "\u7261\u7F8A\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-aries/",
          "\u7261\u725B\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-taurus/",
          "\u53CC\u5B50\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-gemini/",
          "\u87F9\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-cancer/",
          "\u7345\u5B50\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-leo/",
          "\u4E59\u5973\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-virgo/",
          "\u5929\u79E4\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-libra/",
          "\u880D\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-scorpio/",
          "\u5C04\u624B\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-sagittarius/",
          "\u5C71\u7F8A\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-capricorn/",
          "\u6C34\u74F6\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-aquarius/",
          "\u9B5A\u5EA7": "https://spicastar.info/atlas/shop/product-category/zodiac-pisces/"
        },
        moon: {
          "1\u6708": "https://spicastar.info/atlas/shop/product-category/moon-january/",
          "2\u6708": "https://spicastar.info/atlas/shop/product-category/moon-february/",
          "3\u6708": "https://spicastar.info/atlas/shop/product-category/moon-march/",
          "4\u6708": "https://spicastar.info/atlas/shop/product-category/moon-april/",
          "5\u6708": "https://spicastar.info/atlas/shop/product-category/moon-may/",
          "6\u6708": "https://spicastar.info/atlas/shop/product-category/moon-june/",
          "7\u6708": "https://spicastar.info/atlas/shop/product-category/moon-july/",
          "8\u6708": "https://spicastar.info/atlas/shop/product-category/moon-august/",
          "9\u6708": "https://spicastar.info/atlas/shop/product-category/moon-september/",
          "10\u6708": "https://spicastar.info/atlas/shop/product-category/moon-october/",
          "11\u6708": "https://spicastar.info/atlas/shop/product-category/moon-november/",
          "12\u6708": "https://spicastar.info/atlas/shop/product-category/moon-december/"
        }
      };
      let url = "https://spicastar.info/atlas/shop/";
      if (method && option && categoryUrlMap[method] && categoryUrlMap[method][option]) {
        url = categoryUrlMap[method][option];
        const params = new URLSearchParams({ from: "atlas-chat", method, choice: option });
        url = `${url}?${params.toString()}`;
      }
      window.location.href = url;
    }
  }
  function restartFromBeginning() {
    const box = document.getElementById("chatBox");
    if (box)
      box.innerHTML = "";
    addMsg(getGreetingMessage(), false);
    loadProfileFromLocalStorage();
    stepModeSelect();
  }

  // public/liff/src/diagnose.ts
  var thinkingMessages = [
    "\u661F\u306E\u914D\u7F6E\u3092\u8AAD\u307F\u89E3\u3044\u3066\u3044\u307E\u3059\u2026",
    "\u904B\u547D\u306E\u6D41\u308C\u3092\u78BA\u8A8D\u3057\u3066\u3044\u307E\u3059\u2026",
    "\u3042\u306A\u305F\u306B\u5408\u3046\u77F3\u3092\u63A2\u3057\u3066\u3044\u307E\u3059\u2026",
    "\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u306E\u69CB\u6210\u3092\u8003\u3048\u3066\u3044\u307E\u3059\u2026"
  ];
  function rotateThinking() {
    const el = document.getElementById("thinkingText");
    if (!el)
      return;
    state.thinkingIndex = (state.thinkingIndex + 1) % thinkingMessages.length;
    el.textContent = thinkingMessages[state.thinkingIndex];
  }
  async function executeDiagnose() {
    setProgress(3, 4, "\u5C0E\u304D\u306E\u77F3\u3092\u9078\u5B9A");
    const nameForDisplay = getUserNameForDisplay();
    let problem = document.getElementById("problemText")?.value || "";
    if (!problem) {
      problem = `\u5177\u4F53\u7684\u306A\u3054\u76F8\u8AC7\u5185\u5BB9\u306F\u66F8\u304B\u308C\u3066\u3044\u306A\u3044\u305F\u3081\u3001\u4ECA\u306E${nameForDisplay}\u306E\u5168\u4F53\u306E\u6D41\u308C\u3084\u3001\u3053\u308C\u304B\u3089\u5927\u5207\u306B\u3057\u305F\u3044\u30C6\u30FC\u30DE\u304C\u308F\u304B\u308B\u3088\u3046\u306A\u5168\u4F53\u904B\u3092\u4E2D\u5FC3\u306B\u8AAD\u307F\u89E3\u3044\u3066\u304F\u3060\u3055\u3044\u3002`;
    }
    addMsg(problem, true);
    state.formData.problem = problem;
    const date = state.formData.birth?.date;
    if (!date) {
      addMsg("\u751F\u5E74\u6708\u65E5\u306F\u5FC5\u9808\u3067\u3059", false);
      return;
    }
    await addMsg("\u308F\u304B\u308A\u307E\u3057\u305F\u3002\u3042\u308A\u304C\u3068\u3046\u3054\u3056\u3044\u307E\u3059\u3002\n\u3053\u306E\u5185\u5BB9\u3067\u661F\u3068\u77F3\u306E\u6D41\u308C\u3092\u8AAD\u307F\u89E3\u3044\u3066\u3044\u304D\u307E\u3059\u3002\n\n\u5C11\u3057\u3060\u3051\u304A\u5F85\u3061\u304F\u3060\u3055\u3044\u306D\u3002", false);
    setInputArea(`
    <div class="loading">
      <div class="spinner"></div>
      <p id="thinkingText">\u661F\u306E\u914D\u7F6E\u3092\u8AAD\u307F\u89E3\u3044\u3066\u3044\u307E\u3059... \u{1F30C}</p>
    </div>
  `);
    const thinkingTimer = setInterval(rotateThinking, 2e3);
    try {
      state.formData.line_user_id = window.LINE_USER_ID ?? state.userId ?? void 0;
      const res = await fetch("/api/diagnose", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(state.formData)
      });
      if (!res.ok) {
        throw new Error(`HTTP error ${res.status}`);
      }
      const json = await res.json();
      if (json.error) {
        clearInterval(thinkingTimer);
        addMsg(`\u30A8\u30E9\u30FC\u304C\u767A\u751F\u3057\u307E\u3057\u305F: ${json.error}`, false);
        clearInputArea();
        return;
      }
      window.diagnosisId = json.diagnosis_id;
      state.productCandidates = json.products || [];
      state.selectedProductIndex = state.productCandidates.length > 0 ? 0 : null;
      clearInterval(thinkingTimer);
      state.divinationResult = json;
      displayDivinationResult(json);
    } catch {
      clearInterval(thinkingTimer);
      addMsg("\u901A\u4FE1\u30A8\u30E9\u30FC\u304C\u767A\u751F\u3057\u307E\u3057\u305F", false);
      clearInputArea();
    }
  }
  async function showOracleCard(card) {
    await addMsg("\u30AB\u30FC\u30C9\u3092\u30B7\u30E3\u30C3\u30D5\u30EB\u3057\u3066\u3044\u307E\u3059\u2026", false);
    await new Promise((r) => setTimeout(r, 1200));
    await addMsg("1\u679A\u5F15\u304D\u307E\u3059\u2026", false);
    await new Promise((r) => setTimeout(r, 1e3));
    const cardHtml = `
    <div class="msg bot">
      <div class="result-section" style="text-align:center;">
        <h3>\u{1F3B4} \u30AA\u30E9\u30AF\u30EB\u30AB\u30FC\u30C9</h3>
        <img src="${card.image_url}"
          class="section-image"
          style="width:200px;margin:12px auto;display:block;"
          onload="this.classList.add('loaded')"
          onerror="this.style.display='none'">
        <p style="font-size:16px;font-weight:bold;margin-top:8px;">
          ${card.name} ${card.is_upright ? "\uFF08\u6B63\u4F4D\u7F6E\uFF09" : "\uFF08\u9006\u4F4D\u7F6E\uFF09"}
        </p>
      </div>
    </div>
  `;
    const box = document.getElementById("chatBox");
    if (box) {
      box.insertAdjacentHTML("beforeend", cardHtml);
      scrollChatToBottom();
    }
  }
  function typeIntoElement(element, rawText, speed = 20) {
    return new Promise((resolve) => {
      const html = formatText(rawText || "");
      const plain = html.replace(/<br\s*\/?>/gi, "\n").replace(/<[^>]*>/g, "");
      let i = 0;
      function step() {
        if (i < plain.length) {
          element.textContent = plain.slice(0, i + 1);
          i++;
          scrollChatToBottom();
          setTimeout(step, speed);
        } else {
          element.innerHTML = html;
          resolve();
        }
      }
      step();
    });
  }
  async function displayDivinationResult(result) {
    setProgress(3, 4, "\u5C0E\u304D\u306E\u77F3\u3092\u9078\u5B9A");
    clearInputArea();
    const nameForDisplay = getUserNameForDisplay();
    const stoneName = result.stone_name || (result.stones_for_user?.[0]?.name || "\u3042\u306A\u305F\u306E\u77F3");
    const chatBox = document.getElementById("chatBox");
    if (!chatBox)
      return;
    const images = result.images || {};
    const sections = [
      { key: "destiny_map", title: "\u2728 \u904B\u547D\u306E\u5730\u56F3", text: result.destiny_map, lead: "\u307E\u305A\u306F\u3001\u3042\u306A\u305F\u5168\u4F53\u306E\u30C6\u30FC\u30DE\u3084\u6D41\u308C\u3092\u5730\u56F3\u306E\u3088\u3046\u306B\u898B\u3066\u3044\u304D\u307E\u3059\u306D\u3002", image: images.destiny_scene },
      { key: "past", title: "\u{1F319} \u3053\u308C\u307E\u3067\u306E\u6D41\u308C", text: result.past, lead: "\u6B21\u306B\u3001\u3042\u306A\u305F\u304C\u3053\u308C\u307E\u3067\u3069\u3093\u306A\u8CC7\u8CEA\u3084\u6D41\u308C\u3092\u6301\u3063\u3066\u6B69\u3044\u3066\u304D\u305F\u306E\u304B\u3092\u8AAD\u307F\u89E3\u3044\u3066\u3044\u304D\u307E\u3059\u3002" },
      { key: "present_future", title: "\u2600\uFE0F \u4ECA\u3068\u672A\u6765\u3078\u306E\u6D41\u308C", text: result.present_future, lead: "\u6B21\u306B\u3001\u3042\u306A\u305F\u306E\u4ECA\u3068\u3053\u308C\u304B\u3089\u306E\u6D41\u308C\u3092\u898B\u3066\u3044\u304D\u307E\u3059\u3002" },
      { key: "element_diagnosis", title: "\u{1F525} \u30A8\u30EC\u30E1\u30F3\u30C8\u306E\u30D0\u30E9\u30F3\u30B9", text: result.element_diagnosis, lead: "\u6B21\u306F\u3001\u706B\u30FB\u5730\u30FB\u98A8\u30FB\u6C34\u306E\u30D0\u30E9\u30F3\u30B9\u304B\u3089\u898B\u3066\u3044\u304D\u307E\u3059\u3002", image: images.element_balance },
      { key: "bracelet_proposal", title: "\u{1F48E} \u77F3\u306E\u9078\u3073\u65B9\u3068\u610F\u56F3", text: result.bracelet_proposal, lead: "\u3053\u3053\u304B\u3089\u306F\u77F3\u306E\u7D44\u307F\u5408\u308F\u305B\u306E\u610F\u56F3\u3092\u898B\u3066\u3044\u304D\u307E\u3059\u3002", image: images.bracelet },
      { key: "stone_support_message", title: "\u{1F490} \u77F3\u304B\u3089\u306E\u30B5\u30DD\u30FC\u30C8\u30E1\u30C3\u30BB\u30FC\u30B8", text: result.stone_support_message, lead: "\u77F3\u305F\u3061\u306E\u30E1\u30C3\u30BB\u30FC\u30B8\u3092\u304A\u4F1D\u3048\u3057\u307E\u3059\u3002" }
    ].filter((sec) => sec.text);
    let currentIndex = 0;
    await addMsg(`\u3053\u3053\u304B\u3089\u306F\u3001\u661F\u306E\u914D\u7F6E\u3068\u30A8\u30EC\u30E1\u30F3\u30C8\u306E\u6D41\u308C\u3092\u3082\u3068\u306B\u3001
${nameForDisplay}\u306E\u4ECA\u306E\u6D41\u308C\u3092\u8AAD\u307F\u89E3\u3044\u3066\u3044\u304D\u307E\u3059\u3002`, false);
    async function showCurrentSection() {
      if (currentIndex >= sections.length) {
        const extras = [];
        if (result.affirmation) {
          extras.push(`
\u2728 \u3042\u306A\u305F\u3078\u306E\u8A00\u8449
${result.affirmation}`);
        }
        if (result.lucky_color) {
          extras.push(`\u{1F308} \u30E9\u30C3\u30AD\u30FC\u30AB\u30E9\u30FC: **${result.lucky_color}**`);
        }
        if (result.daily_advice) {
          extras.push(`
\u{1F4DD} \u4ECA\u65E5\u304B\u3089\u3067\u304D\u308B\u3053\u3068
${result.daily_advice.split(",").map((a) => `\u30FB ${a.trim()}`).join("\n")}`);
        }
        if (extras.length > 0) {
          await addMsg(extras.join("\n\n"), false);
        }
        await addMsg("\u3053\u3053\u307E\u3067\u306E\u6D41\u308C\u304B\u3089\u3001\u4ECA\u306E\u3042\u306A\u305F\u3092\u6574\u3048\u308B\u77F3\u304C\u898B\u3048\u3066\u304D\u307E\u3057\u305F\u3002", false);
        await addMsg(`\u4ECA\u56DE\u306E\u8A3A\u65AD\u3067\u3042\u306A\u305F\u306E\u8EF8\u3068\u306A\u308B\u77F3\u306F **${stoneName}** \u3067\u3059\u3002`, false);
        await addMsg(
          `\u3053\u306E\u77F3\u306F\u3001\u3042\u306A\u305F\u306E\u661F\u306E\u914D\u7F6E\u3068\u4ECA\u306E\u5FC3\u306E\u6CE2\u9577\u304B\u3089\u5C0E\u304D\u51FA\u3055\u308C\u305F\u3082\u306E\u3067\u3059\u3002

\u3075\u3068\u8FF7\u3063\u305F\u3068\u304D\u3001\u5FC3\u304C\u63FA\u308C\u305F\u3068\u304D\u3001\u305D\u3063\u3068\u624B\u9996\u306B\u89E6\u308C\u3066\u307F\u3066\u304F\u3060\u3055\u3044\u3002
**${stoneName}**\u306E\u9759\u304B\u306A\u30A8\u30CD\u30EB\u30AE\u30FC\u304C\u3001\u3042\u306A\u305F\u672C\u6765\u306E\u30EA\u30BA\u30E0\u3092\u601D\u3044\u51FA\u3055\u305B\u3066\u304F\u308C\u308B\u306F\u305A\u3067\u3059\u3002`,
          false
        );
        await addMsg("\u3082\u3057\u3053\u306E\u77F3\u305F\u3061\u3068\u4E00\u7DD2\u306B\u6B69\u3044\u3066\u307F\u305F\u3044\u3068\u611F\u3058\u305F\u306A\u3089\u3001\u3042\u306A\u305F\u306E\u305F\u3081\u306E\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u3068\u3057\u3066\u5F62\u306B\u3057\u3066\u307F\u307E\u3057\u3087\u3046\u3002", false);
        setInputArea(`
        <button class="btn" onclick="showProductCandidates()">\u{1F48E} \u8A3A\u65AD\u7D50\u679C\u304B\u3089\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u5019\u88DC\u3092\u898B\u308B</button>
        <button class="btn btn-secondary" onclick="goLineRegister()">\u{1F52E} LINE\u3067\u30AA\u30E9\u30AF\u30EB\u30AB\u30FC\u30C9\u3092\u53D7\u3051\u53D6\u308B</button>
      `);
        return;
      }
      const sec = sections[currentIndex];
      if (sec.lead) {
        await addMsg(sec.lead, false);
      }
      const wrapper = document.createElement("div");
      wrapper.className = "msg bot";
      const inner = document.createElement("div");
      inner.className = "result-section";
      const h3 = document.createElement("h3");
      h3.textContent = sec.title;
      inner.appendChild(h3);
      if (sec.image) {
        const img = document.createElement("img");
        img.src = sec.image;
        img.className = "section-image";
        img.alt = sec.title;
        img.onload = () => img.classList.add("loaded");
        img.onerror = () => img.style.display = "none";
        inner.appendChild(img);
      }
      const p = document.createElement("p");
      inner.appendChild(p);
      wrapper.appendChild(inner);
      chatBox.appendChild(wrapper);
      scrollChatToBottom();
      await typeIntoElement(p, sec.text, 20);
      if (sec.key === "element_diagnosis") {
        await addMsg("\u6700\u5F8C\u306B\u30AA\u30E9\u30AF\u30EB\u30AB\u30FC\u30C9\u3092\u5F15\u3044\u3066\u3001\u5C0E\u304D\u306E\u58F0\u3092\u805E\u3044\u3066\u307F\u307E\u3057\u3087\u3046\u3002", false);
        const oracleCard = result.oracle_card;
        if (oracleCard) {
          await showOracleCard(oracleCard);
        }
        const wrapper2 = document.createElement("div");
        wrapper2.className = "msg bot";
        const inner2 = document.createElement("div");
        inner2.className = "result-section";
        const h3b = document.createElement("h3");
        h3b.textContent = "\u30AA\u30E9\u30AF\u30EB\u304B\u3089\u306E\u30E1\u30C3\u30BB\u30FC\u30B8";
        const p2 = document.createElement("p");
        inner2.appendChild(h3b);
        inner2.appendChild(p2);
        wrapper2.appendChild(inner2);
        chatBox.appendChild(wrapper2);
        await typeIntoElement(p2, result.oracle_message, 20);
      }
      setInputArea(`
      <button class="btn" onclick="showNextSection()">\u6B21\u306E\u30E1\u30C3\u30BB\u30FC\u30B8\u3092\u8AAD\u3080</button>
    `);
    }
    async function showNextSection() {
      const isLast = currentIndex === sections.length - 1;
      const label = isLast ? "\u6700\u5F8C\u306E\u30E1\u30C3\u30BB\u30FC\u30B8\u307E\u3067\u8AAD\u3080" : "\u6B21\u306E\u30E1\u30C3\u30BB\u30FC\u30B8\u3092\u8AAD\u3080";
      await addMsg(label, true);
      currentIndex++;
      await showCurrentSection();
    }
    window.showNextSection = showNextSection;
    await showCurrentSection();
  }

  // public/liff/src/products.ts
  function showProductCandidates() {
    if (!state.productCandidates || state.productCandidates.length === 0) {
      addMsg("\u95A2\u9023\u3059\u308B\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u5019\u88DC\u304C\u898B\u3064\u304B\u308A\u307E\u305B\u3093\u3067\u3057\u305F\u3002", false);
      return;
    }
    if (state.selectedProductIndex === null && state.productCandidates.length > 0) {
      state.selectedProductIndex = 0;
    }
    const nameForDisplay = getUserNameForDisplay();
    let html = `
    <div class="result-section">
      <h3>\u{1F48E} ${nameForDisplay}\u306B\u304A\u3059\u3059\u3081\u306E\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u5019\u88DC</h3>
      <p style="font-size:13px;margin:4px 0 10px;">
        \u4ECA\u56DE\u306E\u8A3A\u65AD\u7D50\u679C\u304B\u3089\u5C0E\u304B\u308C\u305F\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u5019\u88DC\u3067\u3059\u3002<br>
        \u6C17\u306B\u306A\u308B\u3082\u306E\u30921\u672C\u9078\u3093\u3067\u3001\u8A73\u3057\u3044\u30DA\u30FC\u30B8\u3092\u958B\u3044\u3066\u304F\u3060\u3055\u3044\u3002
      </p>
  `;
    state.productCandidates.forEach((p, idx) => {
      const isSelected = idx === state.selectedProductIndex;
      const label = p.label || p.name || p.slug || `\u5019\u88DC${idx + 1}`;
      const priceText = p.price ? `\uFF08${p.price}\u5186\uFF09` : "";
      html += `
      <button
        class="btn-toggle ${isSelected ? "active" : ""}"
        style="display:block;width:100%;text-align:left;margin:4px 0;"
        onclick="selectProductCandidate(${idx}, this)"
      >
        ${idx + 1}. ${label} ${priceText}
      </button>
    `;
    });
    html += `</div>
    <button class="btn" onclick="goToSelectedProduct()">\u{1F6D2} \u9078\u3093\u3060\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u306E\u30DA\u30FC\u30B8\u3092\u958B\u304F</button>
    <button class="btn btn-secondary" onclick="restartFromBeginning()">\u{1F504} \u3082\u3046\u4E00\u5EA6\u5360\u3046</button>
  `;
    setInputArea(html);
  }
  function selectProductCandidate(index, el) {
    state.selectedProductIndex = index;
    const container = el.parentElement;
    container?.querySelectorAll(".btn-toggle").forEach((b) => b.classList.remove("active"));
    el.classList.add("active");
  }
  function goToSelectedProduct() {
    if (!state.productCandidates || state.productCandidates.length === 0 || state.selectedProductIndex === null) {
      addMsg("\u5148\u306B\u3001\u898B\u3066\u307F\u305F\u3044\u30D6\u30EC\u30B9\u30EC\u30C3\u30C8\u30921\u672C\u9078\u3093\u3067\u304F\u3060\u3055\u3044\u3002", false);
      return;
    }
    const p = state.productCandidates[state.selectedProductIndex];
    if (p.id) {
      const diagnosisId = window.diagnosisId;
      let url = `https://spicastar.info/atlas/?p=${p.id}`;
      if (diagnosisId) {
        url += `&d=${diagnosisId}`;
      }
      window.location.href = url;
    } else {
      addMsg("\u5546\u54C1\u30DA\u30FC\u30B8\u306E\u60C5\u5831\u304C\u8DB3\u308A\u307E\u305B\u3093\u3067\u3057\u305F\u3002", false);
    }
  }
  function goLineRegister() {
    const diagnosisId = window.diagnosisId;
    const selected = state.productCandidates[state.selectedProductIndex ?? 0] || null;
    const lines = [
      "\u8A3A\u65AD\u7D50\u679C\u3092LINE\u3067\u3082\u53D7\u3051\u53D6\u308A\u305F\u3044\u3067\u3059\u3002",
      diagnosisId ? `\u8A3A\u65ADID: ${diagnosisId}` : "",
      selected && selected.id ? `\u5546\u54C1ID: ${selected.id}` : ""
    ].filter(Boolean);
    const text = encodeURIComponent(lines.join("\n"));
    window.location.href = `https://line.me/R/oaMessage/@586spjck/?${text}`;
  }

  // public/liff/src/main.ts
  window.selectMode = selectMode;
  window.nextStep = nextStep;
  window.executeDiagnose = executeDiagnose;
  window.selectGender = selectGender;
  window.toggleConcern = toggleConcern;
  window.selectStoneMethod = selectStoneMethod;
  window.showStoneOptions = showStoneOptions;
  window.selectStoneOption = selectStoneOption;
  window.confirmStoneSelection = confirmStoneSelection;
  window.showProductCandidates = showProductCandidates;
  window.selectProductCandidate = selectProductCandidate;
  window.goToSelectedProduct = goToSelectedProduct;
  window.goLineRegister = goLineRegister;
  window.selectOrderType = selectOrderType;
  window.selectWristSize = selectWristSize;
  window.selectBraceletType = selectBraceletType;
  window.selectDesign = selectDesign;
  window.buildBracelet = buildBracelet;
  window.goToProduct = goToProduct;
  window.confirmOrder = confirmOrder;
  window.restartFromBeginning = restartFromBeginning;
  window.submitTodayComment = submitTodayComment;
  async function initChatFlow() {
    state.userId = getCookie("hoshin_user_id");
    if (state.userId) {
      try {
        const res = await fetch(`/api/profile?user_id=${encodeURIComponent(state.userId)}`);
        if (res.ok) {
          const profile = await res.json();
          state.formData = { ...state.formData, ...profile };
        }
      } catch {
        console.log("profile load error");
      }
    }
    const box = document.getElementById("chatBox");
    if (box)
      box.innerHTML = "";
    const greeting = getGreetingMessage().split("\n\n");
    for (const line of greeting) {
      await addMsg(line, false);
    }
    loadProfileFromLocalStorage();
    stepModeSelect();
  }
  window.onload = async function() {
    try {
      await initLiff();
      fillOrderNote();
    } catch (e) {
      console.log("LIFF init error", e);
    }
    initStarfield();
    const logoOverlay = document.getElementById("logoOverlay");
    const fortuneGirl = document.querySelector(".fortune-girl");
    setTimeout(() => {
      if (!logoOverlay)
        return;
      logoOverlay.style.pointerEvents = "auto";
      logoOverlay.classList.add("fade-in");
    }, 300);
    const logoDisplayTime = 1800;
    const fadeDuration = 1200;
    setTimeout(() => {
      if (!logoOverlay) {
        initChatFlow();
        return;
      }
      logoOverlay.classList.remove("fade-in");
      setTimeout(() => {
        if (fortuneGirl) {
          fortuneGirl.classList.add("fade-in");
        }
        setTimeout(() => {
          logoOverlay.style.display = "none";
          logoOverlay.style.pointerEvents = "none";
          initChatFlow();
        }, fadeDuration);
      }, fadeDuration / 2);
    }, 300 + logoDisplayTime);
  };
})();
//# sourceMappingURL=bundle.js.map
