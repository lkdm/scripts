#!/usr/bin/env bun
import { $ } from 'bun';
// --- Import packages ---
await $`bun add --global lodash || true`.quiet()

// --- Script starts here ---
import _ from 'lodash'; // External packages

const out = _.chain(["Hello", "World"]).join(" ").value()

console.log(out + "!")
