/**
 * 診断モジュール
 * AI鑑定の実行と診断結果の表示
 */

import { state } from './state';
import { addMsg, setInputArea, clearInputArea, setProgress, formatText, scrollChatToBottom } from './chat';
import { getUserNameForDisplay } from './profile';

const thinkingMessages = [
  '星の配置を読み解いています…',
  '運命の流れを確認しています…',
  'あなたに合う石を探しています…',
  'ブレスレットの構成を考えています…',
];

function rotateThinking(): void {
  const el = document.getElementById('thinkingText');
  if (!el) return;
  state.thinkingIndex = (state.thinkingIndex + 1) % thinkingMessages.length;
  el.textContent = thinkingMessages[state.thinkingIndex];
}

/** 診断を実行 */
export async function executeDiagnose(): Promise<void> {
  setProgress(3, 4, '導きの石を選定');
  const nameForDisplay = getUserNameForDisplay();
  let problem = (document.getElementById('problemText') as HTMLTextAreaElement)?.value || '';

  if (!problem) {
    problem = `具体的なご相談内容は書かれていないため、今の${nameForDisplay}の全体の流れや、これから大切にしたいテーマがわかるような全体運を中心に読み解いてください。`;
  }

  addMsg(problem, true);
  state.formData.problem = problem;

  const date = state.formData.birth?.date;
  if (!date) {
    addMsg('生年月日は必須です', false);
    return;
  }

  await addMsg('わかりました。ありがとうございます。\nこの内容で星と石の流れを読み解いていきます。\n\n少しだけお待ちくださいね。', false);

  setInputArea(`
    <div class="loading">
      <div class="spinner"></div>
      <p id="thinkingText">星の配置を読み解いています... 🌌</p>
    </div>
  `);

  const thinkingTimer = setInterval(rotateThinking, 2000);

  try {
    state.formData.line_user_id = window.LINE_USER_ID ?? state.userId ?? undefined;
    const res = await fetch('/api/diagnose', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(state.formData),
    });

    if (!res.ok) {
      throw new Error(`HTTP error ${res.status}`);
    }

    const json = await res.json();
    if (json.error) {
      clearInterval(thinkingTimer);
      addMsg(`エラーが発生しました: ${json.error}`, false);
      clearInputArea();
      return;
    }

    window.diagnosisId = json.diagnosis_id;
    state.productCandidates = json.recommendations || [];
    state.selectedProductIndex = state.productCandidates.length > 0 ? 0 : null;

    clearInterval(thinkingTimer);
    state.divinationResult = json;
    displayDivinationResult(json);
  } catch {
    clearInterval(thinkingTimer);
    addMsg('通信エラーが発生しました', false);
    clearInputArea();
  }
}

/** オラクルカードを表示 */
async function showOracleCard(card: { image_url?: string; name: string; is_upright: boolean; colors?: Record<string, string> }): Promise<void> {
  await addMsg('カードをシャッフルしています…', false);
  await new Promise(r => setTimeout(r, 1200));
  await addMsg('1枚引きます…', false);
  await new Promise(r => setTimeout(r, 1000));

  // 画像があれば表示、なければCSSグラデーションカード
  const colors = card.colors || {};
  const gradient = colors.gradient || 'linear-gradient(135deg, #1a0533 0%, #4a148c 40%, #ab47bc 100%)';
  const hasImage = card.image_url && card.image_url.length > 10;

  const imageHtml = hasImage
    ? `<img src="${card.image_url}" class="section-image" style="width:220px;margin:12px auto;display:block;border-radius:12px;" onload="this.classList.add('loaded')" onerror="this.parentElement.querySelector('.card-fallback').style.display='flex';this.style.display='none';">`
    : '';

  const fallbackStyle = hasImage ? 'display:none;' : 'display:flex;';

  const cardHtml = `
    <div class="msg bot">
      <div class="result-section" style="text-align:center;">
        <h3>🎴 オラクルカード</h3>
        ${imageHtml}
        <div class="card-fallback" style="${fallbackStyle}width:220px;height:320px;margin:12px auto;border-radius:16px;background:${gradient};align-items:center;justify-content:center;flex-direction:column;box-shadow:0 8px 24px rgba(0,0,0,0.3),inset 0 1px 0 rgba(255,255,255,0.15);border:2px solid rgba(255,215,0,0.4);">
          <div style="font-size:48px;margin-bottom:12px;">🔮</div>
          <div style="color:#fff;font-size:18px;font-weight:bold;text-shadow:0 2px 4px rgba(0,0,0,0.5);">${card.name}</div>
          <div style="color:rgba(255,255,255,0.8);font-size:14px;margin-top:6px;">${card.is_upright ? '正位置' : '逆位置'}</div>
        </div>
        <p style="font-size:17px;font-weight:bold;margin-top:10px;">
          ${card.name} ${card.is_upright ? '（正位置）' : '（逆位置）'}
        </p>
      </div>
    </div>
  `;

  const box = document.getElementById('chatBox');
  if (box) {
    box.insertAdjacentHTML('beforeend', cardHtml);
    scrollChatToBottom();
  }
}

/** セクション内タイプエフェクト */
function typeIntoElement(element: HTMLElement, rawText: string, speed = 20): Promise<void> {
  return new Promise(resolve => {
    const html = formatText(rawText || '');
    const plain = html
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<[^>]*>/g, '');
    let i = 0;
    function step(): void {
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

/** セクションカードを1枚チャットに追加してタイプアニメーションを流す */
async function appendSection(
  chatBox: HTMLElement,
  title: string,
  text: string,
  image?: string
): Promise<void> {
  const wrapper = document.createElement('div');
  wrapper.className = 'msg bot';
  const inner = document.createElement('div');
  inner.className = 'result-section';
  const h3 = document.createElement('h3');
  h3.textContent = title;
  inner.appendChild(h3);
  if (image) {
    const img = document.createElement('img');
    img.src = image;
    img.className = 'section-image';
    img.alt = title;
    img.onload = () => img.classList.add('loaded');
    img.onerror = () => img.style.display = 'none';
    inner.appendChild(img);
  }
  const p = document.createElement('p');
  inner.appendChild(p);
  wrapper.appendChild(inner);
  chatBox.appendChild(wrapper);
  scrollChatToBottom();
  await typeIntoElement(p, text, 18);
}

/** 診断結果を表示（3グループ構成・タップ回数削減版） */
async function displayDivinationResult(result: Record<string, unknown>): Promise<void> {
  setProgress(3, 4, '導きの石を選定');
  clearInputArea();
  const nameForDisplay = getUserNameForDisplay();
  const recommendations = (result.recommendations as Array<{ stones?: string[]; product_name?: string }>) || [];
  const stoneName =
    (result.stone_name as string) ||
    recommendations[0]?.stones?.[0] ||
    'あなたの石';
  const chatBox = document.getElementById('chatBox');
  if (!chatBox) return;

  const images = (result.images || {}) as Record<string, string>;
  const oracleCard = result.oracle_card as { image_url: string; name: string; is_upright: boolean } | undefined;

  // ===== グループ1: 星の地図 + これまでの流れ =====
  async function showGroup1(): Promise<void> {
    await addMsg(`星の配置とエレメントの流れをもとに、${nameForDisplay}の今を読み解いていきます。`, false);

    if (result.destiny_map) {
      await appendSection(chatBox, '✨ 星の地図', result.destiny_map as string, images.destiny_scene);
    }
    if (result.past) {
      await appendSection(chatBox, '🌙 これまでの流れ', result.past as string);
    }

    setInputArea(`
      <button class="btn" onclick="showNextSection()">続きを読む　→　今のあなたへのメッセージ</button>
    `);
  }

  // ===== グループ2: 今と未来 + エレメント + オラクルカード =====
  async function showGroup2(): Promise<void> {
    await addMsg('今のあなたの状態と、これからの流れを見ていきます。', false);

    if (result.present_future) {
      await appendSection(chatBox, '☀️ 今と、これからの流れ', result.present_future as string);
    }
    if (result.element_diagnosis) {
      await appendSection(chatBox, '🔥 エネルギーのバランス', result.element_diagnosis as string, images.element_balance);
    }

    if (oracleCard) {
      await addMsg('最後にオラクルカードを引いて、導きの声を聞いてみましょう。', false);
      await showOracleCard(oracleCard);
      if (result.oracle_message) {
        const w = document.createElement('div');
        w.className = 'msg bot';
        const inn = document.createElement('div');
        inn.className = 'result-section';
        const h = document.createElement('h3');
        h.textContent = 'オラクルからのメッセージ';
        const p = document.createElement('p');
        inn.appendChild(h);
        inn.appendChild(p);
        w.appendChild(inn);
        chatBox.appendChild(w);
        await typeIntoElement(p, result.oracle_message as string, 18);
      }
    }

    setInputArea(`
      <button class="btn" onclick="showNextSection()">続きを読む　→　石のメッセージ</button>
    `);
  }

  // ===== グループ3: 石のサポート + アドバイス + 商品へ =====
  async function showGroup3(): Promise<void> {
    await addMsg('今のあなたを整える石と、そのサポートをお伝えします。', false);

    if (result.bracelet_proposal) {
      await appendSection(chatBox, '💎 あなたに選ばれた石', result.bracelet_proposal as string, images.bracelet);
    }
    if (result.stone_support_message) {
      await appendSection(chatBox, '💐 石からのメッセージ', result.stone_support_message as string);
    }

    // アファメーション・ラッキーカラー・アドバイスをまとめて1メッセージに
    const extras: string[] = [];
    if (result.affirmation) extras.push(`✨ **${result.affirmation}**`);
    if (result.lucky_color) extras.push(`🌈 今日のラッキーカラー：**${result.lucky_color}**`);
    if (result.daily_advice) {
      const adviceList = (result.daily_advice as string).split(',').map((a: string) => `・ ${a.trim()}`).join('\n');
      extras.push(`📝 今日からできること\n${adviceList}`);
    }
    if (extras.length > 0) {
      await addMsg(extras.join('\n\n'), false);
    }

    await addMsg(
      `今回の診断で、${nameForDisplay}の軸となる石は **${stoneName}** です。\n\n`
      + `ふと迷ったとき、心が揺れたとき、そっと手首に触れてみてください。\n`
      + `**${stoneName}** の静かなエネルギーが、あなた本来のリズムを思い出させてくれます。`,
      false
    );

    setInputArea(`
      <button class="btn" onclick="showProductCandidates()">💎 あなたへのおすすめブレスレットを見る</button>
      <button class="btn btn-secondary" onclick="goLineRegister()">🔮 LINEでオラクルカードを受け取る</button>
    `);
  }

  // ===== グループ制御 =====
  let groupIndex = 0;
  const groups = [showGroup1, showGroup2, showGroup3];

  async function showNextSection(): Promise<void> {
    const labels = ['続きを読む　→　今のあなたへのメッセージ', '続きを読む　→　石のメッセージ'];
    await addMsg(labels[groupIndex] || '続きを読む', true);
    groupIndex++;
    await groups[groupIndex]?.();
  }

  window.showNextSection = showNextSection;
  await groups[0]();
}
