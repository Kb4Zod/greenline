import { useEffect, useState } from "react";
import { api } from "../api";
import type { Forecast, Status, WindowForecast } from "../types";
import { fmtDate, fmtMoney } from "../format";

const STATUS_COLOR: Record<Status, string> = {
  covered: "var(--color-go)",
  tight: "var(--color-hold)",
  shortfall: "var(--color-stop)",
};
const STATUS_GLOW: Record<Status, string> = {
  covered: "rgba(74, 222, 128, 0.45)",
  tight: "rgba(251, 191, 36, 0.4)",
  shortfall: "rgba(248, 113, 113, 0.4)",
};
const STATUS_WORD: Record<Status, string> = {
  covered: "Covered",
  tight: "Tight",
  shortfall: "Shortfall",
};

export default function CheckIn() {
  const [forecast, setForecast] = useState<Forecast | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeDays, setActiveDays] = useState(7);
  const [showAccounts, setShowAccounts] = useState(false);

  useEffect(() => {
    api.forecast().then(setForecast).catch(() => setError("Backend unreachable — is the API running?"));
  }, []);

  if (error) return <p className="text-stop">{error}</p>;
  if (!forecast) return null; // local app: data arrives in ms, skeletons would just flicker

  if (forecast.accounts.length === 0) return <EmptyState />;

  const active = forecast.windows.find((w) => w.days === activeDays) ?? forecast.windows[0];
  // The page's overall mood follows the active window.
  const mood = active.status;

  return (
    <main>
      {/* Hero: cash on hand over its green line */}
      <section className="rise">
        <p className="text-paper-dim text-sm tracking-widest uppercase">Cash on hand</p>
        <button
          onClick={() => setShowAccounts((v) => !v)}
          className="block text-left cursor-pointer"
          title="Show per-account split"
        >
          <span className="money block text-7xl mt-2 mb-4 text-paper">
            {fmtMoney(forecast.cash_on_hand_cents)}
          </span>
        </button>
        <hr
          className="greenline"
          style={{
            ["--line-color" as string]: STATUS_COLOR[mood],
            ["--line-glow" as string]: STATUS_GLOW[mood],
          }}
        />
        {showAccounts && (
          <ul className="mt-3 text-sm text-paper-dim">
            {forecast.accounts.map((a) => (
              <li key={a.id} className="flex justify-between py-0.5">
                <span>
                  {a.name} <span className="text-paper-faint">· {a.institution}</span>
                </span>
                <span className="money">{fmtMoney(a.balance_cents)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Review nudge — the first-run ritual */}
      {forecast.pending_review > 0 && (
        <a
          href="#/bills"
          className="rise mt-6 inline-flex items-center gap-2 rounded-full border border-hold/40 bg-hold/10 px-4 py-1.5 text-sm text-hold"
          style={{ animationDelay: "80ms" }}
        >
          ● {forecast.pending_review} detected bill{forecast.pending_review > 1 ? "s" : ""} await review
        </a>
      )}

      {/* The three windows */}
      <section className="mt-10 grid grid-cols-3 gap-3">
        {forecast.windows.map((w, i) => (
          <WindowCard
            key={w.days}
            window={w}
            active={w.days === active.days}
            onSelect={() => setActiveDays(w.days)}
            delay={120 + i * 70}
          />
        ))}
      </section>

      {/* Basis for the active window — progressive disclosure */}
      <section className="rise mt-6" style={{ animationDelay: "330ms" }}>
        {active.due.length === 0 ? (
          <p className="text-paper-faint text-sm">
            No confirmed bills due in the next {active.days} days.
          </p>
        ) : (
          <ul className="divide-y divide-ink-line rounded-xl bg-ink-raised px-4">
            {active.due.map((item, i) => (
              <li key={`${item.bill_id}-${item.due}-${i}`} className="flex justify-between py-2.5 text-sm">
                <span className="text-paper">{item.name}</span>
                <span className="text-paper-dim">
                  {fmtDate(item.due)}
                  <span className="money ml-4 text-paper">{fmtMoney(item.amount_cents)}</span>
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* Payday line */}
      <section className="rise mt-10 text-sm text-paper-dim" style={{ animationDelay: "400ms" }}>
        {forecast.income.map((s) => (
          <p key={s.id} className={s.overdue ? "text-hold" : ""}>
            {s.overdue ? "⚠ Expected paycheck overdue — " : "Next payday: "}
            <span className="text-paper">{fmtDate(s.next_expected)}</span>
            {" · "}
            <span className="money text-paper">~{fmtMoney(s.expected_cents)}</span>
            <span className="text-paper-faint"> (avg of last {s.basis_n})</span>
          </p>
        ))}
        <p className="mt-2 text-paper-faint">As of {fmtDate(forecast.as_of)}</p>
      </section>
    </main>
  );
}

function WindowCard({
  window: w,
  active,
  onSelect,
  delay,
}: {
  window: WindowForecast;
  active: boolean;
  onSelect: () => void;
  delay: number;
}) {
  return (
    <button
      onClick={onSelect}
      className={
        "rise rounded-xl px-4 py-4 text-left transition-colors cursor-pointer " +
        (active ? "bg-ink-raised ring-1 ring-ink-line" : "hover:bg-ink-raised/60")
      }
      style={{ animationDelay: `${delay}ms` }}
    >
      <p className="text-paper-faint text-xs tracking-widest uppercase">{w.days} days</p>
      <p className="money mt-2 text-2xl text-paper">{fmtMoney(w.required_cents)}</p>
      <p className="mt-1 text-xs text-paper-dim">required</p>
      <p className="mt-3 text-sm" style={{ color: STATUS_COLOR[w.status] }}>
        {STATUS_WORD[w.status]}
        <span className="money text-paper-dim ml-2">
          {w.headroom_cents >= 0 ? "+" : "−"}
          {fmtMoney(Math.abs(w.headroom_cents))}
        </span>
      </p>
    </button>
  );
}

function EmptyState() {
  return (
    <main className="rise mt-16 text-center">
      <p className="text-2xl text-paper">Nothing here yet.</p>
      <p className="mt-3 text-paper-dim">
        Import your first bank statement to see your forecast.
      </p>
      <a
        href="#/import"
        className="mt-8 inline-block rounded-full bg-go/15 border border-go/40 px-6 py-2 text-go"
      >
        Import a CSV →
      </a>
    </main>
  );
}
