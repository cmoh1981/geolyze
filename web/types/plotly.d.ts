declare module "react-plotly.js" {
  import { Component } from "react";

  interface PlotParams {
    data: Array<Record<string, unknown>>;
    layout?: Record<string, unknown>;
    config?: Record<string, unknown>;
    style?: React.CSSProperties;
    useResizeHandler?: boolean;
    onInitialized?: (figure: { data: unknown; layout: unknown }) => void;
    onUpdate?: (figure: { data: unknown; layout: unknown }) => void;
  }

  export default class Plot extends Component<PlotParams> {}
}

declare module "plotly.js-dist-min" {
  export function downloadImage(
    gd: unknown,
    opts: {
      format?: string;
      filename?: string;
      width?: number;
      height?: number;
      scale?: number;
    }
  ): Promise<string>;
}
