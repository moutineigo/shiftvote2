import type { AllData } from './types';

const API_BASE = import.meta.env.DEV
  ? 'http://localhost:5177'
  : 'https://eigo55.sakura.ne.jp/shiftvote2-api';

async function getJson<T>(params: Record<string, string>): Promise<T> {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`${API_BASE}/?${qs}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export function fetchAll(monthKey = ''): Promise<AllData> {
  return getJson<AllData>({ action: 'all', month: monthKey });
}

export function setResponse(
  monthKey: string,
  memberId: string,
  date: string,
  value: string,
): Promise<{ ok: boolean; error?: string }> {
  return getJson({
    action: 'set',
    month_key: monthKey,
    member_id: memberId,
    date,
    value,
  });
}

export function setMemberLock(
  monthKey: string,
  memberId: string,
  locked: boolean,
): Promise<{ ok: boolean; error?: string }> {
  return getJson({
    action: 'setmemberlock',
    month_key: monthKey,
    member_id: memberId,
    locked: String(locked),
  });
}

export function setComment(
  monthKey: string,
  memberId: string,
  comment: string,
): Promise<{ ok: boolean; error?: string }> {
  return getJson({
    action: 'setcomment',
    month_key: monthKey,
    member_id: memberId,
    comment,
  });
}
