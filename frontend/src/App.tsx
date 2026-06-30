import { useEffect, useState } from "react";

import { AppShell } from "./components/AppShell";
import { Dashboard } from "./features/Dashboard";

const API_KEY_STORAGE_KEY = "byepaper_api_key";

export default function App() {
  const [apiKey, setApiKey] = useState("");

  useEffect(() => {
    setApiKey(localStorage.getItem(API_KEY_STORAGE_KEY) ?? "");
  }, []);

  function handleApiKeyChange(value: string) {
    setApiKey(value);
    localStorage.setItem(API_KEY_STORAGE_KEY, value);
  }

  return (
    <AppShell apiKey={apiKey} onApiKeyChange={handleApiKeyChange}>
      <Dashboard apiKey={apiKey} />
    </AppShell>
  );
}