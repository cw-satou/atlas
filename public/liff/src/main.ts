/**
 * メインエントリポイント
 * 星の羅針盤「あとらす」フロントエンド
 *
 * 各モジュールからexportされた関数をwindowオブジェクトに登録し、
 * HTMLのonclickイベントから呼び出せるようにする。
 */

import { state } from './state';
import { addMsg } from './chat';
import { initStarfield } from './starfield';
import { initLiff, fillOrderNote } from './liff';
import {
  getGreetingMessage,
  getCookie,
  setCookie,
  generateUserId,
  loadProfileFromLocalStorage,
} from './profile';
import {
  stepModeSelect,
  selectMode,
  nextStep,
  selectGender,
  toggleConcern,
  selectStoneMethod,
  showStoneOptions,
  selectStoneOption,
  confirmStoneSelection,
  selectOrderType,
  restartFromBeginning,
} from './steps';
import { executeDiagnose } from './diagnose';
import { submitTodayComment } from './fortune';
import {
  selectWristSize,
  selectBraceletType,
  selectDesign,
  buildBracelet,
  goToProduct,
  confirmOrder,
} from './bracelet';
import {
  showProductCandidates,
  selectProductCandidate,
  goToSelectedProduct,
  goLineRegister,
} from './products';

// ===== HTMLのonclickから呼び出す関数をwindowに登録 =====
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

// ===== 初期化 =====

async function initChatFlow(): Promise<void> {
  // LINE IDを優先、なければCookieから取得、それもなければ新規生成して保存
  if (window.LINE_USER_ID) {
    state.userId = window.LINE_USER_ID;
    setCookie('hoshin_user_id', state.userId);
  } else {
    state.userId = getCookie('hoshin_user_id');
    if (!state.userId) {
      state.userId = generateUserId();
      setCookie('hoshin_user_id', state.userId);
    }
  }

  if (state.userId) {
    try {
      const res = await fetch(`/api/profile?user_id=${encodeURIComponent(state.userId)}`);
      if (res.ok) {
        const profile = await res.json();
        state.formData = { ...state.formData, ...profile };
      }
    } catch {
      console.log('profile load error');
    }
  }

  const box = document.getElementById('chatBox');
  if (box) box.innerHTML = '';

  const greeting = getGreetingMessage().split('\n\n');
  for (const line of greeting) {
    await addMsg(line, false);
  }

  loadProfileFromLocalStorage();
  stepModeSelect();
}

window.onload = async function (): Promise<void> {
  try {
    await initLiff();
    fillOrderNote();
  } catch (e) {
    console.log('LIFF init error', e);
  }

  // 星空アニメーション開始
  initStarfield();

  const logoOverlay = document.getElementById('logoOverlay');
  const fortuneGirl = document.querySelector('.fortune-girl') as HTMLElement | null;

  // 1. ロゴをフェードイン
  setTimeout(() => {
    if (!logoOverlay) return;
    logoOverlay.style.pointerEvents = 'auto';
    logoOverlay.classList.add('fade-in');
  }, 300);

  const logoDisplayTime = 1800;
  const fadeDuration = 1200;

  // 2. ロゴ表示キープ → フェードアウト → 背景フェードイン → 会話開始
  setTimeout(() => {
    if (!logoOverlay) {
      initChatFlow();
      return;
    }
    logoOverlay.classList.remove('fade-in');

    setTimeout(() => {
      if (fortuneGirl) {
        fortuneGirl.classList.add('fade-in');
      }
      setTimeout(() => {
        logoOverlay.style.display = 'none';
        logoOverlay.style.pointerEvents = 'none';
        initChatFlow();
      }, fadeDuration);
    }, fadeDuration / 2);
  }, 300 + logoDisplayTime);
};
