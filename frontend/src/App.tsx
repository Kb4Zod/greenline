import { useEffect, useState } from "react";
import { api } from "./api";
import CheckIn from "./views/CheckIn";
import Bills from "./views/Bills";
import ImportView from "./views/ImportView";

type Route = "checkin" | "bills" | "import";

function routeFromHash(): Route {
  const hash = window.location.hash.replace("#/", "");
  return hash === "bills" || hash === "import" ? hash : "checkin";
}

const TABS: { route: Route; label: string; hash: string }[] = [
  { route: "checkin", label: "Check-in", hash: "#/" },
  { route: "bills", label: "Bills", hash: "#/bills" },
  { route: "import", label: "Import", hash: "#/import" },
];

export default function App() {
  const [route, setRoute] = useState<Route>(routeFromHash);
  const [appName, setAppName] = useState("…");

  useEffect(() => {
    const onHash = () => setRoute(routeFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    // Name comes from backend config, never hardcoded (decision 0008).
    api.health().then((h) => {
      setAppName(h.app_name);
      document.title = h.app_name;
    }).catch(() => setAppName("Greenline (offline)"));
  }, []);

  return (
    <div className="mx-auto max-w-3xl px-6 pb-24">
      <header className="flex items-baseline justify-between pt-10 pb-12">
        <h1 className="text-xl tracking-[0.25em] uppercase text-paper">
          {appName}
        </h1>
        <nav className="flex gap-1 text-sm">
          {TABS.map((tab) => (
            <a
              key={tab.route}
              href={tab.hash}
              className={
                "px-3 py-1.5 rounded-full transition-colors " +
                (route === tab.route
                  ? "bg-ink-line text-paper"
                  : "text-paper-dim hover:text-paper")
              }
            >
              {tab.label}
            </a>
          ))}
        </nav>
      </header>

      {route === "checkin" && <CheckIn />}
      {route === "bills" && <Bills />}
      {route === "import" && <ImportView />}
    </div>
  );
}
