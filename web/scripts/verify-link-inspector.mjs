import { assessUrl } from "../client/src/lib/url-security.ts";

const plain = assessUrl("https://example.com/account");
if (plain.score !== 0 || plain.band !== "low" || plain.signals.length !== 0) {
  throw new Error("Expected a plain HTTPS link to have no local risk signals.");
}

const suspicious = assessUrl("http://notice@127.0.0.1:8080/update.exe?redirect=https%3A%2F%2Fexample.com");
const signalIds = new Set(suspicious.signals.map((signal) => signal.id));
for (const expected of ["no-https", "userinfo", "ip-host", "custom-port", "download", "redirect"]) {
  if (!signalIds.has(expected)) throw new Error(`Expected local signal not found: ${expected}`);
}
if (suspicious.band !== "high") {
  throw new Error("Expected the compound local signals to produce a high review band.");
}

console.log("Local Link Inspector verification passed without network requests.");
