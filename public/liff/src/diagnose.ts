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
    state.productCandidates = json.products || [];
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
async function showOracleCard(card: { image_url: string; name: string; is_upright: boolean }): Promise<void> {
  await addMsg('カードをシャッフルしています…', false);
  await new Promise(r => setTimeout(r, 1200));
  await addMsg('1枚引きます…', false);
  await new Promise(r => setTimeout(r, 1000));

  const cardHtml = `
    <div class="msg bot">
      <div class="result-section" style="text-align:center;">
        <h3>🎴 オラクルカード</h3>
        <img src="${card.image_url}"
          class="section-image"
          style="width:200px;margin:12px auto;display:block;"
          onload="this.classList.add('loaded')"
          onerror="this.style.display='none'">
        <p style="font-size:16px;font-weight:bold;margin-top:8px;">
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

/** 診断結果を表示 */
async function displayDivinationResult(result: Record<string, unknown>): Promise<void> {
  setProgress(3, 4, '導きの石を選定');
  clearInputArea();
  const nameForDisplay = getUserNameForDisplay();
  const stoneName =
    (result.stone_name as string) ||
    ((result.stones_for_user as Array<{ name: string }>)?.[0]?.name || 'あなたの石');
  const chatBox = document.getElementById('chatBox');
  if (!chatBox) return;

  // 画像情報
  const images = (result.images || {}) as Record<string, string>;

  const sections = [
    { key: 'destiny_map', title: '✨ 運命の地図', text: result.destiny_map as string, lead: 'まずは、あなた全体のテーマや流れを地図のように見ていきますね。', image: images.destiny_scene },
    { key: 'past', title: '🌙 これまでの流れ', text: result.past as string, lead: '次に、あなたがこれまでどんな資質や流れを持って歩いてきたのかを読み解いていきます。' },
    { key: 'present_future', title: '☀️ 今と未来への流れ', text: result.present_future as string, lead: '次に、あなたの今とこれからの流れを見ていきます。' },
    { key: 'element_diagnosis', title: '🔥 エレメントのバランス', text: result.element_diagnosis as string, lead: '次は、火・地・風・水のバランスから見ていきます。', image: images.element_balance },
    { key: 'bracelet_proposal', title: '💎 石の選び方と意図', text: result.bracelet_proposal as string, lead: 'ここからは石の組み合わせの意図を見ていきます。', image: images.bracelet },
    { key: 'stone_support_message', title: '💐 石からのサポートメッセージ', text: result.stone_support_message as string, lead: '石たちのメッセージをお伝えします。' },
  ].filter(sec => sec.text);

  let currentIndex = 0;

  await addMsg(`ここからは、星の配置とエレメントの流れをもとに、\n${nameForDisplay}の今の流れを読み解いていきます。`, false);

  async function showCurrentSection(): Promise<void> {
    if (currentIndex >= sections.length) {
      // 追加セクション: アファメーション、ラッキーカラー、アドバイス
      const extras: string[] = [];
      if (result.affirmation) {
        extras.push(`\n✨ あなたへの言葉\n${result.affirmation}`);
      }
      if (result.lucky_color) {
        extras.push(`🌈 ラッキーカラー: **${result.lucky_color}**`);
      }
      if (result.daily_advice) {
        extras.push(`\n📝 今日からできること\n${(result.daily_advice as string).split(',').map((a: string) => `・ ${a.trim()}`).join('\n')}`);
      }
      if (extras.length > 0) {
        await addMsg(extras.join('\n\n'), false);
      }

      await addMsg('ここまでの流れから、今のあなたを整える石が見えてきました。', false);
      await addMsg(`今回の診断であなたの軸となる石は **${stoneName}** です。`, false);
      await addMsg(
        `この石は、あなたの星の配置と今の心の波長から導き出されたものです。\n\n`
        + `ふと迷ったとき、心が揺れたとき、そっと手首に触れてみてください。\n`
        + `**${stoneName}**の静かなエネルギーが、あなた本来のリズムを思い出させてくれるはずです。`,
        false
      );
      await addMsg('もしこの石たちと一緒に歩いてみたいと感じたなら、あなたのためのブレスレットとして形にしてみましょう。', false);
      setInputArea(`
        <button class="btn" onclick="showProductCandidates()">💎 診断結果からブレスレット候補を見る</button>
        <button class="btn btn-secondary" onclick="goLineRegister()">🔮 LINEでオラクルカードを受け取る</button>
      `);
      return;
    }

    const sec = sections[currentIndex];
    if (sec.lead) {
      await addMsg(sec.lead, false);
    }

    const wrapper = document.createElement('div');
    wrapper.className = 'msg bot';
    const inner = document.createElement('div');
    inner.className = 'result-section';
    const h3 = document.createElement('h3');
    h3.textContent = sec.title;

    // セクションに対応するイメージ画像があれば表示
    inner.appendChild(h3);
    if (sec.image) {
      const img = document.createElement('img');
      img.src = sec.image;
      img.className = 'section-image';
      img.alt = sec.title;
      img.onload = () => img.classList.add('loaded');
      img.onerror = () => img.style.display = 'none';
      inner.appendChild(img);
    }

    const p = document.createElement('p');
    inner.appendChild(p);
    wrapper.appendChild(inner);
    chatBox.appendChild(wrapper);
    scrollChatToBottom();

    await typeIntoElement(p, sec.text, 20);

    if (sec.key === 'element_diagnosis') {
      await addMsg('最後にオラクルカードを引いて、導きの声を聞いてみましょう。', false);
      const oracleCard = result.oracle_card as { image_url: string; name: string; is_upright: boolean } | undefined;
      if (oracleCard) {
        await showOracleCard(oracleCard);
      }

      const wrapper2 = document.createElement('div');
      wrapper2.className = 'msg bot';
      const inner2 = document.createElement('div');
      inner2.className = 'result-section';
      const h3b = document.createElement('h3');
      h3b.textContent = 'オラクルからのメッセージ';
      const p2 = document.createElement('p');
      inner2.appendChild(h3b);
      inner2.appendChild(p2);
      wrapper2.appendChild(inner2);
      chatBox.appendChild(wrapper2);
      await typeIntoElement(p2, result.oracle_message as string, 20);
    }

    setInputArea(`
      <button class="btn" onclick="showNextSection()">次のメッセージを読む</button>
    `);
  }

  async function showNextSection(): Promise<void> {
    const isLast = currentIndex === sections.length - 1;
    const label = isLast ? '最後のメッセージまで読む' : '次のメッセージを読む';
    await addMsg(label, true);
    currentIndex++;
    await showCurrentSection();
  }

  window.showNextSection = showNextSection;
  await showCurrentSection();
}
