// Firebase Messaging Service Worker for background push notifications
importScripts("https://www.gstatic.com/firebasejs/9.23.0/firebase-app-compat.js");
importScripts("https://www.gstatic.com/firebasejs/9.23.0/firebase-messaging-compat.js");

const firebaseConfig = {
  apiKey: "AIzaSyAl_ADzvszn-x0t0ZaxO89brx1Oo5IWRA0",
  authDomain: "globalpulse-c4870.firebaseapp.com",
  projectId: "globalpulse-c4870",
  storageBucket: "globalpulse-c4870.firebasestorage.app",
  messagingSenderId: "438768082415",
  appId: "1:438768082415:web:fb65572341c1d2f9adea1a",
};

firebase.initializeApp(firebaseConfig);

let messaging = null;
try {
  messaging = firebase.messaging();
  messaging.onBackgroundMessage((payload) => {
    console.log("[firebase-messaging-sw.js] Received background push message:", payload);
    const notificationTitle = payload.notification?.title || "GlobalPulse Alert";
    const notificationOptions = {
      body: payload.notification?.body || "You have a new update.",
      icon: "/icon-dark-32x32.png",
      badge: "/icon-dark-32x32.png",
      data: payload.data || {},
    };

    self.registration.showNotification(notificationTitle, notificationOptions);
  });
} catch (err) {
  console.warn("[firebase-messaging-sw.js] Background messaging initialization skipped:", err);
}

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const targetUrl = event.notification.data?.action_url || "/dashboard";
  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then((windowClients) => {
      for (const client of windowClients) {
        if (client.url.includes(targetUrl) && "focus" in client) {
          return client.focus();
        }
      }
      if (clients.openWindow) {
        return clients.openWindow(targetUrl);
      }
    })
  );
});
