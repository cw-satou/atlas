/**
 * 商品選択モジュール
 * マッチングエンジンが返した上位3商品をカード形式で表示する。
 * 既存のCSSクラス・世界観をそのまま使用する。
 */

import { state } from './state';
import { addMsg, setInputArea } from './chat';
import { getUserNameForDisplay } from './profile';

/** 推薦商品の型（APIレスポンスに合わせた形式） */
interface Recommendation {
  rank: number;
  score: number;
  score_breakdown?: { element: number; aura: number; theme: number; worry: number };
  woo_product_id: number;
  sku: string;
  product_name: string;
  price: string | number;
  image_url: string;
  generated_image_url?: string | null;
  product_url: string;
  stones: string[];
  recommendation_reason: string;
  oracle_card?: { name: string; is_upright: boolean };
  diagnosis_message?: string;
}

/** 一致率バーと内訳HTML */
function buildScoreBar(score: number, breakdown?: { element: number; aura: number; theme: number; worry: number }): string {
  const pct = Math.min(100, Math.round(score));
  const breakdownHtml = breakdown ? `
    <div style="margin-top:10px;border-top:1px solid #e8dcc8;padding-top:8px;">
      <div style="font-size:11px;color:#888;margin-bottom:6px;">内訳</div>
      ${[
        ['星座相性', breakdown.element, '#c8860b'],
        ['オーラ', breakdown.aura, '#9b6b3a'],
        ['テーマ', breakdown.theme, '#7a9e4e'],
        ['悩み', breakdown.worry, '#6b5b9e'],
      ].map(([label, val, color]) => {
        const v = Math.min(100, Math.round(val as number));
        return `
          <div style="margin-bottom:5px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:2px;">
              <span style="font-size:11px;color:#666;">${label}</span>
              <span style="font-size:11px;font-weight:600;color:${color};">${v}%</span>
            </div>
            <div style="background:#e8e8e8;border-radius:4px;height:5px;overflow:hidden;">
              <div style="width:${v}%;height:100%;background:${color};border-radius:4px;transition:width .6s ease;"></div>
            </div>
          </div>
        `;
      }).join('')}
    </div>
  ` : '';
  return `
    <div style="margin:6px 0 2px;">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
        <span style="font-size:12px;color:#666;">星読み一致率</span>
        <span style="font-size:13px;font-weight:600;color:#222;">${pct}%</span>
      </div>
      <div style="background:#e8e8e8;border-radius:6px;height:6px;overflow:hidden;">
        <div style="width:${pct}%;height:100%;background:linear-gradient(90deg,#b8860b,#daa520);border-radius:6px;transition:width .6s ease;"></div>
      </div>
      ${breakdownHtml}
    </div>
  `;
}

/** 商品1枚分のカードHTML（既存の result-section クラスを使用） */
function buildProductCard(rec: Recommendation, idx: number, isSelected: boolean): string {
  const rank = rec.rank ?? idx + 1;
  const rankLabel = rank === 1 ? '✨ 第1位' : rank === 2 ? '🌙 第2位' : '⭐ 第3位';
  const priceText = rec.price ? `¥${Number(rec.price).toLocaleString()}` : '';
  const stonesText = (rec.stones || []).join(' × ') || '—';
  const reason = rec.recommendation_reason || 'あなたの星読みに共鳴する構成です';

  // Gemini生成画像を優先、なければWooCommerce画像
  const displayImageUrl = rec.generated_image_url || rec.image_url || '';
  const imageHtml = displayImageUrl
    ? `<img
         src="${displayImageUrl}"
         alt="${rec.product_name || ''}"
         style="width:100%;max-height:160px;object-fit:cover;border-radius:10px;margin:8px 0;"
         onerror="this.style.display='none'"
       >`
    : '';

  const activeStyle = isSelected
    ? 'border:2px solid #b8860b;box-shadow:0 0 12px rgba(184,134,11,0.35);'
    : 'border:1px solid #ddd;';

  return `
    <div
      class="product-card"
      style="background:rgba(255,248,235,0.9);border-radius:14px;padding:14px;margin-bottom:10px;cursor:pointer;transition:all .15s ease;${activeStyle}"
      onclick="selectProductCandidate(${idx}, this)"
    >
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
        <span style="font-size:15px;font-weight:700;color:#222;">${rankLabel}</span>
        ${priceText ? `<span style="font-size:14px;font-weight:600;color:#555;">${priceText}</span>` : ''}
      </div>
      ${imageHtml}
      <p style="font-size:15px;font-weight:600;color:#222;margin:4px 0 6px;line-height:1.5;">${rec.product_name || rec.sku || `候補${rank}`}</p>
      <p style="font-size:13px;color:#666;margin:0 0 6px;">使用石：${stonesText}</p>
      ${buildScoreBar(rec.score || 0, rec.score_breakdown)}
      <p style="font-size:13px;color:#444;margin-top:8px;line-height:1.6;">${reason}</p>
    </div>
  `;
}

/** 推薦ブレスレット候補を表示 */
export function showProductCandidates(): void {
  const recs = state.productCandidates as unknown as Recommendation[];

  if (!recs || recs.length === 0) {
    addMsg('関連するブレスレット候補が見つかりませんでした。', false);
    return;
  }

  if (state.selectedProductIndex === null && recs.length > 0) {
    state.selectedProductIndex = 0;
  }

  const nameForDisplay = getUserNameForDisplay();

  let cardsHtml = '';
  recs.forEach((rec, idx) => {
    cardsHtml += buildProductCard(rec, idx, idx === state.selectedProductIndex);
  });

  const html = `
    <div class="result-section" style="padding:0;">
      <h3 style="margin-bottom:6px;font-size:15px;">💎 ${nameForDisplay}へのおすすめブレスレット</h3>
      <p style="font-size:13px;color:#666;margin-bottom:12px;line-height:1.6;">
        星読みの結果から、最もあなたに共鳴する3つをお選びしました。<br>
        気になる1本を選んで、詳しいページをご覧ください。
      </p>
      ${cardsHtml}
    </div>
    <button class="btn" onclick="goToSelectedProduct()">🛒 選んだブレスレットのページへ</button>
    <button class="btn btn-secondary" onclick="restartFromBeginning()">🔄 もう一度診断する</button>
  `;

  setInputArea(html);
}

/** 商品カードを選択 */
export function selectProductCandidate(index: number, el: HTMLElement): void {
  state.selectedProductIndex = index;

  // カード全体の親を検索してスタイルをリセット
  const container = el.closest('.result-section') || el.parentElement;
  container?.querySelectorAll('.product-card').forEach(card => {
    (card as HTMLElement).style.border = '1px solid #ddd';
    (card as HTMLElement).style.boxShadow = 'none';
  });
  el.style.border = '2px solid #b8860b';
  el.style.boxShadow = '0 0 12px rgba(184,134,11,0.35)';
}

/** 選択したブレスレットのページへ遷移 */
export function goToSelectedProduct(): void {
  const recs = state.productCandidates as unknown as Recommendation[];

  if (!recs || recs.length === 0 || state.selectedProductIndex === null) {
    addMsg('先に、見てみたいブレスレットを1本選んでください。', false);
    return;
  }

  const rec = recs[state.selectedProductIndex];
  if (!rec) {
    addMsg('先に、見てみたいブレスレットを1本選んでください。', false);
    return;
  }

  const diagnosisId = window.diagnosisId;

  if (rec.product_url) {
    const url = diagnosisId
      ? `${rec.product_url}${rec.product_url.includes('?') ? '&' : '?'}d=${diagnosisId}`
      : rec.product_url;
    window.location.href = url;
  } else if (rec.woo_product_id) {
    const base = `https://spicastar.info/atlas/?p=${rec.woo_product_id}`;
    const url = diagnosisId ? `${base}&d=${diagnosisId}` : base;
    window.location.href = url;
  } else {
    addMsg('商品ページの情報が見つかりませんでした。', false);
  }
}

/** LINE登録ページへ遷移 */
export function goLineRegister(): void {
  const diagnosisId = window.diagnosisId;
  const recs = state.productCandidates as unknown as Recommendation[];
  const selected = recs?.[state.selectedProductIndex ?? 0] ?? null;

  const lines = [
    '診断結果をLINEでも受け取りたいです。',
    diagnosisId ? `診断ID: ${diagnosisId}` : '',
    selected?.woo_product_id ? `商品ID: ${selected.woo_product_id}` : '',
  ].filter(Boolean);

  const text = encodeURIComponent(lines.join('\n'));
  window.location.href = `https://line.me/R/oaMessage/@586spjck/?${text}`;
}
