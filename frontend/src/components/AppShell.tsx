import { FileStack, KeyRound } from "lucide-react";

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
          <textarea
            value={apiKey}
            onChange={(event) => onApiKeyChange(event.target.value)}
            placeholder="byp_xxxxx_xxxxx"
            rows={5}
          />
          <button className="sidebar-button" onClick={onOpenOnboarding}>
            Crear organización
          </button>
        </label>
      </aside>

      <main className="main-content">{children}</main>
    </div>
  );
}