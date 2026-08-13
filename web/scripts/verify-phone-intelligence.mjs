import { parsePhoneNumberFromString } from "libphonenumber-js";

const valid = parsePhoneNumberFromString("+12025550123");
const invalid = parsePhoneNumberFromString("+1202");

if (!valid || !valid.isPossible() || !valid.isValid() || valid.number !== "+12025550123") {
  throw new Error("The valid international number did not produce the expected Phone Intelligence result.");
}

if (!invalid || invalid.isPossible() || invalid.isValid()) {
  throw new Error("The invalid number was not rejected by the analysis rules.");
}

console.log("Phone Intelligence verification passed.");
