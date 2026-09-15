import './style.css';
import { fetchAll, setResponse, setMemberLock, setComment } from './api';
import type { AllData } from './types';

const app = document.getElementById('app')!;
const LS_KEY = 'shiftvote2:member_id';

let data: AllData | null = null;
let selectedMemberId: string | null = localStorage.getItem(LS_KEY);
let refreshTimer: number | undefined;
let commentSaveTimer: number | undefined;

function valueClass(v: string): string {
  switch (v) {
    case '〇':
      return 'val-maru';
    case '×':
      return 'val-batsu';
    case '△':
      return 'val-sankaku';
    case '？':
      return 'val-hatena';
    default:
      return '';
  }
}

async function load(showSpinner: boolean) {
  if (showSpinner) app.textContent = '読み込み中...';
  try {
    const monthParam = new URLSearchParams(location.search).get('month') || '';
    const result = await fetchAll(monthParam);
    if (!result.ok) throw new Error(result.error || '取得に失敗しました');
    data = result;
    if (selectedMemberId && !data.meta.members.some((m) => m.member_id === selectedMemberId)) {
      selectedMemberId = null;
    }
    render();
    scheduleRefresh();
  } catch (err) {
    app.innerHTML = `<div class="error-box">読み込みに失敗しました: ${escapeHtml(String(err))}</div>`;
  }
}

function scheduleRefresh() {
  if (refreshTimer) window.clearTimeout(refreshTimer);
  const sec = data?.meta.ui_refresh_sec || 60;
  refreshTimer = window.setTimeout(() => load(false), Math.max(sec, 15) * 1000);
}

function escapeHtml(s: string): string {
  const d = document.createElement('div');
  d.textContent = s;
  return d.innerHTML;
}

function render() {
  if (!data) return;
  const meta = data.meta;

  const responseMap = new Map<string, string>();
  for (const r of data.responses) responseMap.set(`${r.member_id}|${r.date}`, r.value);

  const commentMap = new Map<string, string>();
  for (const c of data.comments) commentMap.set(c.member_id, c.comment);

  const selfMember = meta.members.find((m) => m.member_id === selectedMemberId) || null;

  app.innerHTML = `
    <header class="top">
      <h1>${escapeHtml(meta.title || 'シフト入力')}</h1>
      ${meta.deadline ? `<p class="sub">回答締切: ${escapeHtml(meta.deadline)}</p>` : ''}
      ${meta.note ? `<p class="sub">${escapeHtml(meta.note)}</p>` : ''}
    </header>

    <div class="panel member-picker">
      <label for="member-select">自分の名前:</label>
      <select id="member-select">
        <option value="">選択してください</option>
        ${meta.members
          .map(
            (m) =>
              `<option value="${m.member_id}" ${m.member_id === selectedMemberId ? 'selected' : ''}>${escapeHtml(m.member_name)}</option>`,
          )
          .join('')}
      </select>
      ${
        selfMember
          ? `<label class="lock-toggle">
              <input type="checkbox" id="lock-checkbox" ${selfMember.locked ? 'checked' : ''} />
              入力を確定してロックする
            </label>`
          : ''
      }
    </div>

    <div class="table-scroll">
      <table class="shift">
        <thead>
          <tr>
            <th class="date-col">日程</th>
            ${meta.members
              .map(
                (m) =>
                  `<th class="member-col${m.member_id === selectedMemberId ? ' selected' : ''}">${escapeHtml(m.member_name)}${m.locked ? '🔒' : ''}</th>`,
              )
              .join('')}
          </tr>
        </thead>
        <tbody>
          ${meta.dates
            .map((d) => {
              const cells = meta.members
                .map((m) => {
                  const v = responseMap.get(`${m.member_id}|${d.date}`) || 'ー';
                  const editable = m.member_id === selectedMemberId && !m.locked;
                  const cls = `member-col${m.member_id === selectedMemberId ? ' selected' : ''}${m.locked ? ' locked' : ''}`;
                  return `<td class="${cls}">
                    <button type="button" class="${valueClass(v)}" data-date="${d.date}" ${editable ? '' : 'disabled'}>${escapeHtml(v)}</button>
                  </td>`;
                })
                .join('');
              return `<tr>
                <td class="date-col">
                  ${escapeHtml(d.date)}（${escapeHtml(d.weekday)}）${d.time ? ' ' + escapeHtml(d.time) : ''}
                  ${d.place ? `<div class="place">${escapeHtml(d.place)}${d.note ? ' ・ ' + escapeHtml(d.note) : ''}</div>` : ''}
                </td>
                ${cells}
              </tr>`;
            })
            .join('')}
        </tbody>
      </table>
    </div>

    <div class="legend">
      ${meta.choices.map((c) => `<span class="${valueClass(c)}">${escapeHtml(c)}</span>`).join(' ')}
      <span>セルをタップで切り替わります（自分の列のみ）</span>
    </div>

    ${
      selfMember
        ? `<div class="panel">
            <label for="comment-box">コメント（${escapeHtml(selfMember.member_name)}）</label>
            <textarea id="comment-box" class="comment" placeholder="連絡事項など">${escapeHtml(commentMap.get(selfMember.member_id) || '')}</textarea>
            <div class="save-status" id="comment-status"></div>
          </div>`
        : ''
    }
  `;

  wireEvents();
}

function wireEvents() {
  if (!data) return;
  const meta = data.meta;

  const select = document.getElementById('member-select') as HTMLSelectElement | null;
  select?.addEventListener('change', () => {
    selectedMemberId = select.value || null;
    if (selectedMemberId) localStorage.setItem(LS_KEY, selectedMemberId);
    else localStorage.removeItem(LS_KEY);
    render();
  });

  const lockBox = document.getElementById('lock-checkbox') as HTMLInputElement | null;
  lockBox?.addEventListener('change', async () => {
    if (!selectedMemberId) return;
    lockBox.disabled = true;
    const result = await setMemberLock(meta.month_key, selectedMemberId, lockBox.checked);
    if (!result.ok) {
      alert('ロックの更新に失敗しました: ' + (result.error || ''));
    }
    await load(false);
  });

  document.querySelectorAll<HTMLButtonElement>('table.shift button[data-date]').forEach((btn) => {
    btn.addEventListener('click', async () => {
      if (!selectedMemberId) return;
      const date = btn.dataset.date!;
      const current = btn.textContent?.trim() || 'ー';
      const choices = meta.choices;
      const idx = choices.indexOf(current);
      const next = choices[(idx + 1) % choices.length];

      btn.textContent = next;
      btn.className = valueClass(next);
      btn.disabled = true;

      const result = await setResponse(meta.month_key, selectedMemberId, date, next);
      btn.disabled = false;
      if (!result.ok) {
        alert('保存に失敗しました: ' + (result.error || ''));
        btn.textContent = current;
        btn.className = valueClass(current);
        return;
      }
      const existing = data!.responses.find((r) => r.member_id === selectedMemberId && r.date === date);
      if (existing) existing.value = next;
      else data!.responses.push({ member_id: selectedMemberId, date, value: next, updated_at: new Date().toISOString() });
    });
  });

  const commentBox = document.getElementById('comment-box') as HTMLTextAreaElement | null;
  const commentStatus = document.getElementById('comment-status');
  commentBox?.addEventListener('input', () => {
    if (!selectedMemberId) return;
    if (commentSaveTimer) window.clearTimeout(commentSaveTimer);
    if (commentStatus) commentStatus.textContent = '入力中...';
    commentSaveTimer = window.setTimeout(async () => {
      if (!selectedMemberId) return;
      const result = await setComment(meta.month_key, selectedMemberId, commentBox.value);
      if (commentStatus) {
        commentStatus.textContent = result.ok
          ? '保存しました'
          : '保存に失敗しました: ' + (result.error || '');
      }
    }, 800);
  });
}

void (async () => {
  await load(true);
})();
