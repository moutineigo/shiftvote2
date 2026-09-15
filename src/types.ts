export interface Member {
  member_id: string;
  member_name: string;
  locked: boolean;
}

export interface DateEntry {
  date: string;
  weekday: string;
  time: string;
  place: string;
  note: string;
}

export interface Meta {
  ok: boolean;
  month_key: string;
  title: string;
  deadline: string;
  note: string;
  ui_refresh_sec: number;
  choices: string[];
  members: Member[];
  dates: DateEntry[];
  warning?: string;
  error?: string;
}

export interface Response {
  member_id: string;
  date: string;
  value: string;
  updated_at: string;
}

export interface Comment {
  month_key: string;
  member_id: string;
  comment: string;
  updated_at: string;
}

export interface AllData {
  ok: boolean;
  meta: Meta;
  responses: Response[];
  comments: Comment[];
  error?: string;
}
