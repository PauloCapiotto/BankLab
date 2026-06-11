export interface User {
  id: string;
  name: string;
  email: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Account {
  id: string;
  branch: string;
  number: string;
  type: string;
  balance: string;
  status: string;
}

export interface Transaction {
  id: string;
  account_id: string;
  related_account_id: string | null;
  type: "deposit" | "transfer_in" | "transfer_out";
  status: string;
  amount: string;
  description: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface TransactionList {
  items: Transaction[];
  page: number;
  page_size: number;
  total: number;
}

export interface NotificationItem {
  id: string;
  type: string;
  title: string;
  message: string;
  read_at: string | null;
  created_at: string;
}

export interface Summary {
  total_balance: string;
  monthly_inflow: string;
  monthly_outflow: string;
  unread_notifications: number;
  latest_transactions: Transaction[];
}
