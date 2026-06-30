import { useEffect, useMemo, useState } from "react";
import { AlertCircle, BarChart3, Loader2, Plus } from "lucide-react";

import { createBatch, getMetrics, listBatches } from "../api/client";
import type { Batch, BatchStatus, Metrics } from "../types/api";

type DashboardProps = {
  apiKey: string;
  onOpenBatch: (batchId: string) => void;
};
const batchStatuses: Array<BatchStatus | "all"> = [
  "all",
  "created",
  "receiving",
  "processing",
  "completed",
  "failed",
  "partially_failed",
];

export function Dashboard({ apiKey, onOpenBatch }: DashboardProps) {
  const [batches, setBatches] = useState<Batch[]>([]);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [statusFilter, setStatusFilter] = useState<BatchStatus | "all">("all");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [batchName, setBatchName] = useState("");
  const [isCreating, setIsCreating] = useState(false);

  const canLoad = apiKey.trim().length > 0;

  const selectedStatus = useMemo(() => {
    return statusFilter === "all" ? undefined : statusFilter;
  }, [statusFilter]);

  async function loadDashboard() {
    if (!canLoad) return;

    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [batchesResponse, metricsResponse] = await Promise.all([
        listBatches(apiKey, selectedStatus),
        getMetrics(apiKey),
      ]);

      setBatches(batchesResponse.items);
      setMetrics(metricsResponse);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Unexpected frontend error",
      );
    } finally {
      setIsLoading(false);
    }
  }

  async function handleCreateBatch(event: React.FormEvent) {
    event.preventDefault();

    if (!batchName.trim()) return;

    setIsCreating(true);
    setErrorMessage(null);

    try {
      await createBatch(apiKey, {
        name: batchName.trim(),
        source: "frontend",
        metadata: {
          created_from: "react_ui",
        },
      });

      setBatchName("");
      await loadDashboard();
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "Could not create batch",
      );
    } finally {
      setIsCreating(false);
    }
  }

  useEffect(() => {
    void loadDashboard();
  }, [apiKey, selectedStatus]);

  if (!canLoad) {
    return (
      <section className="empty-state">
        <h1>ByePaper Intake Engine</h1>
        <p>Agrega una API key para cargar batches, métricas y documentos.</p>
      </section>
    );
  }

  return (
    <div className="dashboard">
      <header className="page-header">
        <div>
          <h1>Batches</h1>
          <p>Control de ingesta, procesamiento y revisión documental.</p>
        </div>

        <button className="secondary-button" onClick={loadDashboard}>
          {isLoading ? <Loader2 className="spin" size={16} /> : "Actualizar"}
        </button>
      </header>

      {errorMessage && (
        <div className="alert">
          <AlertCircle size={18} />
          <span>{errorMessage}</span>
        </div>
      )}

      <section className="metrics-grid">
        <MetricCard
          label="Documentos"
          value={metrics?.documents_total ?? 0}
          icon={<BarChart3 size={18} />}
        />
        <MetricCard
          label="Batches"
          value={metrics?.batches_total ?? 0}
          icon={<BarChart3 size={18} />}
        />
        <MetricCard
          label="Duplicados"
          value={metrics?.duplicate_candidates ?? 0}
          icon={<BarChart3 size={18} />}
        />
      </section>

      <section className="toolbar">
        <div className="tabs">
          {batchStatuses.map((status) => (
            <button
              key={status}
              className={statusFilter === status ? "tab active" : "tab"}
              onClick={() => setStatusFilter(status)}
            >
              {status}
            </button>
          ))}
        </div>

        <form className="create-form" onSubmit={handleCreateBatch}>
          <input
            value={batchName}
            onChange={(event) => setBatchName(event.target.value)}
            placeholder="Nuevo batch"
          />
          <button type="submit" disabled={isCreating}>
            <Plus size={16} />
            {isCreating ? "Creando..." : "Crear"}
          </button>
        </form>
      </section>

      <section className="table-panel">
        {isLoading ? (
          <div className="empty-state compact">
            <Loader2 className="spin" />
            <p>Cargando batches...</p>
          </div>
        ) : batches.length === 0 ? (
          <div className="empty-state compact">
            <p>No hay batches para este filtro.</p>
          </div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Nombre</th>
                <th>Fuente</th>
                <th>Estado</th>
                <th>Creado</th>
              </tr>
            </thead>
            <tbody>
              {batches.map((batch) => (
                <tr
                  key={batch.id}
                  className="clickable-row"
                  onClick={() => onOpenBatch(batch.id)}
                >
                  <td>
                    <strong>{batch.name}</strong>
                    <span>{batch.id}</span>
                  </td>
                  <td>{batch.source}</td>
                  <td>
                    <span className={`status-pill ${batch.status}`}>
                      {batch.status}
                    </span>
                  </td>
                  <td>{new Date(batch.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function MetricCard({
  label,
  value,
  icon,
}: {
  label: string;
  value: number;
  icon: React.ReactNode;
}) {
  return (
    <div className="metric-card">
      <div>{icon}</div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}