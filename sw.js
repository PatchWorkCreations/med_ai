// sw.js — minimal, no caching
self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (e) => self.clients.claim());
