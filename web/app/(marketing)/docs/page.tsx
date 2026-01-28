export const metadata = {
  title: "API Documentation - GEOlyze",
  description: "GEOlyze REST API documentation for programmatic access",
};

const endpoints = [
  {
    method: "POST",
    path: "/api/analyze",
    description: "Submit a new GEO dataset for analysis",
    body: '{\n  "geo_id": "GSE12345"\n}',
    response:
      '{\n  "id": "job_abc123",\n  "geo_id": "GSE12345",\n  "status": "pending",\n  "created_at": "2025-01-28T12:00:00Z"\n}',
  },
  {
    method: "GET",
    path: "/api/analyze/:jobId",
    description: "Check the status of an analysis job",
    body: null,
    response:
      '{\n  "id": "job_abc123",\n  "geo_id": "GSE12345",\n  "status": "analyzing",\n  "metadata": {\n    "title": "Study Title",\n    "organism": "Homo sapiens",\n    "samples": 24\n  }\n}',
  },
  {
    method: "GET",
    path: "/api/analyze/:jobId/results",
    description: "Retrieve analysis results including plot data",
    body: null,
    response:
      '{\n  "id": "job_abc123",\n  "status": "completed",\n  "result_data": {\n    "umap": { "data": [...], "layout": {...} },\n    "heatmap": { "data": [...], "layout": {...} },\n    "volcano": { "data": [...], "layout": {...} },\n    "qc": { "data": [...], "layout": {...} }\n  }\n}',
  },
  {
    method: "GET",
    path: "/api/jobs",
    description: "List all analysis jobs for the authenticated user",
    body: null,
    response:
      '[\n  {\n    "id": "job_abc123",\n    "geo_id": "GSE12345",\n    "status": "completed",\n    "created_at": "2025-01-28T12:00:00Z"\n  }\n]',
  },
];

export default function DocsPage() {
  return (
    <div className="py-20 px-4">
      <div className="max-w-4xl mx-auto">
        <h1 className="text-4xl font-bold text-slate-900">API Documentation</h1>
        <p className="mt-4 text-lg text-slate-600">
          Access GEOlyze programmatically with our REST API. Requires a Pro plan
          or higher.
        </p>

        {/* Auth */}
        <section className="mt-12">
          <h2 className="text-2xl font-bold text-slate-900">Authentication</h2>
          <p className="mt-3 text-slate-600">
            All API requests require a Bearer token in the Authorization header.
            Get your token from the dashboard settings.
          </p>
          <div className="mt-4 bg-slate-900 rounded-lg p-4 overflow-x-auto">
            <code className="text-sm text-green-400">
              Authorization: Bearer your_api_token_here
            </code>
          </div>
        </section>

        {/* Base URL */}
        <section className="mt-10">
          <h2 className="text-2xl font-bold text-slate-900">Base URL</h2>
          <div className="mt-4 bg-slate-900 rounded-lg p-4 overflow-x-auto">
            <code className="text-sm text-green-400">
              https://api.geolyze.io/v1
            </code>
          </div>
        </section>

        {/* Endpoints */}
        <section className="mt-10">
          <h2 className="text-2xl font-bold text-slate-900">Endpoints</h2>
          <div className="mt-6 space-y-8">
            {endpoints.map((ep) => (
              <div
                key={ep.path}
                className="border border-slate-200 rounded-xl overflow-hidden"
              >
                <div className="bg-slate-50 px-6 py-4 flex items-center gap-3">
                  <span
                    className={`px-2.5 py-0.5 rounded text-xs font-bold uppercase ${
                      ep.method === "POST"
                        ? "bg-green-100 text-green-700"
                        : "bg-blue-100 text-blue-700"
                    }`}
                  >
                    {ep.method}
                  </span>
                  <code className="text-sm font-mono text-slate-700">
                    {ep.path}
                  </code>
                </div>
                <div className="px-6 py-4">
                  <p className="text-sm text-slate-600">{ep.description}</p>

                  {ep.body && (
                    <div className="mt-4">
                      <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
                        Request Body
                      </p>
                      <pre className="bg-slate-900 rounded-lg p-4 overflow-x-auto">
                        <code className="text-sm text-green-400">
                          {ep.body}
                        </code>
                      </pre>
                    </div>
                  )}

                  <div className="mt-4">
                    <p className="text-xs font-medium text-slate-500 uppercase tracking-wide mb-2">
                      Response
                    </p>
                    <pre className="bg-slate-900 rounded-lg p-4 overflow-x-auto">
                      <code className="text-sm text-green-400">
                        {ep.response}
                      </code>
                    </pre>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Rate limits */}
        <section className="mt-10">
          <h2 className="text-2xl font-bold text-slate-900">Rate Limits</h2>
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200">
                  <th className="text-left py-3 px-4 font-semibold text-slate-700">
                    Plan
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-700">
                    Requests/min
                  </th>
                  <th className="text-left py-3 px-4 font-semibold text-slate-700">
                    Concurrent Jobs
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr className="border-b border-slate-100">
                  <td className="py-3 px-4 text-slate-600">Pro</td>
                  <td className="py-3 px-4 text-slate-600">60</td>
                  <td className="py-3 px-4 text-slate-600">5</td>
                </tr>
                <tr>
                  <td className="py-3 px-4 text-slate-600">Enterprise</td>
                  <td className="py-3 px-4 text-slate-600">300</td>
                  <td className="py-3 px-4 text-slate-600">Unlimited</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
