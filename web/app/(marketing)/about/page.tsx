export const metadata = {
  title: "About - GEOlyze",
  description:
    "GEOlyze makes omics data analysis accessible to every researcher",
};

export default function AboutPage() {
  return (
    <div className="py-20 px-4">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold text-slate-900">About GEOlyze</h1>

        <div className="mt-8 prose prose-slate max-w-none">
          <p className="text-lg text-slate-600 leading-relaxed">
            GEOlyze was built to solve a simple problem: analyzing public omics
            datasets from NCBI GEO shouldn&apos;t require weeks of bioinformatics
            expertise. Researchers spend too much time writing analysis scripts
            instead of interpreting results.
          </p>

          <h2 className="text-2xl font-bold text-slate-900 mt-12 mb-4">
            Our Mission
          </h2>
          <p className="text-slate-600 leading-relaxed">
            We believe every researcher should have access to professional-grade
            omics analysis tools, regardless of their computational background.
            GEOlyze automates the entire pipeline from raw GEO accession to
            publication-ready figures.
          </p>

          <h2 className="text-2xl font-bold text-slate-900 mt-12 mb-4">
            What We Do
          </h2>
          <ul className="space-y-3 text-slate-600">
            <li className="flex gap-2">
              <span className="text-indigo-600 font-bold">1.</span>
              <span>
                <strong>Automatic data type detection</strong> — We identify
                whether your dataset is bulk RNA-seq, single-cell, microarray, or
                other omics data and apply the appropriate pipeline.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-600 font-bold">2.</span>
              <span>
                <strong>End-to-end analysis</strong> — Quality control,
                normalization, dimensionality reduction, clustering, differential
                expression, and pathway analysis.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-600 font-bold">3.</span>
              <span>
                <strong>Interactive visualizations</strong> — Explore your results
                with UMAP plots, heatmaps, volcano plots, and more using
                interactive Plotly charts.
              </span>
            </li>
            <li className="flex gap-2">
              <span className="text-indigo-600 font-bold">4.</span>
              <span>
                <strong>Publication-ready exports</strong> — Download
                high-resolution figures and analysis reports suitable for
                journals and grant applications.
              </span>
            </li>
          </ul>

          <h2 className="text-2xl font-bold text-slate-900 mt-12 mb-4">
            Technology
          </h2>
          <p className="text-slate-600 leading-relaxed">
            GEOlyze is built on proven bioinformatics tools including Scanpy,
            DESeq2, and custom pipelines optimized for GEO datasets. Our backend
            processes datasets in parallel using cloud infrastructure to deliver
            results in minutes rather than hours.
          </p>

          <h2 className="text-2xl font-bold text-slate-900 mt-12 mb-4">
            Contact
          </h2>
          <p className="text-slate-600 leading-relaxed">
            Questions, feedback, or partnership inquiries? Reach us at{" "}
            <a
              href="mailto:hello@geolyze.io"
              className="text-indigo-600 font-medium hover:text-indigo-500"
            >
              hello@geolyze.io
            </a>
            .
          </p>
        </div>
      </div>
    </div>
  );
}
