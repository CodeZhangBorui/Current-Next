export type User = { username: string; grade: number; classnum: number; is_active: boolean; is_staff: boolean };
export type Issue = { id: number; deadline: string; subject: string[]; leader: string; editors: string[]; responsible_editor: string; published: boolean };
export type Entry = { uuid: string; issue_id: number; filename: string; page: number; title: string; origin: string; wordcount: number; description: string; selector_name: string; reviewer_name: string; status: "pending" | "created" | "reviewed" | "selected" };
