importScripts('https://storage.googleapis.com/workbox-cdn/releases/3.0.0/workbox-sw.js');

console.log('this is my custom service worker');

workbox.precaching.precacheAndRoute([]);

self.addEventListener('install', function(event) {
  console.log('The service worker is installed');
});
