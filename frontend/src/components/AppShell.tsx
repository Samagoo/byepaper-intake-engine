import { Eye, EyeOff, FileStack, KeyRound, Trash2 } from "lucide-react";
import { useState } from "react";


type AppShellProps = {
  apiKey: string;
  onApiKeyChange: (value: string) => void;
  onOpenOnboarding: () => void;
  children: React.ReactNode;
};

export function AppShell({
  apiKey,
  onApiKeyChange,
  onOpenOnboarding,
  children,
}: AppShellProps) {
  const [showApiKey, setShowApiKey] = useState(false);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <FileStack size={24} />
          <div>
            <strong>ByePaper</strong>
            <span>Intake Engine</span>
          </div>
        </div>

        <label className="api-key-box">
          <span>
            <KeyRound size={16} />
            API Key
          </span>
          <div className="api-key-input-row">
            <input
              type={showApiKey ? "text" : "password"}
              value={apiKey}
              onChange={(event) => onApiKeyChange(event.target.value)}
              placeholder="byp_xxxxx_xxxxx"
            />

            <button
              type="button"
              className="icon-button"
              onClick={() => setShowApiKey((value) => !value)}
              title={showApiKey ? "Ocultar API key" : "Mostrar API key"}
            >
              {showApiKey ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>

            <button
              type="button"
              className="icon-button"
              onClick={() => onApiKeyChange("")}
              title="Limpiar API key"
            >
              <Trash2 size={16} />
            </button>
          </div>
          <button className="sidebar-button" onClick={onOpenOnboarding}>
            Crear organización
          </button>
        </label>
      </aside>

      <main className="main-content">{children}</main>
    </div>
  );
}