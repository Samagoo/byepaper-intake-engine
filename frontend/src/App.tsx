import { useEffect, useState } from "react";

import { AppShell } from "./components/AppShell";
import { BatchDetail } from "./features/BatchDetail";
import { Dashboard } from "./features/Dashboard";
import { DocumentDetail } from "./features/DocumentDetail";
import { Onboarding } from "./features/Onboarding";

const API_KEY_STORAGE_KEY = "byepaper_api_key";

type ViewState =
  | { name: "onboarding" }
  | { name: "dashboard" }
  | { name: "batch"; batchId: string }
  | { name: "document"; documentId: string };

export default function App() {
  const [apiKey, setApiKey] = useState("");
  const [view, setView] = useState<ViewState>({ name: "onboarding" });

  useEffect(() => {
    const storedApiKey = localStorage.getItem(API_KEY_STORAGE_KEY) ?? "";
    setApiKey(storedApiKey);

    if (storedApiKey) {
      setView({ name: "dashboard" });
    }
  }, []);

  function handleApiKeyChange(value: string) {
    setApiKey(value);
    localStorage.setItem(API_KEY_STORAGE_KEY, value);
  }

  function handleApiKeyCreated(value: string) {
    handleApiKeyChange(value);
    setView({ name: "dashboard" });
  }

  return (
    <AppShell
      apiKey={apiKey}
      onApiKeyChange={handleApiKeyChange}
      onOpenOnboarding={() => setView({ name: "onboarding" })}
    >
      {view.name === "onboarding" && (
        <Onboarding onApiKeyCreated={handleApiKeyCreated} />
      )}

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
        <DocumentDetail
          apiKey={apiKey}
          documentId={view.documentId}
          onBack={() => setView({ name: "dashboard" })}
        />
      )}
    </AppShell>
  );
}