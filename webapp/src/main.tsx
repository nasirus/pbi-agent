import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import App from "./App";
import "./styles/index.css";
import logoUrl from "../../src/pbi_agent/web/static/logo.jpg";

function ensureBrandIcons(): void {
  const iconSelectors = [
    { rel: "icon", type: "image/jpeg" },
    { rel: "apple-touch-icon", type: "image/jpeg" },
  ];

  for (const { rel, type } of iconSelectors) {
    let link = document.head.querySelector<HTMLLinkElement>(
      `link[rel="${rel}"]`,
    );
    if (link === null) {
      link = document.createElement("link");
      link.rel = rel;
      document.head.appendChild(link);
    }
    link.type = type;
    link.href = logoUrl;
  }
}

ensureBrandIcons();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
);
