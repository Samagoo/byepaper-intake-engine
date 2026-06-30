import { useEffect, useState } from "react";

import { AppShell } from "./components/AppShell";
import { BatchDetail } from "./features/BatchDetail";
import { Dashboard } from "./features/Dashboard";

const API_KEY_STORAGE_KEY = "byepaper_api_key";

type ViewState =
  | { name: "dashboard" }
  | { name: "batch"; batchId: string }
  | { name: "document"; documentId: string };

export default function App() {
  const [apiKey, setApiKey] = useState("");
  const [view, setView] = useState<ViewState>({ name: "dashboard" });

  useEffect(() => {
    setApiKey(localStorage.getItem(API_KEY_STORAGE_KEY) ?? "");
  }, []);

  function handleApiKeyChange(value: string) {
    setApiKey(value);
    localStorage.setItem(API_KEY_STORAGE_KEY, value);
  }

  return (
    <AppShell apiKey={apiKey} onApiKeyChange={handleApiKeyChange}>
      {view.name === "dashboard" && (
        <Dashboard
          apiKey={apiKey}
          onOpenBatch={(batchId) => setView({ name: "batch", batchId })}
        />
      )}

      {view.name === "batch" && (
        <BatchDetail
          apiKey={apiKey}
          batchId={view.batchId}
          onBack={() => setView({ name: "dashboard" })}
          onOpenDocument={(documentId) =>
            setView({ name: "document", documentId })
          }
        />
      )}

      {view.name === "document" && (
        <div className="empty-state">
          <h1>Detalle de documento</h1>
          <p>{view.documentId}</p>
          <button
            className="secondary-button"
            onClick={() => setView({ name: "dashboard" })}
          >
            Volver al dashboard
          </button>
        </div>
      )}
    </AppShell>
  );
}