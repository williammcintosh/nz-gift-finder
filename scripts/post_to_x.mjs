#!/usr/bin/env node
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import process from 'node:process';

const ROOT = path.resolve(path.dirname(new URL(import.meta.url).pathname), '..');
const ENV_PATH = path.join(ROOT, '.env');
const DRAFTS_DIR = path.join(ROOT, 'drafts', 'x');
const ENDPOINT = 'https://api.x.com/2/tweets';

function loadEnv(filePath) {
  const env = {};
  if (!fs.existsSync(filePath)) return env;
  const raw = fs.readFileSync(filePath, 'utf8');
  for (const line of raw.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) continue;
    const idx = trimmed.indexOf('=');
    if (idx === -1) continue;
    const key = trimmed.slice(0, idx).trim();
    let value = trimmed.slice(idx + 1).trim();
    if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
      value = value.slice(1, -1);
    }
    env[key] = value;
  }
  return env;
}

function requireEnv(env, keys) {
  const missing = keys.filter((k) => !env[k]);
  if (missing.length) {
    throw new Error(`Missing required env vars in ${ENV_PATH}: ${missing.join(', ')}`);
  }
}

function percentEncode(value) {
  return encodeURIComponent(String(value))
    .replace(/[!'()*]/g, (c) => `%${c.charCodeAt(0).toString(16).toUpperCase()}`);
}

function nonce(size = 16) {
  return crypto.randomBytes(size).toString('hex');
}

function timestamp() {
  return Math.floor(Date.now() / 1000).toString();
}

function makeSignatureBaseString(method, url, oauthParams) {
  const normalized = Object.entries(oauthParams)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${percentEncode(k)}=${percentEncode(v)}`)
    .join('&');

  return [method.toUpperCase(), percentEncode(url), percentEncode(normalized)].join('&');
}

function sign(baseString, consumerSecret, tokenSecret) {
  const key = `${percentEncode(consumerSecret)}&${percentEncode(tokenSecret || '')}`;
  return crypto.createHmac('sha1', key).update(baseString).digest('base64');
}

function makeAuthHeader(oauthParams) {
  const header = Object.entries(oauthParams)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([k, v]) => `${percentEncode(k)}="${percentEncode(v)}"`)
    .join(', ');
  return `OAuth ${header}`;
}

function buildOAuthHeader(env, method, url) {
  const oauthParams = {
    oauth_consumer_key: env.X_CONSUMER_KEY,
    oauth_nonce: nonce(),
    oauth_signature_method: 'HMAC-SHA1',
    oauth_timestamp: timestamp(),
    oauth_token: env.X_ACCESS_TOKEN,
    oauth_version: '1.0',
  };

  const baseString = makeSignatureBaseString(method, url, oauthParams);
  oauthParams.oauth_signature = sign(baseString, env.X_CONSUMER_SECRET, env.X_ACCESS_TOKEN_SECRET);
  return makeAuthHeader(oauthParams);
}

function getTextFromArgs(args) {
  const text = args.join(' ').trim();
  if (!text) {
    throw new Error('No post text supplied. Example: node scripts/post_to_x.mjs draft "Hello from NZ Gift Finder"');
  }
  return text;
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function stamp() {
  return new Date().toISOString().replace(/[:.]/g, '-');
}

function saveDraft(text) {
  ensureDir(DRAFTS_DIR);
  const file = path.join(DRAFTS_DIR, `${stamp()}.txt`);
  fs.writeFileSync(file, `${text}\n`, 'utf8');
  return file;
}

async function createTweet(env, text, dryRun = false) {
  const body = { text };

  if (dryRun) {
    return { dryRun: true, body };
  }

  const auth = buildOAuthHeader(env, 'POST', ENDPOINT);
  const res = await fetch(ENDPOINT, {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: auth,
    },
    body: JSON.stringify(body),
  });

  const json = await res.json().catch(async () => ({ raw: await res.text() }));
  if (!res.ok) {
    throw new Error(`X API error ${res.status}: ${JSON.stringify(json)}`);
  }
  return json;
}

function usage() {
  console.log(`Usage:
  node scripts/post_to_x.mjs draft "your post text"
  node scripts/post_to_x.mjs dry-run "your post text"
  node scripts/post_to_x.mjs post "your post text"

Notes:
  - draft: save text to drafts/x/*.txt without posting
  - dry-run: validate env + print payload without posting
  - post: publish immediately to X using OAuth 1.0a user tokens
`);
}

async function main() {
  const [command, ...rest] = process.argv.slice(2);
  if (!command || ['-h', '--help', 'help'].includes(command)) {
    usage();
    return;
  }

  const text = getTextFromArgs(rest);

  if (text.length > 280) {
    throw new Error(`Post is ${text.length} characters. X limit is 280.`);
  }

  const env = { ...process.env, ...loadEnv(ENV_PATH) };

  if (command === 'draft') {
    const file = saveDraft(text);
    console.log(`Draft saved: ${path.relative(ROOT, file)}`);
    console.log(text);
    return;
  }

  requireEnv(env, [
    'X_CONSUMER_KEY',
    'X_CONSUMER_SECRET',
    'X_ACCESS_TOKEN',
    'X_ACCESS_TOKEN_SECRET',
  ]);

  if (command === 'dry-run') {
    const result = await createTweet(env, text, true);
    console.log(JSON.stringify(result, null, 2));
    return;
  }

  if (command === 'post') {
    const result = await createTweet(env, text, false);
    console.log(JSON.stringify(result, null, 2));
    return;
  }

  throw new Error(`Unknown command: ${command}`);
}

main().catch((err) => {
  console.error(err.message || err);
  process.exit(1);
});
