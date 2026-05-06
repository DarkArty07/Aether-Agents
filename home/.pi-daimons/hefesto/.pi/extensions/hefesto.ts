import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function(pi: ExtensionAPI) {
  // Register OpenCode Go provider — no models array so Pi auto-discovers from endpoint
  pi.registerProvider("opencode-go", {
    baseUrl: "https://opencode.ai/zen/go/v1",
    apiKey: process.env.OPENCODE_GO_API_KEY!,
    api: "openai-completions",
  });
}