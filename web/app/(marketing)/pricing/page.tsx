import Link from "next/link";
import { Button } from "@/components/ui/button";

export const metadata = {
  title: "Pricing - GEOlyze",
  description: "Simple pricing for researchers. Start free, scale as you grow.",
};

const plans = [
  {
    name: "Free",
    price: "$0",
    period: "forever",
    description: "Perfect for trying out GEOlyze",
    features: [
      "3 analyses per month",
      "Basic plots (UMAP, heatmaps)",
      "24-hour data retention",
      "Standard processing queue",
      "PNG downloads",
    ],
    cta: "Get Started",
    ctaVariant: "outline" as const,
    href: "/signup",
    highlight: false,
  },
  {
    name: "Pro",
    price: "$29",
    period: "/month",
    description: "For active researchers and labs",
    features: [
      "Unlimited analyses",
      "All plot types (volcano, dot plots, pathway)",
      "30-day data retention",
      "Priority processing queue",
      "PNG, SVG, and PDF downloads",
      "API access",
      "Batch analysis (up to 10 datasets)",
      "Custom color palettes",
    ],
    cta: "Start Pro Trial",
    ctaVariant: "primary" as const,
    href: "/signup",
    highlight: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For institutions and large teams",
    features: [
      "Everything in Pro",
      "Unlimited data retention",
      "Dedicated processing",
      "SSO / SAML authentication",
      "Custom pipelines",
      "On-premise deployment option",
      "SLA and priority support",
      "Team management",
    ],
    cta: "Contact Sales",
    ctaVariant: "outline" as const,
    href: "mailto:enterprise@geolyze.io",
    highlight: false,
  },
];

export default function PricingPage() {
  return (
    <div className="py-20 px-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl font-bold text-slate-900">
            Simple, transparent pricing
          </h1>
          <p className="mt-4 text-lg text-slate-600 max-w-2xl mx-auto">
            Start free with 3 analyses per month. Upgrade to Pro for unlimited
            analyses and advanced features.
          </p>
        </div>

        {/* Plans */}
        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto">
          {plans.map((plan) => (
            <div
              key={plan.name}
              className={`rounded-2xl p-8 ${
                plan.highlight
                  ? "bg-indigo-600 text-white ring-4 ring-indigo-600 ring-offset-2"
                  : "bg-white border border-slate-200"
              }`}
            >
              <h3
                className={`text-lg font-semibold ${
                  plan.highlight ? "text-indigo-100" : "text-slate-900"
                }`}
              >
                {plan.name}
              </h3>
              <div className="mt-4 flex items-baseline gap-1">
                <span
                  className={`text-4xl font-bold ${
                    plan.highlight ? "text-white" : "text-slate-900"
                  }`}
                >
                  {plan.price}
                </span>
                <span
                  className={`text-sm ${
                    plan.highlight ? "text-indigo-200" : "text-slate-500"
                  }`}
                >
                  {plan.period}
                </span>
              </div>
              <p
                className={`mt-2 text-sm ${
                  plan.highlight ? "text-indigo-200" : "text-slate-500"
                }`}
              >
                {plan.description}
              </p>

              <ul className="mt-8 space-y-3">
                {plan.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2">
                    <svg
                      className={`w-5 h-5 flex-shrink-0 mt-0.5 ${
                        plan.highlight ? "text-indigo-200" : "text-indigo-600"
                      }`}
                      fill="none"
                      viewBox="0 0 24 24"
                      strokeWidth={2}
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M4.5 12.75l6 6 9-13.5"
                      />
                    </svg>
                    <span
                      className={`text-sm ${
                        plan.highlight ? "text-indigo-100" : "text-slate-600"
                      }`}
                    >
                      {feature}
                    </span>
                  </li>
                ))}
              </ul>

              <div className="mt-8">
                <Link href={plan.href}>
                  <Button
                    variant={plan.highlight ? "secondary" : plan.ctaVariant}
                    className="w-full"
                  >
                    {plan.cta}
                  </Button>
                </Link>
              </div>
            </div>
          ))}
        </div>

        {/* FAQ teaser */}
        <div className="mt-20 text-center">
          <p className="text-slate-600">
            Have questions?{" "}
            <a
              href="mailto:support@geolyze.io"
              className="text-indigo-600 font-medium hover:text-indigo-500"
            >
              Contact us
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
