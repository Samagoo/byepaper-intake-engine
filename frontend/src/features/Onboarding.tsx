import { useMemo, useState } from "react";
import { AlertCircle, Building2, CheckCircle2, KeyRound, Loader2 } from "lucide-react";

import { createOrganization, createOrganizationApiKey } from "../api/client";

type OnboardingProps = {
  onApiKeyCreated: (apiKey: string) => void;
};

function buildSlug(value: string) {
  return value
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function Onboarding({ onApiKeyCreated }: OnboardingProps) {
  const [name, setName] = useState("Demo Organization");
  const [slug, setSlug] = useState("demo-organization");
  const [apiKey, setApiKey] = useState("");
  const [organizationId, setOrganizationId] = useState("");
  const [isCreating, setIsCreating] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const canSubmit = useMemo(() => {
    return name.trim().length >= 2 && slug.trim().length >= 2;
  }, [name, slug]);

  function handleNameChange(value: string) {
    setName(value);
    setSlug(buildSlug(value));
  }

  async function handleCreateOrganization(event: React.FormEvent) {
    event.preventDefault();

    if (!canSubmit) return;

    setIsCreating(true);
    setErrorMessage(null);
    setApiKey("");
    setOrganizationId("");

    try {
      const organization = await createOrganization({
        name: name.trim(),
        slug: slug.trim(),
        status: "active",
      });

      const apiKeyResponse = await createOrganizationApiKey(organization.id);

      setOrganizationId(organization.id);
      setApiKey(apiKeyResponse.api_key);
      onApiKeyCreated(apiKeyResponse.api_key);
    } catch (error) {
      setErrorMessage(
        error instanceof Error
          ? error.message
          : "Could not create organization",
      );
    } finally {
      setIsCreating(false);
    }
  }

  return (
    <div className="dashboard">
      <header className="page-header">
        <div>
          <h1>Crear organización</h1>
          <p>
            Crea un tenant local y genera una API key para usar el dashboard.
          </p>
        </div>
      </header>

      {errorMessage && (
        <div className="alert">
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      <section className="onboarding-grid">
        <form className="onboarding-card" onSubmit={handleCreateOrganization}>
          <div className="onboarding-title">
            <Building2 size={22} />
            <div>
              <h2>Nueva organización</h2>
              <p>Esta organización será el tenant dueño de sus batches y documentos.</p>
            </div>
          </div>

          <label>
            Nombre
            <input
              value={name}
              onChange={(event) => handleNameChange(event.target.value)}
              placeholder="Ej. Empresa Norte"
            />
          </label>

          <label>
            Slug
            <input
              value={slug}
              onChange={(event) => setSlug(buildSlug(event.target.value))}
              placeholder="empresa-norte"
            />
          </label>

          <button type="submit" disabled={!canSubmit || isCreating}>
            {isCreating ? <Loader2 className="spin" size={16} /> : <KeyRound size={16} />}
            {isCreating ? "Creando..." : "Crear organización y API key"}
          </button>
        </form>

        <section className="onboarding-card">
          <div className="onboarding-title">
            <KeyRound size={22} />
            <div>
              <h2>API key generada</h2>
              <p>La API key completa solo se muestra una vez.</p>
            </div>
          </div>

          {apiKey ? (
            <div className="success-box">
              <CheckCircle2 size={18} />
              <div>
                <strong>Organización lista</strong>
                <span>{organizationId}</span>
              </div>
            </div>
          ) : (
            <div className="empty-state compact">
              <p>Aquí aparecerá la API key cuando crees la organización.</p>
            </div>
          )}

          <textarea
            className="api-key-result"
            value={apiKey}
            readOnly
            placeholder="byp_xxxxx_xxxxx"
            rows={6}
          />

          {apiKey && (
            <p className="helper-text">
              Ya guardé esta API key en el navegador y puedes usar el dashboard.
            </p>
          )}
        </section>
      </section>
    </div>
  );
}