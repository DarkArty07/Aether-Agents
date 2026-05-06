import type { ExtensionAPI } from "@mariozechner/pi-coding-agent";

export default function(pi: ExtensionAPI) {
  pi.registerProvider("opencode-go", {
    baseUrl: "https://opencode.ai/zen/go/v1",
    apiKey: process.env.OPENCODE_GO_API_KEY!,
    api: "openai-completions",
  });
}
