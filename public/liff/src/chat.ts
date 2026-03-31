/**
 * チャットUI管理
 * メッセージの表示、タイピングエフェクト、スクロール制御
 */

import { state } from './state';

/** チャットボックスの最下部にスクロール */
export function scrollChatToBottom(): void {
  const box = document.getElementById('chatBox');
  if (!box) return;
  box.scrollTop = box.scrollHeight;
}

/** テキストのフォーマット（Markdown風の強調変換） */
export function formatText(text: string): string {
  if (!text) return '';
  const decoded = text
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&');
  return decoded.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
}

/**
 * HTML対応タイピングエフェクト
 * HTMLタグ（<br>・<strong>等）は即時挿入し、テキスト文字だけを1文字ずつ表示する。
 * これにより太字・改行がタイプ中から正しく描画される。
 */
export function typeHtml(element: HTMLElement, html: string, speed = 40): Promise<void> {
  return new Promise((resolve) => {
    // HTMLをトークン列に分解: タグ全体 or テキスト1文字
    const tokens: string[] = [];
    const re = /(<[^>]+\/?>|<\/[^>]+>)|([^<])/g;
    let m: RegExpExecArray | null;
    while ((m = re.exec(html)) !== null) {
      tokens.push(m[0]);
    }

    let i = 0;
    let current = '';

    function type(): void {
      // HTMLタグはまとめて即時挿入（タグ文字を1文字ずつ表示しない）
      while (i < tokens.length && tokens[i].startsWith('<')) {
        current += tokens[i];
        i++;
      }
      if (i < tokens.length) {
        current += tokens[i];
        i++;
        element.innerHTML = current;
        scrollChatToBottom();
        setTimeout(type, speed);
      } else {
        element.innerHTML = html;
        scrollChatToBottom();
        resolve();
      }
    }
    type();
  });
}

/** タイピングエフェクト付きテキスト表示（フォーマット済みHTMLを受け取る） */
export function typeText(element: HTMLElement, text: string, speed = 40): Promise<void> {
  return typeHtml(element, text, speed);
}

/** メッセージをチャットに追加（キュー制御付き、メッセージ間に1秒の間） */
export function addMsg(text: string, isUser = false): Promise<void> {
  state.messageQueue = state.messageQueue
    .then(() => new Promise<void>(r => setTimeout(r, isUser ? 300 : 1000)))
    .then(() => renderMessage(text, isUser));
  return state.messageQueue;
}

/** メッセージを描画する */
function renderMessage(text: string, isUser: boolean): Promise<void> {
  return new Promise((resolve) => {
    const box = document.getElementById('chatBox');
    if (!box) { resolve(); return; }

    const div = document.createElement('div');
    div.className = `msg ${isUser ? 'user' : 'bot'}`;
    box.appendChild(div);

    const formatted = formatText(text.replace(/\n/g, '<br>'));

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

/** 入力エリアにHTMLを設定 */
export function setInputArea(html: string): void {
  const el = document.getElementById('inputArea');
  if (el) el.innerHTML = html;
  scrollChatToBottom();
}

/** 入力エリアをクリア */
export function clearInputArea(): void {
  setInputArea('');
}

/** プログレスバーを更新 */
export function setProgress(step: number, total: number, label: string): void {
  const el = document.getElementById('progressBar');
  if (el) {
    el.innerHTML = `STEP ${step} / ${total}<br>${label}`;
  }
}
