import { useEffect, useState } from "react";
import { api } from "../api";
import type { Bill, BillStatus, Cadence } from "../types";
import { CADENCE_LABEL, fmtDate, fmtMoney } from "../format";

export default function Bills() {
  const [bills, setBills] = useState<Bill[] | null>(null);
  const [adding, setAdding] = useState(false);

  const refresh = () => api.bills().then(setBills);
  useEffect(() => {
    refresh();
  }, []);

  if (!bills) return null;

  const drafts = bills.filter((b) => b.status === "detected");
  const confirmed = bills.filter((b) => b.status === "confirmed");
  const dismissed = bills.filter((b) => b.status === "dismissed");

  // Optimistic: flip locally, then sync. Local app — conflicts are not a thing.
  const setStatus = (bill: Bill, status: BillStatus) => {
    setBills((prev) =>
      prev!.map((b) => (b.id === bill.id ? { ...b, status } : b)),
    );
    api.patchBill(bill.id, { status }).catch(refresh);
  };

  return (
    <main className="rise">
      {drafts.length > 0 && (
        <section className="mb-10">
          <h2 className="text-paper-dim text-sm tracking-widest uppercase mb-3">
            Detected — awaiting your review
          </h2>
          <ul className="space-y-2">
            {drafts.map((bill) => (
              <li key={bill.id} className="rounded-xl bg-ink-raised px-4 py-3">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-paper">{bill.display_name}</p>
                    <p className="text-xs text-paper-faint mt-0.5">
                      seen {bill.occurrences}× {CADENCE_LABEL[bill.cadence]}
                      {bill.last_seen && <> · last {fmtDate(bill.last_seen)}</>}
                      {" · "}confidence {(bill.confidence * 100).toFixed(0)}%
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="money text-paper">{fmtMoney(bill.amount_cents)}</span>
                    <button
                      onClick={() => setStatus(bill, "confirmed")}
                      className="rounded-full bg-go/15 border border-go/40 px-3 py-1 text-sm text-go cursor-pointer"
                    >
                      Confirm
                    </button>
                    <button
                      onClick={() => setStatus(bill, "dismissed")}
                      className="rounded-full px-3 py-1 text-sm text-paper-faint hover:text-paper cursor-pointer"
                    >
                      Dismiss
                    </button>
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      )}

      <section>
        <div className="flex items-baseline justify-between mb-3">
          <h2 className="text-paper-dim text-sm tracking-widest uppercase">
            Confirmed bills
          </h2>
          <button
            onClick={() => setAdding((v) => !v)}
            className="text-sm text-go cursor-pointer"
          >
            {adding ? "Cancel" : "+ Add bill"}
          </button>
        </div>

        {adding && <AddBillForm onDone={() => { setAdding(false); refresh(); }} />}

        {confirmed.length === 0 && !adding ? (
          <p className="text-paper-faint text-sm">
            None yet — confirm detections above or add one manually. Only
            confirmed bills move the forecast.
          </p>
        ) : (
          <ul className="divide-y divide-ink-line rounded-xl bg-ink-raised px-4">
            {confirmed.map((bill) => (
              <ConfirmedRow key={bill.id} bill={bill} onChange={refresh} onDismiss={() => setStatus(bill, "dismissed")} />
            ))}
          </ul>
        )}
      </section>

      {dismissed.length > 0 && (
        <section className="mt-10">
          <h2 className="text-paper-faint text-sm tracking-widest uppercase mb-3">Dismissed</h2>
          <ul className="space-y-1">
            {dismissed.map((bill) => (
              <li key={bill.id} className="flex justify-between text-sm text-paper-faint px-1 py-1">
                <span>{bill.display_name}</span>
                <button
                  onClick={() => setStatus(bill, "detected")}
                  className="cursor-pointer hover:text-paper"
                >
                  Restore
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  );
}

function ConfirmedRow({
  bill,
  onChange,
  onDismiss,
}: {
  bill: Bill;
  onChange: () => void;
  onDismiss: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [amount, setAmount] = useState((bill.amount_cents / 100).toFixed(2));
  const [cadence, setCadence] = useState<Cadence>(bill.cadence);
  const [nextDue, setNextDue] = useState(bill.next_due);

  const save = async () => {
    await api.patchBill(bill.id, {
      amount_cents: Math.round(parseFloat(amount) * 100),
      cadence,
      next_due: nextDue,
    });
    setEditing(false);
    onChange();
  };

  return (
    <li className="py-2.5">
      <div className="flex items-center justify-between gap-3 text-sm">
        <span className="text-paper">
          {bill.display_name}
          {bill.stale && (
            <span className="ml-2 text-hold" title="No matching transaction for 2 cycles">
              stale?
            </span>
          )}
        </span>
        <span className="flex items-center gap-3 text-paper-dim">
          <span>{CADENCE_LABEL[bill.cadence]}</span>
          <span>due {fmtDate(bill.next_due)}</span>
          <span className="money text-paper">{fmtMoney(bill.amount_cents)}</span>
          <button onClick={() => setEditing((v) => !v)} className="text-paper-faint hover:text-paper cursor-pointer">
            {editing ? "close" : "edit"}
          </button>
        </span>
      </div>
      {editing && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
          <input
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-24 rounded bg-ink border border-ink-line px-2 py-1 money text-paper"
          />
          <select
            value={cadence}
            onChange={(e) => setCadence(e.target.value as Cadence)}
            className="rounded bg-ink border border-ink-line px-2 py-1 text-paper"
          >
            {Object.entries(CADENCE_LABEL).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
          <input
            type="date"
            value={nextDue}
            onChange={(e) => setNextDue(e.target.value)}
            className="rounded bg-ink border border-ink-line px-2 py-1 text-paper"
          />
          <button onClick={save} className="rounded-full bg-go/15 border border-go/40 px-3 py-1 text-go cursor-pointer">
            Save
          </button>
          <button onClick={onDismiss} className="px-2 py-1 text-stop/80 hover:text-stop cursor-pointer">
            Dismiss
          </button>
        </div>
      )}
    </li>
  );
}

function AddBillForm({ onDone }: { onDone: () => void }) {
  const [name, setName] = useState("");
  const [amount, setAmount] = useState("");
  const [cadence, setCadence] = useState<Cadence>("monthly");
  const [nextDue, setNextDue] = useState("");
  const [accountId, setAccountId] = useState<number | null>(null);
  const [accounts, setAccounts] = useState<{ id: number; name: string }[]>([]);

  useEffect(() => {
    fetch("/api/accounts")
      .then((r) => r.json())
      .then((list) => {
        setAccounts(list);
        if (list.length > 0) setAccountId(list[0].id);
      });
  }, []);

  const submit = async () => {
    if (!name || !amount || !nextDue || accountId === null) return;
    await api.createBill({
      account_id: accountId,
      display_name: name,
      amount_cents: Math.round(parseFloat(amount) * 100),
      cadence,
      next_due: nextDue,
    });
    onDone();
  };

  return (
    <div className="mb-4 flex flex-wrap items-center gap-2 rounded-xl bg-ink-raised p-4 text-sm">
      <input
        placeholder="Name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="rounded bg-ink border border-ink-line px-2 py-1 text-paper"
      />
      <input
        placeholder="0.00"
        value={amount}
        onChange={(e) => setAmount(e.target.value)}
        className="w-24 rounded bg-ink border border-ink-line px-2 py-1 money text-paper"
      />
      <select
        value={cadence}
        onChange={(e) => setCadence(e.target.value as Cadence)}
        className="rounded bg-ink border border-ink-line px-2 py-1 text-paper"
      >
        {Object.entries(CADENCE_LABEL).map(([value, label]) => (
          <option key={value} value={value}>{label}</option>
        ))}
      </select>
      <input
        type="date"
        value={nextDue}
        onChange={(e) => setNextDue(e.target.value)}
        className="rounded bg-ink border border-ink-line px-2 py-1 text-paper"
      />
      {accounts.length > 1 && (
        <select
          value={accountId ?? undefined}
          onChange={(e) => setAccountId(Number(e.target.value))}
          className="rounded bg-ink border border-ink-line px-2 py-1 text-paper"
        >
          {accounts.map((a) => (
            <option key={a.id} value={a.id}>{a.name}</option>
          ))}
        </select>
      )}
      <button onClick={submit} className="rounded-full bg-go/15 border border-go/40 px-4 py-1 text-go cursor-pointer">
        Add
      </button>
    </div>
  );
}
