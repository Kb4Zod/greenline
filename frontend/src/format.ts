const money = new Intl.NumberFormat("en-US", {
  style: "currency",
  currency: "USD",
});

export function fmtMoney(cents: number): string {
  return money.format(cents / 100);
}

export function fmtDate(iso: string): string {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d).toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

export const CADENCE_LABEL: Record<string, string> = {
  weekly: "weekly",
  biweekly: "every 2 weeks",
  semimonthly: "twice a month",
  monthly: "monthly",
  quarterly: "quarterly",
  annual: "yearly",
};
