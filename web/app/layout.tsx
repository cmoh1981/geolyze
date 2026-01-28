import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: "GEOlyze - Automated GEO Data Analysis",
  description:
    "Enter any GEO accession ID and get publication-ready UMAP, heatmaps, DE analysis, and interactive plots. No coding required.",
  keywords: [
    "GEO",
    "bioinformatics",
    "RNA-seq",
    "scRNA-seq",
    "UMAP",
    "differential expression",
    "omics",
  ],
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={inter.className}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
