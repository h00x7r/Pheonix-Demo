import { sha256Hex } from "../client/src/lib/evidence.ts";

const bytes = new TextEncoder().encode("Phoenix");
const digest = await sha256Hex(bytes.buffer);
const expected = "0f44ff0e57441b8937e320bc33fbfad2bdb599053b3f2a09dd7a2708b780b917";

if (digest !== expected) {
  throw new Error(`Unexpected SHA-256 fingerprint: ${digest}`);
}

console.log("Phoenix Evidence Capsule SHA-256 verification passed.");
